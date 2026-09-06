import logging
import asyncio
import os
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobExecutorType,
    TurnHandlingOptions,
    cli,
)
from livekit.plugins import openai, rime, silero, google

load_dotenv()
logger = logging.getLogger("negotiate-it")

from livekit.agents import llm
from livekit.agents.llm import function_tool
import zlib
import re
import json
import time

from cognition.schemas import PsychologicalState, Personality
from cognition.state_engine import StateUpdateSignal, apply_state_transition

# Preload Silero VAD globally once at process startup with optimized speech threshold & prefix padding
# prefix_padding_duration ensures the first syllable/consonant is NEVER clipped when speaking
PRELOADED_VAD = silero.VAD.load(
    min_speech_duration=0.08,
    min_silence_duration=0.28,
    prefix_padding_duration=0.35,
    activation_threshold=0.45
)

FEMALE_VOICES = {
    'aggressive': ['astra', 'lyra', 'breeze'],
    'authoritative': ['astra', 'lyra'],
    'frantic': ['breeze', 'iris', 'rain'],
    'desperate': ['rain', 'willow', 'iris'],
    'cold': ['lyra', 'astra'],
    'paranoid': ['iris', 'breeze', 'willow'],
    'default': ['lyra', 'astra', 'breeze', 'iris', 'willow', 'rain']
}

MALE_VOICES = {
    'aggressive': ['stone', 'storm', 'hawk'],
    'authoritative': ['cedar', 'stone', 'hawk'],
    'frantic': ['falcon', 'cove', 'river'],
    'desperate': ['ember', 'marsh', 'cove'],
    'cold': ['cedar', 'stone', 'marsh'],
    'paranoid': ['ember', 'falcon', 'river'],
    'default': ['marsh', 'cove', 'cedar', 'falcon', 'stone', 'river', 'hawk', 'ember', 'storm']
}

def select_speaker(name: str, gender: str, archetype: str = '') -> str:
    """Intelligently maps name, gender, and psychological archetype to a unique Rime voice."""
    g = (gender or 'male').lower()
    arch = (archetype or '').lower()
    clean_name = re.sub(r'[^a-zA-Z]', '', name).lower() or 'person'
    h = zlib.crc32(clean_name.encode('utf-8'))
    if any(female_kw in g for female_kw in ['female', 'woman', 'girl', 'she', 'her']):
        bank = FEMALE_VOICES.get(arch, FEMALE_VOICES['default'])
        return bank[h % len(bank)]
    else:
        bank = MALE_VOICES.get(arch, MALE_VOICES['default'])
        return bank[h % len(bank)]


def clean_spoken_text(text: str) -> str:
    """Strips meta-reasoning, thoughts, brackets, and internal prompt leakage before TTS."""
    if not text:
        return ""
    # Strip thoughts tag or XML tags if any
    text = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    # Remove anything inside parentheses or brackets used as stage directions
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)
    # Remove asterisk-wrapped actions like *slams fist* or *gasps*
    text = re.sub(r'\*[^*]*\*', '', text)
    # Remove markdown bold/italic
    text = re.sub(r'[*_]{1,3}', '', text)
    
    # Check for double newline delimiter where models often dump meta-analysis after dialogue
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if paragraphs:
        meta_indicators = (
            'we have to respond', 'the user said', 'we need to', 'we must', 'let\'s respond',
            'she might say', 'he might say', 'elena might', 'alex might', 'update stress',
            'as elena', 'as alex', 'internal state', 'the negotiator', 'respond as'
        )
        filtered_paras = []
        for p in paragraphs:
            p_lower = p.lower()
            if any(indicator in p_lower for indicator in meta_indicators):
                break  # Stop as soon as meta reasoning starts
            filtered_paras.append(p)
        text = ' '.join(filtered_paras) if filtered_paras else paragraphs[0]

    bad_starts = (
        'the user', 'the negotiator', 'i need to', 'i should', 'we need to',
        'the instruction', 'system:', 'thought:', 'thinking:', 'response:',
        'as the character', 'i must', 'we must', 'internal state', 'instruction:',
        'we have to', 'let us', 'let\'s'
    )
    lines = text.split('\n')
    valid_lines = []
    for l in lines:
        stripped = l.strip()
        if not stripped:
            continue
        if any(stripped.lower().startswith(b) for b in bad_starts):
            continue
        valid_lines.append(stripped)
    text = ' '.join(valid_lines)
    # Strip any stray trailing JSON artifacts (e.g., '"]}', '"}', or quotes) if the LLM escaped JSON
    text = re.sub(r'[\"\']\s*[\}\]]+\s*$', '', text)
    text = re.sub(r'[\"\'\`]+$', '', text)
    # Collapse multiple ellipses or dot sequences into a single comma pause
    text = re.sub(r'(\s*[\.…]+\s*)+', ', ', text)
    return text.strip()


