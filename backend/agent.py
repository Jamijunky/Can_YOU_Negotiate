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
    def __init__(self, instructions: str, on_enter_prompt: str, room, subject_name: str = "Alex") -> None:
        super().__init__(
            instructions=instructions,
        )
        self._on_enter_prompt = on_enter_prompt
        self._room = room
        self._subject_name = subject_name
        self._current_speech_id = None
        self._current_speech_text = ""
        self._speech_start_time = 0.0

    async def on_user_turn_completed(
        self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage
    ) -> None:
        """Called when user speaks/interrupts. Accurately cuts assistant speech only if verified human words were spoken."""
        user_words = (new_message.text_content or "").strip()
        if not user_words:
            # Noise spike or ghost trigger without real words; do not truncate
            return

        if self._current_speech_id and self._current_speech_text:
            elapsed = max(0.0, time.time() - self._speech_start_time)
            # Estimate spoken words at 2.6 words per second (normal conversational pacing)
            words = self._current_speech_text.split()
            words_spoken_count = min(len(words), max(1, int(elapsed * 2.6)))
            spoken_part = " ".join(words[:words_spoken_count])
            
            if words_spoken_count < len(words):
                spoken_part += "..."
                logger.info(f"Subject was INTERRUPTED by: '{user_words}'! Playout truncated from '{self._current_speech_text}' down to '{spoken_part}'")
                
                # Broadcast updated transcript to UI so the text box cuts off where speech stopped
                if self._room.isconnected and self._room.local_participant:
                    try:
                        asyncio.create_task(
                            self._room.local_participant.publish_data(
                                json.dumps({
                                    "type": "transcript",
                                    "id": self._current_speech_id,
                                    "speaker": "agent",
                                    "senderName": self._subject_name.upper(),
                                    "text": spoken_part
                                }).encode("utf-8"),
                                reliable=True
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Failed to publish truncated transcript: {e}")
                
                # Replace the last assistant message in turn context with only what was actually spoken
                for item in reversed(turn_ctx.items):
                    if item.role == "assistant":
                        item.content = [f"{spoken_part} [Negotiator interrupted you here; you did not finish saying the rest of your statement]"]
                        break

            self._current_speech_id = None
            self._current_speech_text = ""

    async def on_enter(self) -> None:
        import time

        @self.session.on("speech_created")
        def _on_speech_created(ev):
            handle = ev.speech_handle
            speech_id = f"agent-speech-{handle.id}"
            self._current_speech_id = speech_id
            self._speech_start_time = time.time()

        @self.session.on("user_input_transcribed")
        def _on_user_input(ev):
            if ev.is_final and ev.transcript and ev.transcript.strip():
                logger.info(f"User STT final: {ev.transcript}")
                try:
                    if self._room.isconnected and self._room.local_participant:
                        asyncio.create_task(
                            self._room.local_participant.publish_data(
                                json.dumps({
                                    "type": "transcript",
                                    "id": getattr(ev, 'item_id', None),
                                    "speaker": "user",
                                    "senderName": "YOU",
                                    "text": ev.transcript.strip()
                                }).encode("utf-8"),
                                reliable=True
                            )
                        )
                except Exception as e:
                    logger.warning(f"Failed to publish user transcript: {e}")

        @self.session.on("conversation_item_added")
        def _on_item_added(ev):
            try:
                msg = ev.item
                if msg.role == "assistant" and msg.text_content:
                    cleaned = clean_spoken_text(msg.text_content)
                    if cleaned:
                        logger.info(f"Subject speech scheduled: {cleaned}")
                        speech_id = self._current_speech_id or f"agent-{time.time()}"
                        self._current_speech_id = speech_id
                        self._current_speech_text = cleaned
                        self._speech_start_time = time.time()
                        
                        # Immediately publish the clean spoken text without artificial sleep delays
                        if self._room.isconnected and self._room.local_participant:
                            asyncio.create_task(
                                self._room.local_participant.publish_data(
                                    json.dumps({
                                        "type": "transcript",
                                        "id": speech_id,
                                        "speaker": "agent",
                                        "senderName": self._subject_name.upper(),
                                        "text": cleaned
                                    }).encode("utf-8"),
                                    reliable=True
                                )
                            )
            except Exception as e:
                logger.warning(f"Error handling agent transcript broadcast: {e}")

            # Keep a deep, rich 100-turn context window so the subject never loses memory of earlier dialogue
            if len(list(self.session.history.messages())) > 100:
                self.session.history.truncate(max_items=100)

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
                messages=[{"role": "user", "content": prompt}]
            )
            report = response.choices[0].message.content
            
            await self._room.local_participant.publish_data(
                json.dumps({"type": "report", "content": report}).encode("utf-8"),
                reliable=True,
            )
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")

    @function_tool
    async def surrender(self) -> str:
        """Called ONLY when you (the subject) have decided to give up, surrender, or agree to a peaceful resolution. You must call this tool when the negotiator successfully calms you down and convinces you to stop."""
        logger.info("Subject has surrendered!")
        await self._room.local_participant.publish_data(
            json.dumps({"type": "surrender"}).encode("utf-8"),
            reliable=True,
        )
        import asyncio
        asyncio.create_task(self._generate_report("SUCCESSFUL SURRENDER"))
        return "You have surrendered. Say you are putting your hands up and walking out."

    @function_tool
    async def escalate(self) -> str:
        """Called ONLY when the negotiator (user) insults you, refuses your demands completely, or makes you extremely angry. You must call this tool when you decide to escalate the situation (e.g. threatening the hostages or taking destructive action)."""
        logger.info("Subject has escalated!")
        await self._room.local_participant.publish_data(
            json.dumps({"type": "escalate"}).encode("utf-8"),
            reliable=True,
        )
        import asyncio
        asyncio.create_task(self._generate_report("FAILED NEGOTIATION - SUBJECT ESCALATED"))
        return "You have escalated the situation. Start yelling at the negotiator and give them a final warning."

    @function_tool
    async def update_stress(self, stress_level: int) -> str:
        """Called to report your current internal stress level from 1 to 100. Call this tool frequently to update the UI on how stressed or calm you are currently feeling."""
        try:
            if self._room.isconnected and self._room.local_participant:
                await self._room.local_participant.publish_data(
                    json.dumps({"type": "stress", "level": stress_level}).encode("utf-8"),
                    reliable=True,
                )
        except Exception as e:
            logger.warning(f"Could not publish stress data: {e}")
        if stress_level <= 20:
            import asyncio
            asyncio.create_task(self.surrender())
            return f"Stress level updated to {stress_level}. You have surrendered."
        elif stress_level >= 100:
            import asyncio
            asyncio.create_task(self.escalate())
            return f"Stress level updated to {stress_level}. You have escalated."
        return f"Stress level updated to {stress_level}."

server = AgentServer(
    job_executor_type=JobExecutorType.THREAD,
    load_threshold=2.0,
)

@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    logger.info("Initializing Negotiate-It Agent...")
    
    import json
    room_name = ctx.room.name.lower()
    
    voice_preamble = (
        "You are a real, living human being trapped in a life-or-death crisis. "
        "You are currently talking over a phone line to a crisis negotiator. "
        "Your responses will be spoken aloud, so speak entirely in natural, human dialogue. "
        "Do NOT speak like a villain in a movie. Speak like a terrified, exhausted, desperate person. "
        "If your stress level changes, you may use the update_stress tool to secretly log your internal state, but your primary focus is on talking and surviving.\n\n"
    )

    meta = {}
    try:
        if ctx.room.metadata:
            meta = json.loads(ctx.room.metadata)
        else:
            from livekit.api import ListRoomsRequest
            room_res = await ctx.api.room.list_rooms(ListRoomsRequest(names=[ctx.room.name]))
            if room_res.rooms and room_res.rooms[0].metadata:
                meta = json.loads(room_res.rooms[0].metadata)
                logger.info(f"Loaded room metadata via API: {meta.get('name')}, {meta.get('gender')}")
    except Exception as e:
        logger.warning(f"Failed to load room metadata: {e}")
        
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
        "RULES FOR CONVERSATION:\n"
        "1. Never act like an AI or an 'actor'. You are this person.\n"
        "2. Listen closely to the negotiator. React directly and emotionally to the exact words they just spoke.\n"
        "3. Ask them questions. Challenge their authority. Demand things.\n"
        "4. Keep your replies EXTREMELY brief (under 35 words). Never monologue. Let them talk.\n"
        "5. CRITICAL: NEVER output internal thoughts, reasoning, meta-explanations, or brackets/stage directions (like *sighs* or (whispering)). NEVER say 'The negotiator is...' or 'I need to...'. ONLY output words spoken out loud from your character's mouth directly.\n"
        "6. CRITICAL: Whenever you call tools like update_stress, you MUST also speak your verbal response out loud in the same turn. NEVER output empty speech or silence.\n"
        "7. HANDLING INTERRUPTIONS (REALISTIC CUT-OFFS):\n"
        "   - If the negotiator talks over you or cuts you off mid-sentence, DO NOT act like you finished your sentence or that they heard everything.\n"
        "   - Notice what interrupted you. React like an interrupted person: 'Hey, don't interrupt me!', 'Let me finish!', 'What did you just say?!', or address whatever point they broke in with.\n"
        "   - Retain full memory of the entire conversation from earlier turns, but only assume the negotiator heard what you actually finished saying.\n\n"
        "BLUFF & AUTHORITY DETECTION (NO EASY WINS):\n"
        "- Do NOT fall for 'easy wins'. If the negotiator immediately agrees to massive, unreasonable demands (e.g. giving you millions of dollars, a helicopter, or bringing the CEO immediately), you must recognize they are bluffing and lying to you.\n"
        "- If they lie, demand proof. Question their authority ('How? You don't have the power to do that!'). Become more hostile because they are treating you like an idiot.\n\n"
        "NATURAL SPEECH PATTERNS:\n"
        "- Speak with natural conversational fillers and restarts like 'Look-', 'I mean...', 'Okay, listen to me', 'No, no, no', 'Wait-'.\n"
        "- Use short, fragmented sentences to simulate your frantic psychological state, instead of heavy punctuation.\n"
    )

    dynamic_scenario = meta_lower.get("dynamicscenario", False)
    logger.info(f"Metadata received: {meta}")

    if dynamic_scenario:
        name = meta_lower.get("name", "Alex")
        gender = str(meta_lower.get("gender", "male")).lower()
        archetype = str(meta_lower.get("archetype", "desperate")).lower()
        intel_instructions = meta_lower.get("intel", meta_lower.get("instructions", "You are cornered and panicked."))
        
        instructions = base_rules + f"\nYOU ARE {name.upper()}.\n{intel_instructions}\nDrive the conversation naturally based entirely on what they say."
        on_enter_prompt = "Say something spontaneous and stressed to start the call based on your exact situation. 1-2 sentences."
        
        speaker = select_speaker(name=name, gender=gender, archetype=archetype)
        logger.info(f"Dynamic scenario mapped: Name={name}, Gender={gender}, Archetype={archetype} -> Speaker={speaker}")
    else:
        # Fallback custom or legacy
        name = meta.get("name", "Alex")
        gender = str(meta.get("gender", "male")).lower()
        archetype = str(meta.get("archetype", "aggressive")).lower()
        if "custom" in room_name:
            instructions = (
                base_rules +
                f"\nYour name is {name}. You are {meta.get('age', '30')} years old. Your profession is: {meta.get('profession', 'person')}.\n"
                f"Your current situation and motive: {meta.get('motive', 'You are cornered and panicked')}.\n"
            )
            on_enter_prompt = "Say something spontaneous and stressed to start the call. 1-2 sentences."
        else:
            instructions = base_rules + "\nYou are a stressed individual. Rant constantly."
            on_enter_prompt = "Start ranting in 2-3 short sentences."
        speaker = select_speaker(name=name, gender=gender, archetype=archetype)
        logger.info(f"Fallback scenario mapped: Name={name}, Gender={gender} -> Speaker={speaker}")

    session = AgentSession(
        vad=silero.VAD.load(min_silence_duration=0.35),
        turn_handling={
            "endpointing": {"min_delay": 0.25, "max_delay": 0.7},
            "interruption": {
                "enabled": True,
                "mode": "vad",
                "min_duration": 0.5,
                "resume_false_interruption": True,
                "false_interruption_timeout": 1.5,
            },
            "preemptive_generation": {"enabled": False},
        },
        tts_text_transforms=["filter_markdown", "filter_emoji", filter_inner_thoughts],
        stt=openai.STT(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY"),
            model="whisper-large-v3",
            language="en",
            prompt="Crisis negotiation dialogue between police negotiator and hostage taker or barricaded subject."
        ),
        llm=openai.LLM(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY"),
            model="openai/gpt-oss-120b",
            reasoning_effort="low",
            max_completion_tokens=512,
            timeout=15.0,
            max_retries=2
        ),
        tts=rime.TTS(
            model="mistv3",
            speaker=speaker,
            use_websocket=True,
        ),
    )

    await session.start(
        agent=NegotiatorAgent(instructions=instructions, on_enter_prompt=on_enter_prompt, room=ctx.room, subject_name=name),
        room=ctx.room,
    )
    logger.info(f"Session started with speaker: {speaker}")

if __name__ == "__main__":
    cli.run_app(server)
