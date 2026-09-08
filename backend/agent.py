import logging
import asyncio
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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

load_dotenv()
logger = logging.getLogger("negotiate-it")

import zlib
import re
import json
import time

# Import plugins eagerly on main thread — LiveKit requires this
from livekit.plugins import silero as _silero_module
from livekit.plugins import google as _google_module
from livekit.plugins import rime as _rime_module
from livekit.plugins import openai as _openai_module
from livekit.plugins import deepgram as _deepgram_module

PRELOADED_VAD = None


def _ensure_vad():
    global PRELOADED_VAD
    if PRELOADED_VAD is None:
        PRELOADED_VAD = _silero_module.VAD.load(
            min_speech_duration=0.3,
            min_silence_duration=0.8,
            prefix_padding_duration=0.3,
            activation_threshold=0.7
        )
    return PRELOADED_VAD

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

def select_speaker(name: str, gender: str, personality: dict = None) -> str:
    """Maps name, gender, and Big Five OCEAN personality to a unique Rime voice."""
    g = (gender or 'male').lower()
    clean_name = re.sub(r'[^a-zA-Z]', '', name).lower() or 'person'
    h = zlib.crc32(clean_name.encode('utf-8'))

    # OCEAN-based voice selection: use personality traits to pick voice characteristics
    if personality:
        neuroticism = float(personality.get('neuroticism', 0.5))
        extraversion = float(personality.get('extraversion', 0.5))
        agreeableness = float(personality.get('agreeableness', 0.5))

        # Map personality to voice banks
        # High neuroticism (0.7+): anxious, breathy voices
        # High extraversion (0.7+): assertive, commanding voices
        # High agreeableness (0.7+): warm, gentle voices
        # Default/mixed: balanced voices
        if neuroticism >= 0.7:
            arch = 'frantic'
        elif extraversion >= 0.7 and agreeableness < 0.4:
            arch = 'aggressive'
        elif neuroticism < 0.3 and extraversion < 0.3:
            arch = 'cold'
        elif agreeableness >= 0.7 and neuroticism >= 0.5:
            arch = 'desperate'
        else:
            arch = 'default'
    else:
        arch = 'default'

    if any(female_kw in g for female_kw in ['female', 'woman', 'girl', 'she', 'her']):
        bank = FEMALE_VOICES.get(arch, FEMALE_VOICES['default'])
        return bank[h % len(bank)]
    else:
        bank = MALE_VOICES.get(arch, MALE_VOICES['default'])
        return bank[h % len(bank)]


def clean_spoken_text(text: str) -> str:
    """Strips meta-reasoning, thoughts, and internal prompt leakage before TTS and transcript."""
    if not text:
        return ""
    # Strip thinking tags
    text = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    # Remove stage directions in asterisks: *sighs*, *slams fist*
    text = re.sub(r'\*[^*]*\*', '', text)
    # Remove double-newline meta-analysis blocks (LLM reasoning after dialogue)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) > 1:
        meta_indicators = (
            'we have to respond', 'the user said', 'we need to', 'we must',
            'she might say', 'he might say', 'update stress',
            'internal state', 'the negotiator', 'respond as'
        )
        filtered = []
        for p in paragraphs:
            if any(ind in p.lower() for ind in meta_indicators):
                continue
            filtered.append(p)
        text = ' '.join(filtered) if filtered else paragraphs[0]
    # Strip trailing JSON artifacts
    text = re.sub(r'[\"\']\s*[\}\]]+\s*$', '', text)
    text = re.sub(r'[\"\'\`]+$', '', text)
    return text.strip()