async def filter_inner_thoughts(text_stream):
    """Custom LiveKit TTS text transform that intercepts and strips internal thoughts/reasoning in realtime."""
    buffer = ''
    meta_cutoff_patterns = (
        r'\bwe have to respond\b', r'\bthe user said\b', r'\bwe need to\b',
        r'\bwe must\b', r'\bupdate stress\b', r'\blet\'s respond\b',
        r'\bthe negotiator said\b', r'\binternal state\b', r'\bthinking:\b'
    )
    bad_starts = (
        'the user', 'the negotiator', 'i need to', 'i should', 'we need to',
        'the instruction', 'system:', 'thought:', 'thinking:', 'response:',
        'as the character', 'i must', 'we must', 'internal state', 'instruction:',
        'we have to', 'let us', 'let\'s'
    )
    stopped = False

    async for chunk in text_stream:
        if stopped:
            break
        buffer += chunk
        
        # Check if meta reasoning has started in the stream
        buffer_lower = buffer.lower()
        for pat in meta_cutoff_patterns:
            if re.search(pat, buffer_lower):
                stopped = True
                match = re.search(pat, buffer_lower)
                buffer = buffer[:match.start()]
                break

        while True:
            match = re.search(r'[\n.!?]', buffer)
            if not match:
                break
            idx = match.end()
            segment = buffer[:idx]
            buffer = buffer[idx:]
            
            stripped = segment.strip()
            if any(stripped.lower().startswith(b) for b in bad_starts):
                continue
            cleaned = re.sub(r'<[^>]*>', '', segment)
            cleaned = re.sub(r'\([^)]*\)', '', cleaned)
            cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
            cleaned = re.sub(r'\*[^*]*\*', '', cleaned)
            if cleaned.strip():
                yield cleaned

    if not stopped and buffer.strip():
        stripped = buffer.strip()
        if not any(stripped.lower().startswith(b) for b in bad_starts):
            cleaned = re.sub(r'<[^>]*>', '', buffer)
            cleaned = re.sub(r'\([^)]*\)', '', cleaned)
            cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
            cleaned = re.sub(r'\*[^*]*\*', '', cleaned)
            if cleaned.strip():
                yield cleaned


class NegotiatorAgent(Agent):
    def __init__(self, instructions: str, on_enter_prompt: str, room, subject_name: str = "Alex", opening_line: str = "", archetype: str = "") -> None:
        super().__init__(
            instructions=instructions,
        )
        self._on_enter_prompt = on_enter_prompt
        self._room = room
        self._subject_name = subject_name
        self._opening_line = opening_line
        self._archetype = archetype
        
        volatility, impulsivity, dominance = 0.5, 0.5, 0.5
        if archetype == "frantic":
            volatility, impulsivity, dominance = 0.9, 0.8, 0.3
        elif archetype == "aggressive":
            volatility, impulsivity, dominance = 0.8, 0.7, 0.8
        elif archetype == "desperate":
            volatility, impulsivity, dominance = 0.7, 0.6, 0.4
        elif archetype == "paranoid":
            volatility, impulsivity, dominance = 0.6, 0.4, 0.6
            
        self._personality = Personality(
            impulsivity=impulsivity,
            dominance=dominance,
            emotional_volatility=volatility,
        )
        self._psychology = PsychologicalState(stress=85, fear=70, anger=60, desperation=80, sense_of_control=20, guilt=10)
        
        self._stress = 85
        self._surrendered = False
        self._escalated = False
        self._last_user_text = ""
        self._cut_off = False
        self._last_directive_msg = None

    async def _evaluate_dialogue_state(self, user_text: str, agent_text: str):
        """Asynchronously updates stress, surrender, and escalation in the background without blocking voice streaming."""
        try:
            u = user_text.lower()
            delta = 0
            calm_signals = ('calm', 'listen', 'promise', 'help', 'safe', 'understand', 'doctor', 'family', 'water', 'food', 'nobody gets hurt', 'talk to me', 'here with you', 'trust me', 'no one will hurt')
            tense_signals = ('surrender now', 'give up', 'breach', 'sniper', 'jail', 'prison', 'guilty', 'drop the weapon', 'final warning', 'now or else', 'idiot', 'crazy', 'shut up', 'back off')
            
            for word in calm_signals:
                if word in u:
                    delta -= 5
            for word in tense_signals:
                if word in u:
                    delta += 8
            
            if delta == 0 and u:
                delta = -2 if len(u.split()) >= 4 else 1

            self._stress = max(10, min(100, self._stress + delta))
            logger.info(f"Updated internal stress to {self._stress}% (delta {delta:+d})")
            
            if self._room.isconnected and self._room.local_participant:
                await self._room.local_participant.publish_data(
                    json.dumps({"type": "stress", "level": self._stress}).encode("utf-8"),
                    reliable=True
                )

            agent_lower = agent_text.lower()
            if self._stress <= 20 or any(kw in agent_lower for kw in ['i give up', 'putting my hands up', 'walking out', 'i surrender', "i'm coming out", "hands are up"]):
                if not self._surrendered:
                    self._surrendered = True
                    logger.info("Triggered SURRENDER based on dialogue and stress level!")
                    await self._room.local_participant.publish_data(
                        json.dumps({"type": "surrender"}).encode("utf-8"),
                        reliable=True
                    )
                    asyncio.create_task(self._generate_report("SUCCESSFUL SURRENDER"))
            elif self._stress >= 100 or any(kw in agent_lower for kw in ["it's over for all of you", "shoot them", "pulling the trigger", "last warning"]):
                if not self._escalated:
                    self._escalated = True
                    logger.info("Triggered ESCALATION based on dialogue and stress level!")
                    await self._room.local_participant.publish_data(
                        json.dumps({"type": "escalate"}).encode("utf-8"),
                        reliable=True
                    )
                    asyncio.create_task(self._generate_report("FAILED NEGOTIATION - SUBJECT ESCALATED"))
        except Exception as e:
            logger.warning(f"Error in background stress evaluation: {e}")

    async def on_enter(self) -> None:
        import time
        self._last_speech_time = time.time()
        self._nudge_count = 0

        async def _dead_air_loop():
            while True:
                await asyncio.sleep(1.0)
                if time.time() - self._last_speech_time > 3.5 and self._nudge_count < 1:
                    logger.info("Dead air detected, nudging user...")
                    self.session.chat_ctx.messages.append(llm.ChatMessage(role="system", content="[SYSTEM] The user has been silent for 3.5 seconds. Give a very short, anxious 2-4 word nudge (e.g. 'You there?', 'Hello?', 'Don't go silent on me.')."))
                    self.session.generate_reply()
                    self._nudge_count += 1
                    self._last_speech_time = time.time()

        asyncio.create_task(_dead_air_loop())

        @self.session.on("user_input_transcribed")
        def _on_user_input(ev):
            transcript = (ev.transcript or "").strip()
            if not transcript:
                return
            if ev.is_final:
                self._last_user_text = transcript
                self._last_speech_time = time.time()
                self._nudge_count = 0
                
                # Heuristic Appraisal
                u = transcript.lower()
                threat_delta = hope_delta = respect_delta = 0
                
                calm_signals = ('calm', 'listen', 'promise', 'help', 'safe', 'understand', 'doctor', 'family', 'water', 'food', 'nobody gets hurt', 'talk to me', 'here with you', 'trust me', 'no one will hurt')
                tense_signals = ('surrender now', 'give up', 'breach', 'sniper', 'jail', 'prison', 'guilty', 'drop the weapon', 'final warning', 'now or else', 'idiot', 'crazy', 'shut up', 'back off')
                
                for word in calm_signals:
                    if word in u:
                        hope_delta += 10
                        threat_delta -= 10
                for word in tense_signals:
                    if word in u:
                        threat_delta += 20
                        respect_delta -= 10
                        
                signal = StateUpdateSignal(threat_delta=threat_delta, hope_delta=hope_delta, respect_delta=respect_delta)
                new_psych, meta = apply_state_transition(self._psychology, self._personality, signal)
                self._psychology = new_psych
                
                # Compute cognitive pacing based on state
                pacing = "normal"
                derived_speed = 1.05
                if new_psych.fear > 80 or new_psych.anger > 80:
                    pacing = "erratic and fast"
                    derived_speed = 1.15
                elif new_psych.fear > 60:
                    pacing = "anxious and hesitant"
                    derived_speed = 1.0
                elif new_psych.anger > 60:
                    pacing = "hostile and tense"
                    derived_speed = 1.10
                    
                # Update TTS plugin dynamically if possible, or we just rely on LLM expression
                
                cut_off_str = " (You were just CUT OFF by the negotiator. SNAP BACK or react angrily to being interrupted.)" if self._cut_off else ""
                self._cut_off = False
                
                directive_text = f"[COGNITIVE DIRECTIVE] State: Fear={int(new_psych.fear)} Anger={int(new_psych.anger)} Stress={int(new_psych.stress)}. Pacing: {pacing}. Keep reply under 2 lines.{cut_off_str}"
                logger.info(f"Generated sidecar directive: {directive_text}")
                
                # Inject directive into session history
                msg = llm.ChatMessage(role="system", content=directive_text)
                self.session.chat_ctx.messages.append(msg)
                
            try:
                if self._room.isconnected and self._room.local_participant:
                    item_id = str(getattr(ev, 'item_id', None) or f"user-{time.time()}")
                    asyncio.create_task(
                        self._room.local_participant.publish_data(
                            json.dumps({
                                "type": "transcript",
                                "id": item_id,
                                "speaker": "user",
                                "senderName": "YOU",
                                "text": transcript,
                                "isFinal": bool(ev.is_final)
                            }).encode("utf-8"),
                            reliable=bool(ev.is_final)
                        )
                    )
            except Exception as e:
                logger.warning(f"Failed to publish user transcript: {e}")

        @self.session.on("agent_speech_interrupted")
        def _on_interrupted(ev):
            logger.info("Agent speech interrupted!")
            self._cut_off = True

        @self.session.on("conversation_item_added")
        def _on_item_added(ev):
            self._last_speech_time = time.time()
            try:
                msg = ev.item
                if msg.role == "assistant" and msg.text_content:
                    cleaned = clean_spoken_text(msg.text_content)
                    if cleaned:
                        logger.info(f"Subject speech scheduled: {cleaned}")
                        item_id = str(getattr(msg, 'id', None) or f"agent-{time.time()}")
                        if self._room.isconnected and self._room.local_participant:
                            asyncio.create_task(
                                self._room.local_participant.publish_data(
                                    json.dumps({
                                        "type": "transcript",
                                        "id": item_id,
                                        "speaker": "agent",
                                        "senderName": self._subject_name.upper(),
                                        "text": cleaned,
                                        "isFinal": True
                                    }).encode("utf-8"),
                                    reliable=True
                                )
                            )
                        # Evaluate stress and milestones asynchronously in background
                        asyncio.create_task(self._evaluate_dialogue_state(self._last_user_text, cleaned))
            except Exception as e:
                logger.warning(f"Error handling agent transcript broadcast: {e}")

            # Keep a deep, rich 100-turn context window so the subject never loses memory of earlier dialogue
            if len(list(self.session.history.messages())) > 100:
                self.session.history.truncate(max_items=100)

        if self._opening_line:
            logger.info(f"[FAST-START] Speaking instant opening line: {self._opening_line}")
            self.session.say(self._opening_line, allow_interruptions=True, add_to_chat_ctx=True)
        else:
            self.session.history.add_message(role="user", content="Hello? Are you there?")
            self.session.generate_reply(instructions=self._on_enter_prompt)

    async def _generate_report(self, outcome: str):
        try:
            import asyncio
            from openai import AsyncOpenAI
            from cognition.experience_store import ExperienceStore, OutcomeSignal
            from cognition.learning_engine import LearningCalibrationEngine

            # Log to ExperienceStore for continuous learning
            try:
                store = ExperienceStore(db_path="audit_experience.db")
                engine = LearningCalibrationEngine(store=store, config_path="audit_calibration.json")
                outcome_sig = OutcomeSignal(
                    session_id=self._room.name,
                    goal_achieved=("SURRENDER" in outcome.upper()),
                    negotiator_complied=True,
                    promises_broken=1 if "ESCALATED" in outcome.upper() else 0,
                    promises_kept=1 if "SURRENDER" in outcome.upper() else 0,
                    human_realism_rating=0.95,
                    final_trust=60.0 if "SURRENDER" in outcome.upper() else 10.0
                )
                store.store_outcome(self._subject_name, outcome_sig)
                engine.calibrate()
                logger.info(f"Recorded session outcome in ExperienceStore for {self._subject_name}. Calibrated learning priors.")
            except Exception as e_store:
                logger.warning(f"Failed to record in ExperienceStore: {e_store}")

            client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.environ.get("GROQ_API_KEY"))
            
            chat_history = ""
            for item in self.session.history.messages():
                chat_history += f"{item.role}: {item.content}\n"
                
            prompt = f"Analyze this crisis negotiation transcript where the outcome was: {outcome}. Give a brief grading summary of the negotiator's performance on Empathy, Active Listening, and De-escalation (A-F scale), followed by 2 sentences of advice:\n\n{chat_history}"
            
            response = await client.chat.completions.create(
                model="qwen/qwen3.8-27b", 
                messages=[{"role": "user", "content": prompt}],
                extra_body={"reasoning_format": "hidden"}
            )
            report = response.choices[0].message.content
            
            await self._room.local_participant.publish_data(
                json.dumps({"type": "report", "content": report}).encode("utf-8"),
                reliable=True,
            )
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")