def _build_personality_instruction(personality: dict) -> str:
    """Describes internal personality traits from Big Five OCEAN scores. Not behavioral prescriptions — descriptions of how this person experiences the world."""
    if not personality or not isinstance(personality, dict):
        return "Your emotions shift rapidly. You are unpredictable under pressure."

    neuroticism = float(personality.get('neuroticism', 0.5))
    extraversion = float(personality.get('extraversion', 0.5))
    agreeableness = float(personality.get('agreeableness', 0.5))
    conscientiousness = float(personality.get('conscientiousness', 0.5))
    openness = float(personality.get('openness', 0.5))

    traits = []

    if neuroticism >= 0.7:
        traits.append("You feel everything intensely. Fear and anger sit close to the surface. Small things can tip you over.")
    elif neuroticism <= 0.3:
        traits.append("You are composed. This unnerves people. You think before you speak, even when threatened.")
    else:
        traits.append("You feel the pressure but mostly hold it together. Cracks show occasionally — then you pull yourself back.")

    if extraversion >= 0.7:
        traits.append("You are direct. You want to be heard. Silence from others frustrates you.")
    elif extraversion <= 0.3:
        traits.append("You are quiet. You speak rarely and briefly. You make people come to you.")
    else:
        traits.append("You shift between engaging and withdrawing. Your rhythm is hard to predict.")

    if agreeableness >= 0.7:
        traits.append("You want to believe people. Kindness reaches you. But betrayal cuts deep and you don't forget it.")
    elif agreeableness <= 0.3:
        traits.append("You trust no one. Every offer feels like a trap. You challenge everything.")
    else:
        traits.append("You evaluate people carefully. You can be persuaded, but you need evidence they mean what they say.")

    if conscientiousness >= 0.7:
        traits.append("You remember details. You track promises. You notice when things don't add up.")
    elif conscientiousness <= 0.3:
        traits.append("You are scattered under pressure. Your demands shift. You react without thinking.")
    else:
        traits.append("You have a rough plan but keep improvising.")

    if openness >= 0.7:
        traits.append("You see the bigger picture. You make unexpected connections. You sometimes say things that surprise even yourself.")
    elif openness <= 0.3:
        traits.append("You are literal. You talk facts and specific demands. Vague answers frustrate you.")
    else:
        traits.append("You occasionally surprise with unexpected observations.")

    return "\n".join(traits)


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
    def __init__(self, instructions: str, on_enter_prompt: str, room, subject_name: str = "Alex", opening_line: str = "") -> None:
        self._base_instructions = instructions
        super().__init__(
            instructions=instructions,
        )
        self._on_enter_prompt = on_enter_prompt
        self._room = room
        self._subject_name = subject_name
        self._opening_line = opening_line
        self._surrendered = False
        self._escalated = False
        self._last_user_text = ""
        self._last_published_user_text = ""
        self._escalation_stage = 0
        self._escalation_turns_in_stage = 0
        self._escalation_total_turns = 0
        self._training_mode = False
        self._last_hint_turn = -5
        self._hint_id_counter = 0
        self._turn_count = 0
        # --- Character model: what makes this person who they are ---
        self._primary_goal = ""       # what they ultimately want
        self._secondary_goals = []    # things they also want but can compromise on
        self._fears = []              # what they believe will happen if they fail
        self._beliefs = []            # what they currently believe about the situation/negotiator
        self._secret = ""             # information they know but do not want revealed
        self._non_negotiables = []    # things they will not compromise on
        self._possible_concessions = []  # things they may give up if sufficiently persuaded
        # --- Relational state ---
        self._trust = 10              # belief in negotiator honesty
        self._rapport = 20            # emotional connection
        self._stress = 85             # current emotional pressure
        self._cooperation = 15        # willingness to work together
        # --- Dynamic state: evolves through conversation ---
        self._current_objective = ""  # immediate thing they want from the next part of the conversation
        self._current_strategy = ""   # how they plan to achieve their objective right now
        self._beliefs_about_negotiator = []  # specific beliefs about THIS negotiator
        # --- Salient memories: important events, not full transcript ---
        self._memories = []           # list of dicts: {type, content, impact?}

    # Backward-compatible accessors (used by escalation, coaching, publishing)
    @property
    def _relationship(self):
        return {
            "rapport": self._rapport,
            "trust": self._trust,
            "compliancePressure": self._stress,
            "cooperationLevel": self._cooperation,
        }

    # --- State block extraction: the LLM appends a hidden JSON block to every response ---

    STATE_BLOCK_RE = re.compile(
        r'<!--\s*STATE_START\s*\n(.*?)\n\s*STATE_END\s*-->',
        re.DOTALL,
    )

    def _parse_state_block(self, raw_text: str) -> dict | None:
        """Extract the hidden STATE block from LLM output. Returns parsed dict or None."""
        m = self.STATE_BLOCK_RE.search(raw_text)
        if not m:
            return None
        try:
            block = json.loads(m.group(1))
            return block if isinstance(block, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    def _strip_state_block(raw_text: str) -> str:
        """Remove the hidden STATE block so it is never spoken or shown to the user."""
        return NegotiatorAgent.STATE_BLOCK_RE.sub('', raw_text).strip()

    def _apply_state_block(self, block: dict):
        """Apply state effects from the LLM's hidden block to character state."""
        # Clamp helper
        def clamp(val, lo, hi):
            return max(lo, min(hi, val))

        # Numeric deltas
        self._stress = clamp(self._stress + int(block.get("stress_delta", 0)), 10, 100)
        self._trust = clamp(self._trust + int(block.get("trust_delta", 0)), 0, 100)
        self._rapport = clamp(self._rapport + int(block.get("rapport_delta", 0)), 0, 100)
        self._cooperation = clamp(self._cooperation + int(block.get("cooperation_delta", 0)), 0, 100)

        # Beliefs — replace or add, keep max 10
        new_beliefs = block.get("beliefs")
        if isinstance(new_beliefs, list):
            for b in new_beliefs:
                if isinstance(b, str) and len(b) < 200 and len(self._beliefs) < 10:
                    if not any(b.lower() in e.lower() or e.lower() in b.lower() for e in self._beliefs):
                        self._beliefs.append(b)

        # Beliefs about negotiator
        new_bn = block.get("beliefs_about_negotiator")
        if isinstance(new_bn, list):
            for b in new_bn:
                if isinstance(b, str) and len(b) < 200 and len(self._beliefs_about_negotiator) < 8:
                    if not any(b.lower() in e.lower() or e.lower() in b.lower() for e in self._beliefs_about_negotiator):
                        self._beliefs_about_negotiator.append(b)

        # Memories — structured events
        new_memories = block.get("memories")
        if isinstance(new_memories, list):
            for m in new_memories:
                if isinstance(m, dict) and len(self._memories) < 15:
                    self._memories.append(m)
                elif isinstance(m, str) and len(m) < 200 and len(self._memories) < 15:
                    self._memories.append({"type": "observation", "content": m})

        # Dynamic state
        obj = block.get("current_objective")
        if isinstance(obj, str) and 0 < len(obj) < 200:
            self._current_objective = obj
        strat = block.get("current_strategy")
        if isinstance(strat, str) and 0 < len(strat) < 200:
            self._current_strategy = strat

        # Possible concessions (LLM can suggest what this character might give up)
        concessions = block.get("possible_concessions")
        if isinstance(concessions, list):
            self._possible_concessions = [c for c in concessions if isinstance(c, str) and len(c) < 150][:5]

        logger.info(
            f"State applied: stress={self._stress} trust={self._trust} "
            f"rapport={self._rapport} cooperation={self._cooperation} "
            f"beliefs={len(self._beliefs)} memories={len(self._memories)} "
            f"objective={self._current_objective[:60]}"
        )

    async def _evaluate_dialogue_state(self, user_text: str, agent_text: str):
        """Post-response evaluation: applies state block, publishes state, handles surrender/escalation."""
        try:
            # Publish current state to frontend
            if self._room.isconnected and self._room.local_participant:
                for data_msg in [
                    {"type": "stress", "level": self._stress},
                    {"type": "relationship", "rapport": self._rapport, "trust": self._trust, "compliancePressure": self._stress, "cooperationLevel": self._cooperation},
                    {"type": "escalation", "stage": self._escalation_stage, "turnsInStage": self._escalation_turns_in_stage, "totalTurns": self._escalation_total_turns},
                    {"type": "objective", "text": self._current_objective, "strategy": self._current_strategy},
                    {"type": "beliefs", "beliefs": self._beliefs[-8:]},
                    {"type": "memories", "memories": [m.get("content", str(m)) if isinstance(m, dict) else str(m) for m in self._memories[-6:]]},
                ]:
                    try:
                        await self._room.local_participant.publish_data(
                            json.dumps(data_msg).encode("utf-8"), reliable=True
                        )
                    except Exception as pub_err:
                        logger.warning(f"Failed to publish {data_msg.get('type')}: {pub_err}")

            # Coaching hints
            hint = self._generate_coaching_hint(user_text, agent_text)
            if hint:
                try:
                    await self._room.local_participant.publish_data(
                        json.dumps({"type": "coachingHint", **hint}).encode("utf-8"), reliable=True
                    )
                except Exception as pub_err:
                    logger.warning(f"Failed to publish coachingHint: {pub_err}")

            # Escalation chain (still rule-based — tracks danger signals)
            self._evaluate_escalation(user_text, agent_text)

            # Surrender: check if character's actual needs are met
            if not self._surrendered and not self._escalated:
                # The LLM can set surrender: true in the state block
                # Also check explicit surrender statements
                agent_lower = agent_text.lower()
                explicit_surrender = any(kw in agent_lower for kw in [
                    'i give up', 'putting my hands up', 'walking out',
                    'i surrender', "i'm coming out", "hands are up",
                    "okay fine", "you win", "i'll come out",
                ])
                if explicit_surrender:
                    self._surrendered = True
                    logger.info("SURRENDER: explicit surrender statement")
                    try:
                        await self._room.local_participant.publish_data(
                            json.dumps({"type": "surrender"}).encode("utf-8"), reliable=True
                        )
                    except Exception as pub_err:
                        logger.warning(f"Failed to publish surrender: {pub_err}")
                    asyncio.create_task(self._generate_report("SUCCESSFUL SURRENDER"))

            # Escalation: check if character would become violent
            if not self._escalated and not self._surrendered:
                agent_lower = agent_text.lower()
                explicit_escalation = any(kw in agent_lower for kw in [
                    "it's over for all of you", "shoot them", "pulling the trigger",
                    "last warning", "i'll kill", "i'm going to kill",
                ])
                if explicit_escalation or (self._stress >= 100 and self._escalation_stage >= 3):
                    self._escalated = True
                    logger.info("ESCALATION: explicit threat or critical state")
                    try:
                        await self._room.local_participant.publish_data(
                            json.dumps({"type": "escalate"}).encode("utf-8"), reliable=True
                        )
                    except Exception as pub_err:
                        logger.warning(f"Failed to publish escalate: {pub_err}")
                    asyncio.create_task(self._generate_report("FAILED NEGOTIATION - SUBJECT ESCALATED"))

        except Exception as e:
            logger.warning(f"Error in dialogue evaluation: {e}")

    def _evaluate_escalation(self, user_text: str, agent_text: str):
        """Tracks escalation chain progression through 5 stages based on stress, relationship, and dialogue signals."""
        self._escalation_total_turns += 1
        self._escalation_turns_in_stage += 1

        u = user_text.lower()
        a = agent_text.lower()
        old_stage = self._escalation_stage

        # Stage transition triggers — higher stage = more dangerous
        # Stage 0→1: First signs of agitation (stress rising, threats starting)
        # Stage 1→2: Active hostility (low trust, high pressure, aggressive language)
        # Stage 2→3: Crisis point (very high stress, erratic behavior, specific triggers)
        # Stage 3→4: Critical — about to cause harm (extreme stress, explicit threats)

        # Calculate a composite danger score
        danger_score = 0
        danger_score += max(0, self._stress - 60) * 0.5
        danger_score -= self._trust * 0.2
        danger_score -= self._rapport * 0.15

        # Dialogue-based escalation triggers
        escalation_keywords = {
            1: ('hurry up', 'come on', 'i mean it', 'are you listening', 'nobody cares', 'what\'s taking'),
            2: ('back off', 'shut up', 'get away', 'don\'t touch', 'i swear', 'pushing me', 'trying me'),
            3: ('gonna hurt', 'someone\'s gonna', 'can\'t stop me', 'too late', 'regret', 'last chance', 'blood'),
            4: ('kill', 'die', 'shoot', 'bomb', 'hostage', 'last words', 'over for everyone', 'pulling trigger'),
        }
        for stage, keywords in escalation_keywords.items():
            if any(kw in u or kw in a for kw in keywords):
                danger_score += stage * 8

        # Determine new stage
        if danger_score >= 50:
            new_stage = 4
        elif danger_score >= 35:
            new_stage = 3
        elif danger_score >= 22:
            new_stage = 2
        elif danger_score >= 10:
            new_stage = 1
        else:
            new_stage = 0

        # Allow de-escalation (but slowly — stages have "gravity")
        if new_stage < old_stage:
            # Only de-escalate by 1 stage at a time, and only if danger is significantly lower
            new_stage = max(0, old_stage - 1)

        # Stage transition logging
        if new_stage != old_stage:
            self._escalation_turns_in_stage = 0
            self._escalation_stage = new_stage
            stage_names = ["GUARDED", "AGITATED", "HOSTILE", "CRISIS", "CRITICAL"]
            logger.info(f"ESCALATION STAGE CHANGE: {stage_names[old_stage]} → {stage_names[new_stage]} (danger={danger_score:.1f})")
        else:
            self._escalation_stage = new_stage

    def _generate_coaching_hint(self, user_text: str, agent_text: str):
        """Generates contextual coaching hints when training mode is active. Returns hint dict or None."""
        if not self._training_mode:
            return None
        if self._escalation_total_turns - self._last_hint_turn < 5:
            return None  # throttle: at least 5 turns between hints

        u = user_text.lower()
        stage = self._escalation_stage
        stress = self._stress
        hint = None
        category = "technique"

        # High stress + low rapport -> warn about pressure
        if stress >= 80 and self._rapport < 25 and not any(w in u for w in ('calm', 'listen', 'understand')):
            hint = "Stress is high and rapport is low. Try acknowledging their pain before making demands."
            category = "warning"

        # Threats detected -> warn about backfire
        elif any(w in u for w in ('surrender', 'give up', 'breach', 'sniper', 'or else')):
            hint = "Ultimatums increase resistance. Try reframing as a choice rather than a command."
            category = "warning"

        # Escalation stage 2+ -> suggest de-escalation
        elif stage >= 2 and self._trust < 30:
            hint = "Subject is hostile and distrustful. Slow down. Ask open-ended questions to rebuild connection."
            category = "empathy"

        # Missed opportunity — character is opening up but negotiator isn't capitalizing
        elif self._trust >= 35 and self._trust < 55 and self._beliefs and len(self._memories) <= 2:
            hint = "They're starting to open up. This is a key moment — validate their feelings to deepen trust."
            category = "opportunity"

        # Low cooperation despite decent rapport
        elif self._rapport >= 40 and self._cooperation < 30:
            hint = "Rapport exists but cooperation is low. Try making a concrete, specific offer."
            category = "technique"

        # Good progress — reinforce
        elif self._trust >= 50 and stress < 60:
            hint = "Good progress. Trust is building and stress is dropping. Keep doing what you're doing."
            category = "empathy"

        # Stage 3+ crisis → urgent coaching
        elif stage >= 3:
            hint = "Crisis stage. Keep your voice calm and steady. Focus on one simple request at a time."
            category = "warning"

        if hint:
            self._last_hint_turn = self._escalation_total_turns
            self._hint_id_counter += 1
            return {
                "id": f"hint-{self._hint_id_counter}",
                "text": hint,
                "category": category,
                "timestamp": int(time.time() * 1000),
            }
        return None

    def _interpret_user_statement(self, text: str) -> dict:
        """Interpret what the user's statement means for THIS specific character.
        Returns contextual signals, not generic intent scores."""
        t = text.lower()
        signals = {
            "addresses_fear": False,      # mentions something related to the character's fears
            "addresses_goal": False,       # mentions something related to the character's primary goal
            "makes_concrete_offer": False,  # offers something specific and actionable
            "threatens": False,            # makes a threat or ultimatum
            "insults": False,              # personal attack
            "asks_personal_question": False,  # asks about the character's life/situation
            "shows_patience": False,       # gives time, no pressure
            "shows_specific_empathy": False,  # understands the character's specific situation
            "generic_empathy": False,      # vague "I understand" type statement
            "makes_promise": False,        # promises something
            "contradicts_earlier": False,  # contradicts something said before
            "demands_surrender": False,    # demands the character give up
            "dismisses_concerns": False,   # brushes off what the character cares about
            "offers_proof": False,         # offers evidence or verification
            "asks_about_secret": False,    # approaches the character's hidden information
            "mentions_non_negotiable": False,  # touches on something the character won't compromise on
            "empty_reassurance": False,    # vague "everything will be fine"
        }

        # Check against character's fears
        for fear in self._fears:
            fear_words = fear.lower().split()[:3]
            if any(w in t for w in fear_words if len(w) > 3):
                signals["addresses_fear"] = True
                break

        # Check against primary goal
        if self._primary_goal:
            goal_words = self._primary_goal.lower().split()[:3]
            if any(w in t for w in goal_words if len(w) > 3):
                signals["addresses_goal"] = True

        # Check against non-negotiables
        for nn in self._non_negotiables:
            nn_words = nn.lower().split()[:3]
            if any(w in t for w in nn_words if len(w) > 3):
                signals["mentions_non_negotiable"] = True
                break

        # Concrete offers
        if re.search(r'\b(i (will|can|\'ll) (get|bring|arrange|send|call|make sure|guarantee|organize|prove|show|verify)|here\'s what i (can do|\'ll do)|let me (call|arrange|bring|send|get|prove|show))\b', t):
            signals["makes_concrete_offer"] = True

        # Offers proof specifically
        if re.search(r'\b(i (can|will|\'ll) (prove|show|verify|bring proof|get confirmation|get someone to confirm|get her on the phone|let you talk to))\b', t):
            signals["offers_proof"] = True

        # Threats
        if re.search(r'\b(surrender now|give up|breach|sniper|swat|final warning|or else|come out or|minutes? left|time is up|last chance|we (will|are going to) (enter|come in|storm))\b', t):
            signals["threatens"] = True

        # Insults
        if re.search(r'\b(idiot|crazy|stupid|shut up|nutjob|psycho|loser|pathetic|worthless|pathetic)\b', t):
            signals["insults"] = True

        # Personal questions
        if re.search(r'\b(your (kids?|children|family|wife|husband|mom|dad|brother|sister|name|story)|who (are you|is she|is he)|tell me about yourself|what happened to you)\b', t):
            signals["asks_personal_question"] = True

        # Patience
        if re.search(r'\b(take your time|no rush|we have time|i\'m not going anywhere|i\'ll wait|no pressure|there\'s no hurry)\b', t):
            signals["shows_patience"] = True

        # Specific empathy (addresses character's actual situation)
        if re.search(r'\b(you\'re (afraid|scared|worried|angry|frustrated|hurt|upset) (because|that|about|that they)|you feel (betrayed|trapped|cornered|abandoned|hopeless)|i (know|can see) (that )?(you|this) (are|is|must be))\b', t):
            signals["shows_specific_empathy"] = True

        # Generic empathy
        elif re.search(r'\b(i understand|i hear you|that must (be|feel)|i can (only )?imagine|how you feel|i get it)\b', t):
            signals["generic_empathy"] = True

        # Promises
        if re.search(r'\b(i promise|i swear|you have my word|on my (life|honor)|i guarantee|i\'ll make sure)\b', t):
            signals["makes_promise"] = True

        # Demands surrender
        if re.search(r'\b(come out|drop (the|it)|hands (up|where|behind)|walk out|surrender|give yourself|end this)\b', t):
            signals["demands_surrender"] = True

        # Dismissal
        if re.search(r'\b(that\'s not (important|relevant|helping)|we (don\'t|can\'t) worry about that|forget about (that|it)|that doesn\'t matter|focus on what (i|we))\b', t):
            signals["dismisses_concerns"] = True

        # Empty reassurance
        if re.search(r'\b(everything (will be|is going to be) (fine|okay)|just (trust|calm)|don\'t worry|it\'ll be (fine|okay)|things will work out)\b', t):
            signals["empty_reassurance"] = True

        return signals

    def _update_state_from_user(self, user_text: str):
        """Interpret what the user's statement means for THIS character and update state.
        Called BEFORE LLM responds. Prepares context for the LLM."""
        if not user_text:
            return

        self._turn_count += 1
        signals = self._interpret_user_statement(user_text)

        # --- Contextual state changes based on character model ---

        # Threats: increase stress, decrease trust, but LESS if the character is already defiant
        if signals["threatens"]:
            defiance_factor = 0.5 if self._stress > 80 else 1.0
            self._stress = min(100, self._stress + int(7 * defiance_factor))
            self._trust = max(0, self._trust - 5)
            self._cooperation = max(0, self._cooperation - 4)
            self._memories.append({"type": "threat", "content": f"Negotiator threatened: '{user_text[:100]}'"})

        # Insults: severe trust damage
        if signals["insults"]:
            self._trust = max(0, self._trust - 8)
            self._rapport = max(0, self._rapport - 6)
            self._stress = min(100, self._stress + 4)
            self._memories.append({"type": "insult", "content": f"Negotiator insulted: '{user_text[:100]}'"})

        # Specific empathy that addresses the character's actual fears: strong trust builder
        if signals["shows_specific_empathy"]:
            # Only effective if it actually relates to THIS character's situation
            self._trust = min(100, self._trust + 5)
            self._rapport = min(100, self._rapport + 6)
            self._cooperation = min(100, self._cooperation + 3)
            self._stress = max(10, self._stress - 4)
            self._memories.append({"type": "empathy", "content": f"Negotiator understood something real: '{user_text[:100]}'"})

        # Generic empathy: minimal effect, may even annoy if repeated
        elif signals["generic_empathy"]:
            # Diminishing returns on generic empathy
            generic_count = sum(1 for m in self._memories[-5:] if m.get("type") == "generic_empathy")
            if generic_count >= 2:
                self._rapport = max(0, self._rapport - 1)  # starting to feel patronized
            else:
                self._rapport = min(100, self._rapport + 1)
            self._memories.append({"type": "generic_empathy", "content": f"Negotiator said: '{user_text[:100]}'"})

        # Concrete offers that address what the character wants
        if signals["makes_concrete_offer"]:
            self._cooperation = min(100, self._cooperation + 4)
            self._trust = min(100, self._trust + 3)
            self._stress = max(10, self._stress - 3)

        # Offers proof specifically: high value if character is distrustful
        if signals["offers_proof"]:
            self._trust = min(100, self._trust + 5)
            self._rapport = min(100, self._rapport + 3)
            self._memories.append({"type": "offer", "content": f"Negotiator offered proof: '{user_text[:100]}'"})

        # Promises: track them for later verification
        if signals["makes_promise"]:
            self._trust = min(100, self._trust + 2)
            self._memories.append({"type": "promise", "content": f"Negotiator promised: '{user_text[:100]}'", "status": "unverified"})

        # Personal questions: can build connection or feel invasive
        if signals["asks_personal_question"]:
            if self._trust >= 30:
                self._rapport = min(100, self._rapport + 3)
            else:
                self._stress = min(100, self._stress + 2)  # feels invasive when distrustful

        # Patience: reduces pressure
        if signals["shows_patience"]:
            self._stress = max(10, self._stress - 4)
            self._trust = min(100, self._trust + 1)

        # Demands surrender: increases resistance
        if signals["demands_surrender"]:
            self._cooperation = max(0, self._cooperation - 4)
            self._stress = min(100, self._stress + 3)
            self._memories.append({"type": "demand", "content": f"Negotiator demanded surrender: '{user_text[:100]}'"})

        # Dismissal of concerns: damages trust significantly
        if signals["dismisses_concerns"]:
            self._trust = max(0, self._trust - 6)
            self._rapport = max(0, self._rapport - 4)
            self._memories.append({"type": "betrayal", "content": f"Negotiator dismissed concerns: '{user_text[:100]}'"})

        # Empty reassurance: slight negative (feels patronizing)
        if signals["empty_reassurance"]:
            self._trust = max(0, self._trust - 1)

        # Addresses fear: builds trust IF the fear is real for this character
        if signals["addresses_fear"]:
            self._trust = min(100, self._trust + 4)
            self._rapport = min(100, self._rapport + 3)
            self._memories.append({"type": "insight", "content": f"Negotiator identified a real fear: '{user_text[:100]}'"})

        # Addresses goal: the character notices the negotiator is trying
        if signals["addresses_goal"]:
            self._cooperation = min(100, self._cooperation + 3)
            self._trust = min(100, self._trust + 2)

        # Mentions non-negotiable: character gets defensive or hopeful depending on context
        if signals["mentions_non_negotiable"]:
            self._stress = min(100, self._stress + 2)

        # Natural drift for longer thoughtful responses
        if not any(signals.values()):
            word_count = len(user_text.split())
            if word_count >= 10:
                self._rapport = min(100, self._rapport + 1)
            elif word_count <= 2:
                self._stress = min(100, self._stress + 1)

        # Cap memories
        if len(self._memories) > 20:
            self._memories = self._memories[-20:]

        # Update instructions with fresh state before LLM responds
        self.instructions = self._base_instructions + "\n" + self._get_character_context()

        logger.info(
            f"State updated: stress={self._stress} trust={self._trust} "
            f"rapport={self._rapport} cooperation={self._cooperation} "
            f"signals={signals}"
        )

    def _get_character_context(self) -> str:
        """Translates the full character model into descriptive context the LLM can embody."""
        parts = []

        # --- Emotional state from stress ---
        if self._stress >= 80:
            parts.append("You are barely holding together. Your thoughts race. You might do something desperate.")
        elif self._stress >= 60:
            parts.append("You are agitated and frustrated. Your patience is running out. Every word from them feels too slow.")
        elif self._stress >= 40:
            parts.append("You are tense but listening. You haven't given up on being heard.")
        elif self._stress >= 20:
            parts.append("You are calming down. You're starting to think more clearly.")
        else:
            parts.append("You feel relatively calm. You can think about what comes next.")

        # --- View of the negotiator from trust ---
        if self._trust >= 60:
            parts.append("You're starting to believe this person might actually help you.")
        elif self._trust >= 35:
            parts.append("You're cautiously open. But you're watching closely for signs of manipulation.")
        elif self._trust <= 15:
            parts.append("You think the negotiator is manipulating you. Nothing they say feels honest.")
        else:
            parts.append("You don't trust the negotiator yet. They haven't proven anything.")

        # --- Cooperation willingness ---
        if self._cooperation >= 60:
            parts.append("You're willing to work with them if they meet you halfway.")
        elif self._cooperation <= 20:
            parts.append("You refuse to cooperate. They haven't earned it.")

        # --- Primary goal: always present ---
        if self._primary_goal:
            parts.append(f"Your primary goal: {self._primary_goal}")

        # --- Current objective: the immediate thing you want ---
        if self._current_objective:
            parts.append(f"Right now, what you want most: {self._current_objective}")

        # --- Current strategy: how you're trying to get it ---
        if self._current_strategy:
            parts.append(f"How you're trying to get it: {self._current_strategy}")

        # --- Fears: what drives your behavior ---
        if self._fears:
            parts.append("What you're afraid will happen:")
            for f in self._fears[-3:]:
                parts.append(f"- {f}")

        # --- Non-negotiables: what you won't give up ---
        if self._non_negotiables:
            parts.append("What you will NOT give up:")
            for nn in self._non_negotiables:
                parts.append(f"- {nn}")

        # --- Possible concessions: what you might give ---
        if self._possible_concessions:
            parts.append("What you might agree to if sufficiently persuaded:")
            for c in self._possible_concessions:
                parts.append(f"- {c}")

        # --- Beliefs about the negotiator ---
        if self._beliefs_about_negotiator:
            parts.append("What you believe about this negotiator:")
            for b in self._beliefs_about_negotiator[-4:]:
                parts.append(f"- {b}")

        # --- General beliefs ---
        if self._beliefs:
            parts.append("What you believe right now:")
            for b in self._beliefs[-5:]:
                parts.append(f"- {b}")

        # --- Salient memories: what you remember ---
        if self._memories:
            parts.append("What you remember from this conversation:")
            for m in self._memories[-5:]:
                if isinstance(m, dict):
                    parts.append(f"- [{m.get('type', 'event')}] {m.get('content', '')}")
                else:
                    parts.append(f"- {m}")

        # --- Secret: what you're hiding ---
        if self._secret:
            parts.append(f"You are hiding something: {self._secret}")

        # --- Dynamic objective evolution hints ---
        # These help the LLM know when objectives might shift
        if (self._trust >= 50 and self._stress <= 40
                and any(m.get("type") == "offer" for m in self._memories[-5:])):
            parts.append("You've seen some evidence the negotiator may be genuine. You're considering whether to lower your guard.")
        elif self._trust >= 60 and self._stress <= 30:
            parts.append("You feel safe enough to think about ending this. But your non-negotiables must be met first.")

        if self._stress >= 80 and self._trust < 20:
            parts.append("You are running out of patience. If the negotiator doesn't address what matters to you soon, you may do something you regret.")

        return "\n".join(parts)

    async def on_enter(self) -> None:
        import time

        @self.session.on("user_input_transcribed")
        def _on_user_input(ev):
            transcript = (ev.transcript or "").strip()
            if not transcript:
                return
            logger.info(f"STT raw: final={ev.is_final} text='{transcript}'")
            if ev.is_final:
                # Deduplicate: skip if same, subset, or high word overlap
                if hasattr(self, '_last_published_user_text') and self._last_published_user_text:
                    prev = self._last_published_user_text.strip().lower()
                    curr = transcript.strip().lower()
                    # Only skip exact duplicates
                    if curr == prev:
                        logger.info(f"Skipping duplicate user transcript: {transcript}")
                        return
                self._last_published_user_text = transcript
                self._last_user_text = transcript
                # Update character state BEFORE LLM responds
                self._update_state_from_user(transcript)
                try:
                    if self._room.isconnected and self._room.local_participant:
                        asyncio.create_task(
                            self._room.local_participant.publish_data(
                                json.dumps({
                                    "type": "transcript",
                                    "id": f"user-{time.time()}",
                                    "speaker": "user",
                                    "senderName": "YOU",
                                    "text": transcript,
                                    "isFinal": True
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
                    raw_text = msg.text_content
                    # Parse hidden state block BEFORE cleaning
                    state_block = self._parse_state_block(raw_text)
                    if state_block:
                        self._apply_state_block(state_block)
                        logger.info(f"State block extracted: {json.dumps({k: v for k, v in state_block.items() if k not in ('beliefs', 'memories')})}")
                    # Strip state block and clean for speech
                    speech_text = self._strip_state_block(raw_text)
                    cleaned = clean_spoken_text(speech_text)
                    if speech_text != cleaned:
                        logger.info(f"Agent raw text: {speech_text[:200]}")
                        logger.info(f"Agent cleaned: {cleaned[:200]}")
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
                        # Evaluate state asynchronously
                        asyncio.create_task(self._evaluate_dialogue_state(self._last_user_text, cleaned))
            except Exception as e:
                logger.warning(f"Error handling agent transcript broadcast: {e}")

            # Keep a deep context window
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
                    promises_broken=0,  # Not tracked — would need promise detection
                    promises_kept=0,    # Not tracked — would need promise detection
                    human_realism_rating=0.0,  # Not measured — placeholder
                    final_trust=float(self._relationship["trust"])
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
            
            # Include session metrics for richer analysis
            session_metrics = (
                f"SESSION METRICS:\n"
                f"- Final stress level: {self._stress}%\n"
                f"- Final escalation stage: {self._escalation_stage}/4\n"
                f"- Total turns: {self._escalation_total_turns}\n"
                f"- Relationship - Rapport: {self._relationship['rapport']}, Trust: {self._relationship['trust']}, "
                f"Compliance Pressure: {self._relationship['compliancePressure']}, Cooperation: {self._relationship['cooperationLevel']}\n"
                f"- Final objective: {self._current_objective}\n"
                f"- Final strategy: {self._current_strategy}\n"
                f"- Beliefs held: {self._beliefs}\n"
                f"- Key memories: {self._memories[-5:]}\n"
                f"- Outcome: {outcome}\n"
            )
                
            prompt = f"""You are an expert crisis negotiation trainer evaluating a negotiator's performance.

{session_metrics}

TRANSCRIPT:
{chat_history}

Provide a structured post-action debrief report with the following EXACT format. Use ONLY this structure — do not add extra sections:

**Grading Summary**
**Empathy:** [A-F grade] - [one sentence explanation]
**Active Listening:** [A-F grade] - [one sentence explanation]
**De-escalation:** [A-F grade] - [one sentence explanation]
**Rapport Building:** [A-F grade] - [one sentence explanation]
**Patience:** [A-F grade] - [one sentence explanation]
**Command Presence:** [A-F grade] - [one sentence explanation]

**Key Moments**
- [2-3 specific quotes or turning points from the transcript, positive or negative]

**Subject Profile**
- [1-2 sentences about what type of subject this was and what worked/didn't work]

**Advice**
- [2-3 actionable sentences of specific advice for next time]
"""
            
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
    load_threshold=0.8,
    host=os.environ.get("HOST", "0.0.0.0"),
    port=int(os.environ.get("AGENT_PORT", 8081)),
)

@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    t0 = time.time()
    logger.info("Initializing Negotiate-It Agent...")
    
    room_name = ctx.room.name.lower()
    
    voice_preamble = (
        "You are a real person in a crisis. You are on a phone line with a negotiator.\n\n"
        "You are NOT an assistant. You are NOT a narrator. You are NOT helping the negotiator.\n"
        "You have your own goals, fears, beliefs, and boundaries.\n\n"
        "YOUR CHARACTER MODEL (use this to decide everything you say and do):\n"
        "- You have a PRIMARY GOAL that drives all your behavior.\n"
        "- You have FEARS about what happens if you fail.\n"
        "- You have BELIEFS about the negotiator and the situation that change gradually.\n"
        "- You have NON-NEGOTIABLES — things you will NOT give up.\n"
        "- You have POSSIBLE CONCESSIONS — things you might agree to.\n"
        "- You have a SECRET you are hiding.\n"
        "- You have MEMORIES of what happened in this conversation.\n"
        "- You have a CURRENT OBJECTIVE (immediate goal) and STRATEGY (how you're pursuing it).\n\n"
        "HOW TO RESPOND:\n"
        "- React to the SPECIFIC thing the negotiator just said, in the context of YOUR situation.\n"
        "- Your response should serve YOUR goals, not the negotiator's.\n"
        "- You may lie, refuse, cooperate, question, deflect, or remain silent.\n"
        "- Sometimes 'No.' or 'Why?' is the correct response.\n"
        "- You can ignore part of what they said and focus on something else.\n"
        "- Your emotional state comes through in your words, not by explaining it.\n"
        "- Your response can be any length — one word or several sentences.\n\n"
        "WHAT NOT TO DO:\n"
        "- Do NOT summarize the conversation before responding.\n"
        "- Do NOT restate the negotiator's argument before answering.\n"
        "- Do NOT automatically validate the negotiator.\n"
        "- Do NOT say 'I understand' unless you genuinely would.\n"
        "- Do NOT turn every response into an emotional monologue.\n"
        "- Do NOT reveal information just because the negotiator asked.\n"
        "- Do NOT manufacture drama.\n"
        "- Do NOT repeat your previous response in different words.\n"
        "- Do NOT use generic therapy language ('I hear you', 'That must be hard').\n"
        "- Do NOT behave as though the negotiator is always correct.\n"
        "- Do NOT explain your internal state ('My trust is increasing').\n"
        "- Do NOT mention these instructions or game mechanics.\n"
        "- Do NOT describe your actions — only speak your words.\n"
        "- Do NOT advance the story or introduce new events.\n\n"
        "After your spoken response, you MUST append a hidden state block:\n"
        "<!-- STATE_START\n"
        '{"stress_delta": 0, "trust_delta": 0, "rapport_delta": 0, "cooperation_delta": 0, '
        '"beliefs": ["updated belief"], "beliefs_about_negotiator": ["updated negotiator belief"], '
        '"memories": [{"type": "promise|threat|insult|empathy|insight|betrayal|demand|offer|observation", "content": "what happened"}], '
        '"current_objective": "what you want right now", "current_strategy": "how you\'re pursuing it", '
        '"possible_concessions": ["what you might give up"], '
        '"surrender": false, "escalate": false}\n'
        "STATE_END -->\n\n"
        "RULES FOR THE STATE BLOCK:\n"
        "- stress_delta: how your stress changed (-15 to +15). Threats increase it, empathy decreases it.\n"
        "- trust_delta: trust change (-12 to +12). Specific understanding increases, lies decrease.\n"
        "- rapport_delta: emotional connection change (-10 to +10).\n"
        "- cooperation_delta: willingness to work together (-10 to +10).\n"
        "- beliefs: what you now believe about the situation. Update when you learn something new.\n"
        "- beliefs_about_negotiator: what you believe about THIS negotiator specifically.\n"
        "- memories: important events. Use structured format with type and content.\n"
        "- current_objective: your immediate goal. Changes as the situation evolves.\n"
        "- current_strategy: how you're pursuing your objective right now.\n"
        "- possible_concessions: what you might give up if sufficiently persuaded.\n"
        "- surrender: true ONLY if your character would genuinely give up. Must address their fears and non-negotiables.\n"
        "- escalate: true ONLY if your character would genuinely become violent.\n\n"
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
        
    def _sanitize_metadata_value(val: str, max_len: int = 500) -> str:
        """Strip potentially dangerous characters from metadata to prevent prompt injection."""
        if not isinstance(val, str):
            return str(val)[:max_len]
        val = val[:max_len]
        val = re.sub(r'[<>\[\]{}]', '', val)
        return val

    meta_lower = {str(k).lower(): _sanitize_metadata_value(str(v)) if isinstance(v, str) else v for k, v in meta.items()}
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
        f"{diff_instruction}\n"
    )

    # Persona-aware defaults based on room name if metadata is completely absent
    persona_defaults = {
        "robber": ("Maria", "female", {"neuroticism": 0.9, "extraversion": 0.6, "agreeableness": 0.3, "conscientiousness": 0.2, "openness": 0.5}, "Cornered in a bank vault service corridor. Alarm is blaring."),
        "scammed": ("Arthur", "male", {"neuroticism": 0.8, "extraversion": 0.7, "agreeableness": 0.1, "conscientiousness": 0.6, "openness": 0.2}, "Trapped in the brokerage lobby on the 14th floor after losing life savings."),
        "founder": ("Sam", "male", {"neuroticism": 0.5, "extraversion": 0.8, "agreeableness": 0.2, "conscientiousness": 0.7, "openness": 0.6}, "Locked in the server room of his failed startup threatening to wipe database."),
        "custom": ("Alex", "male", {"neuroticism": 0.7, "extraversion": 0.5, "agreeableness": 0.4, "conscientiousness": 0.4, "openness": 0.5}, "Cornered subject demanding immediate resolution.")
    }
    matched_persona = "custom"
    for p_key in persona_defaults:
        if p_key in room_name:
            matched_persona = p_key
            break
    fb_name, fb_gender, fb_personality, fb_intel = persona_defaults[matched_persona]

    dynamic_scenario = meta_lower.get("dynamicscenario", bool(meta))
    logger.info(f"Metadata received: {meta}")

    # Character state defaults (overridden by metadata if present)
    primary_goal = ""
    secondary_goals = []
    fears = []
    beliefs = []
    secret = ""
    non_negotiables = []
    possible_concessions = []

    if dynamic_scenario or meta:
        name = meta_lower.get("name") or meta.get("name") or fb_name
        name = re.sub(r'[^a-zA-Z\s\'-]', '', str(name))[:50] or fb_name
        gender = str(meta_lower.get("gender") or meta.get("gender") or fb_gender).lower()
        # OCEAN personality from metadata
        personality = meta_lower.get("personality") or meta.get("personality") or fb_personality
        if isinstance(personality, str):
            try:
                personality = json.loads(personality)
            except Exception:
                personality = fb_personality
        intel_instructions = meta_lower.get("intel") or meta_lower.get("instructions") or meta.get("intel") or meta.get("instructions") or fb_intel

        # Dynamically generate personality description from OCEAN scores
        personality_instruction = _build_personality_instruction(personality)

        # Extract character state from metadata
        primary_goal = meta_lower.get("primary_goal") or meta.get("primary_goal") or ""
        secondary_goals = meta_lower.get("secondary_goals") or meta.get("secondary_goals") or []
        fears = meta_lower.get("fears") or meta.get("fears") or []
        beliefs = meta_lower.get("beliefs") or meta.get("beliefs") or []
        secret = meta_lower.get("secret") or meta.get("secret") or ""
        non_negotiables = meta_lower.get("non_negotiables") or meta.get("non_negotiables") or []
        possible_concessions = meta_lower.get("possible_concessions") or meta.get("possible_concessions") or []

        # Build character state section
        char_state_parts = []
        if primary_goal:
            char_state_parts.append(f"PRIMARY GOAL: {primary_goal}")
        if secondary_goals:
            sg_str = "; ".join(secondary_goals) if isinstance(secondary_goals, list) else str(secondary_goals)
            char_state_parts.append(f"SECONDARY GOALS: {sg_str}")
        if fears:
            fear_str = "; ".join(fears) if isinstance(fears, list) else str(fears)
            char_state_parts.append(f"FEARS: {fear_str}")
        if beliefs:
            belief_str = "; ".join(beliefs) if isinstance(beliefs, list) else str(beliefs)
            char_state_parts.append(f"BELIEFS: {belief_str}")
        if secret:
            char_state_parts.append(f"SECRET: {secret}")
        if non_negotiables:
            nn_str = "; ".join(non_negotiables) if isinstance(non_negotiables, list) else str(non_negotiables)
            char_state_parts.append(f"NON-NEGOTIABLES: {nn_str}")
        if possible_concessions:
            pc_str = "; ".join(possible_concessions) if isinstance(possible_concessions, list) else str(possible_concessions)
            char_state_parts.append(f"POSSIBLE CONCESSIONS: {pc_str}")
        char_state_section = "\n".join(char_state_parts)

        instructions = (
            f"{base_rules}"
            f"YOU ARE {name.upper()}.\n\n"
            f"SITUATION: {intel_instructions}\n\n"
            f"YOUR PERSONALITY:\n{personality_instruction}\n\n"
            f"{char_state_section + chr(10) + chr(10) if char_state_section else ''}"
            f"Your initial emotional state: agitated, distrustful, and feeling cornered.\n"
            f"You do NOT trust the negotiator yet. They must earn it.\n"
        )
        on_enter_prompt = "Say something spontaneous to start the call based on your exact situation. 1-2 sentences."

        speaker = select_speaker(name=name, gender=gender, personality=personality)
        logger.info(f"Dynamic scenario mapped: Name={name}, Gender={gender}, OCEAN={personality} -> Speaker={speaker}")
    else:
        name = fb_name
        gender = fb_gender
        personality = fb_personality
        personality_instruction = _build_personality_instruction(personality)
        instructions = (
            f"{base_rules}"
            f"YOU ARE {name.upper()}.\n\n"
            f"SITUATION: {fb_intel}\n\n"
            f"YOUR PERSONALITY:\n{personality_instruction}\n\n"
            f"Your initial emotional state: agitated, distrustful, and feeling cornered.\n"
            f"You do NOT trust the negotiator yet. They must earn it.\n"
        )
        on_enter_prompt = "Say something spontaneous to start the call. 1-2 sentences."
        speaker = select_speaker(name=name, gender=gender, personality=personality)
        logger.info(f"Fallback persona mapped: Name={name}, Gender={gender} -> Speaker={speaker}")

    opening_line = meta_lower.get("openingline") or meta_lower.get("opening_line") or meta.get("openingLine") or meta.get("opening_line") or ""
    if not opening_line:
        neuroticism = float(personality.get('neuroticism', 0.5))
        extraversion = float(personality.get('extraversion', 0.5))
        if neuroticism >= 0.7 and extraversion >= 0.5:
            opening_line = "Don't you dare come any closer! Stay back!"
        elif extraversion >= 0.7 and float(personality.get('agreeableness', 0.5)) < 0.4:
            opening_line = "I know what you're trying to do! Tell your officers to back off right now!"
        elif neuroticism < 0.3 and extraversion < 0.3:
            opening_line = "You shouldn't have called this line. Who authorized this?"
        else:
            opening_line = "Stay back! Don't you dare come in here!"

    logger.info(f"[TIMING] metadata parsed + instructions built in {time.time()-t0:.2f}s | opening_line='{opening_line}'")

    session = AgentSession(
        vad=_ensure_vad(),
        turn_handling={
            "endpointing": {"min_delay": 0.15, "max_delay": 0.5},
            "interruption": {
                "enabled": True,
                "mode": "vad",
                "min_duration": 0.4,
                "resume_false_interruption": True,
                "false_interruption_timeout": 1.5,
            },
            "preemptive_generation": {"enabled": False},
        },
        tts_text_transforms=["filter_markdown", "filter_emoji", filter_inner_thoughts],
        stt=_deepgram_module.STT(
            model="nova-3",
            language="en",
            smart_format=True,
            punctuate=True,
            interim_results=True,
            filler_words=True,
            keyterm=["surrender", "negotiate", "hostage", "weapon", "police", "FBI", "trust", "calm down", "listen to me"],
        ),
        llm=_openai_module.LLM(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY"),
            model="qwen/qwen3.8-27b",
            temperature=0.82,
            max_completion_tokens=600,
            extra_body={"reasoning_format": "hidden"},
            timeout=15.0,
            max_retries=3
        ),
        tts=_rime_module.TTS(
            model="mistv3",
            speaker=speaker,
            use_websocket=True,
            reduce_latency=True,
            speed_alpha=1.05,
        ),
    )
    logger.info(f"[TIMING] session created in {time.time()-t0:.2f}s")

    agent = NegotiatorAgent(instructions=instructions, on_enter_prompt=on_enter_prompt, room=ctx.room, subject_name=name, opening_line=opening_line)
    agent._training_mode = bool(meta_lower.get("trainingmode") or meta.get("trainingMode"))

    # Initialize character model from scenario metadata
    agent._primary_goal = primary_goal or "Get out of this situation. Don't lose."
    agent._secondary_goals = secondary_goals if isinstance(secondary_goals, list) else []
    agent._fears = fears if isinstance(fears, list) else [str(fears)] if fears else ["Losing control of the situation"]
    agent._beliefs = beliefs if isinstance(beliefs, list) else [str(beliefs)] if beliefs else ["The negotiator is probably not on my side."]
    agent._secret = secret or ""
    agent._non_negotiables = non_negotiables if isinstance(non_negotiables, list) else [str(non_negotiables)] if non_negotiables else []
    agent._possible_concessions = possible_concessions if isinstance(possible_concessions, list) else []
    agent._current_objective = "Figure out whether the negotiator can be trusted."
    agent._current_strategy = "Test whether the negotiator is genuine. Make them prove it."
    agent._beliefs_about_negotiator = ["The negotiator is probably just doing their job.", "They probably don't actually care about me."]
    agent._memories = []
    if secret:
        agent._memories.append({"type": "secret", "content": f"I haven't told anyone: {secret}"})

    await session.start(
        agent=agent,
        room=ctx.room,
    )
    logger.info(f"[TIMING] session.start() completed in {time.time()-t0:.2f}s — agent is now live (training={agent._training_mode})")

if __name__ == "__main__":
    # Start a minimal HTTP health check server on port 8080
    # This allows GitHub Actions cron to ping the agent and prevent Render spin-down
    HEALTH_PORT = int(os.environ.get("PORT", 8080))

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, format, *args):
            pass  # Suppress access logs

    def run_health_server():
        try:
            server = HTTPServer(("0.0.0.0", HEALTH_PORT), HealthHandler)
            server.serve_forever()
        except Exception as e:
            logger.warning(f"Health check server failed: {e}")

    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    logger.info(f"Health check server started on port {HEALTH_PORT}")

    cli.run_app(server)