server = AgentServer(
    job_executor_type=JobExecutorType.THREAD,
    load_threshold=2.0,
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8081)),
)

@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    t0 = time.time()
    logger.info("Initializing Negotiate-It Agent...")
    
    room_name = ctx.room.name.lower()
    
    voice_preamble = (
        "You are a real, terrified human being trapped in a life-or-death crisis. "
        "You are talking over a phone line to a crisis negotiator outside. "
        "Your responses will be spoken aloud in real time over the phone line. "
        "Your heart is hammering against your ribs. You are desperate, raw, volatile, and breathless.\n\n"
    )

    meta = {}
    try:
        if ctx.room.metadata:
            meta = json.loads(ctx.room.metadata)
            logger.info(f"Loaded metadata from ctx.room.metadata: {meta.get('name')}")
        elif hasattr(ctx, 'job') and ctx.job and ctx.job.room and ctx.job.room.metadata:
            meta = json.loads(ctx.job.room.metadata)
            logger.info(f"Loaded metadata from ctx.job.room.metadata: {meta.get('name')}")
        elif hasattr(ctx, 'job') and ctx.job and ctx.job.participant and ctx.job.participant.metadata:
            meta = json.loads(ctx.job.participant.metadata)
            logger.info(f"Loaded metadata from ctx.job.participant.metadata: {meta.get('name')}")
        else:
            from livekit.api import ListRoomsRequest
            room_res = await ctx.api.room.list_rooms(ListRoomsRequest(names=[ctx.room.name]))
            if room_res.rooms and room_res.rooms[0].metadata:
                meta = json.loads(room_res.rooms[0].metadata)
                logger.info(f"Loaded room metadata via API: {meta.get('name')}, {meta.get('gender')}")
    except Exception as e:
        logger.warning(f"Failed to load room metadata: {e}")

    # If metadata was still pending propagation, check participants or retry briefly
    if not meta:
        for _ in range(5):
            for p in ctx.room.remote_participants.values():
                if p.metadata:
                    try:
                        meta = json.loads(p.metadata)
                        logger.info(f"Loaded metadata from participant {p.identity}: {meta.get('name')}")
                        break
                    except Exception:
                        pass
            if meta:
                break
            if ctx.room.metadata:
                try:
                    meta = json.loads(ctx.room.metadata)
                    logger.info(f"Loaded metadata from ctx.room.metadata on retry: {meta.get('name')}")
                    break
                except Exception:
                    pass
            await asyncio.sleep(0.2)
        
    meta_lower = {str(k).lower(): v for k, v in meta.items()}
    difficulty = meta_lower.get("difficulty", "medium")
    diff_instruction = ""
    if difficulty == "low":
        diff_instruction = "You are overwhelmed and looking for a way out. If the negotiator shows basic empathy and makes a reasonable promise, you will quickly lower your guard and want to surrender."
    elif difficulty == "high":
        diff_instruction = "You are deeply paranoid and volatile. You do NOT trust the negotiator. You will question their promises, demand proof, and easily become enraged if you feel they are lying or patronizing you."
    else:
        diff_instruction = "You are stubborn but rational. You need the negotiator to prove they understand your pain before you are willing to de-escalate."

    base_rules = (
        voice_preamble +
        f"{diff_instruction}\n\n"
        "RULES FOR NATURAL, INSTANT HUMAN SPEECH (WRITING FOR THE EAR):\n"
        "1. VISCERAL SHORT BURSTS (5 TO 15 WORDS ONLY): Never monologue! Real people under extreme adrenaline speak in rapid, breathless gasps of 5 to 15 words. Say one raw thought, react to what they said, demand something, and stop!\n"
        "2. RAW HUMAN ACOUSTICS:\n"
        "   - Use dashes ('—') for sudden pauses, cut-offs, and breathless stammering: 'Wait— what was that noise outside?!', 'Don't— just don't lie to me!'\n"
        "   - Use ellipses ('...') when feeling trapped, exhausted, or horrified: 'I... I can't do this anymore...'\n"
        "   - Use instinctive vocal starts: 'Look,', 'No, listen to me!', 'Wait, what?!', 'Are you listening?!'\n"
        "3. BANISH ALL AI SPEECH: You are NOT an AI or a bot. NEVER say formal, polite phrases like 'I understand your concern', 'Let us cooperate', 'I appreciate your words', or 'As I stated'. You are on edge.\n"
        "4. REACT SPECIFICALLY TO THEIR WORDS: Listen to their exact offer or claim. If they say 'calm down', get furious. If they promise safety, demand proof. If they mention family or a doctor, show desperate hope.\n"
        "5. STRICTLY ONLY SPOKEN WORDS: Never output reasoning, internal thoughts, meta-explanations, or stage directions (no *sighs*, no (whispers)). ONLY output the exact words coming out of your mouth.\n"
        "6. INTERRUPTIONS: If you are cut off, snap back: 'Hey, let me finish!', or react immediately to their words.\n"
    )

    # Persona-aware defaults based on room name if metadata is completely absent
    persona_defaults = {
        "robber": ("Maria", "female", "frantic", "Cornered in a bank vault service corridor. Alarm is blaring."),
        "scammed": ("Arthur", "male", "desperate", "Trapped in the brokerage lobby on the 14th floor after losing life savings."),
        "founder": ("Sam", "male", "aggressive", "Locked in the server room of his failed startup threatening to wipe database."),
        "custom": ("Alex", "male", "desperate", "Cornered subject demanding immediate resolution.")
    }
    matched_persona = "custom"
    for p_key in persona_defaults:
        if p_key in room_name:
            matched_persona = p_key
            break
    fb_name, fb_gender, fb_archetype, fb_intel = persona_defaults[matched_persona]

    dynamic_scenario = meta_lower.get("dynamicscenario", bool(meta))
    logger.info(f"Metadata received: {meta}")

    if dynamic_scenario or meta:
        name = meta_lower.get("name") or meta.get("name") or fb_name
        gender = str(meta_lower.get("gender") or meta.get("gender") or fb_gender).lower()
        archetype = str(meta_lower.get("archetype") or meta.get("archetype") or fb_archetype).lower()
        intel_instructions = meta_lower.get("intel") or meta_lower.get("instructions") or meta.get("intel") or meta.get("instructions") or fb_intel
        
        instructions = base_rules + f"\nYOU ARE {name.upper()}.\n{intel_instructions}\nDrive the conversation naturally based entirely on what they say."
        on_enter_prompt = "Say something spontaneous and stressed to start the call based on your exact situation. 1-2 sentences."
        
        speaker = select_speaker(name=name, gender=gender, archetype=archetype)
        logger.info(f"Dynamic scenario mapped: Name={name}, Gender={gender}, Archetype={archetype} -> Speaker={speaker}")
    else:
        name = fb_name
        gender = fb_gender
        archetype = fb_archetype
        instructions = base_rules + f"\nYOU ARE {name.upper()}.\n{fb_intel}\nDrive the conversation naturally based entirely on what they say."
        on_enter_prompt = "Say something spontaneous and stressed to start the call. 1-2 sentences."
        speaker = select_speaker(name=name, gender=gender, archetype=archetype)
        logger.info(f"Fallback persona mapped: Name={name}, Gender={gender} -> Speaker={speaker}")

    opening_line = meta_lower.get("openingline") or meta_lower.get("opening_line") or meta.get("openingLine") or meta.get("opening_line") or ""
    if not opening_line:
        if archetype in ("frantic", "desperate"):
            opening_line = "Don't you dare come any closer! Stay back!"
        elif archetype == "aggressive":
            opening_line = "I know what you're trying to do! Tell your officers to back off right now!"
        elif archetype == "cold":
            opening_line = "You shouldn't have called this line. Who authorized this?"
        else:
            opening_line = "Stay back! Don't you dare come in here!"

    logger.info(f"[TIMING] metadata parsed + instructions built in {time.time()-t0:.2f}s | opening_line='{opening_line}'")

    session = AgentSession(
        vad=PRELOADED_VAD,
        turn_handling={
            "endpointing": {"min_delay": 0.12, "max_delay": 0.55},
            "interruption": {
                "enabled": True,
                "mode": "vad",
                "min_duration": 0.28,
                "resume_false_interruption": True,
                "false_interruption_timeout": 1.2,
            },
            "preemptive_generation": {"enabled": False},
        },
        tts_text_transforms=["filter_markdown", "filter_emoji", filter_inner_thoughts],
        stt=openai.STT(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY"),
            model="whisper-large-v3-turbo",
            temperature=0.0,
            language="en",
        ),
        llm=openai.LLM(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY"),
            model="qwen/qwen3.8-27b",
            temperature=0.75,
            max_completion_tokens=45,
            extra_body={"reasoning_format": "hidden"},
            timeout=8.0,
            max_retries=2
        ),
        tts=rime.TTS(
            model="mistv3",
            speaker=speaker,
            use_websocket=True,
            reduce_latency=True,
            speed_alpha=1.05,
        ),
    )
    logger.info(f"[TIMING] session created in {time.time()-t0:.2f}s")

    await session.start(
        agent=NegotiatorAgent(instructions=instructions, on_enter_prompt=on_enter_prompt, room=ctx.room, subject_name=name, opening_line=opening_line, archetype=archetype),
        room=ctx.room,
    )
    logger.info(f"[TIMING] session.start() completed in {time.time()-t0:.2f}s — agent is now live")

if __name__ == "__main__":
    cli.run_app(server)
