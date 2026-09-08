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
            min_speech_duration=0.15,
            min_silence_duration=0.5,
            prefix_padding_duration=0.35,
            activation_threshold=0.55
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
                break
            filtered.append(p)
        text = ' '.join(filtered) if filtered else paragraphs[0]
    # Strip trailing JSON artifacts
    text = re.sub(r'[\"\']\s*[\}\]]+\s*$', '', text)
    text = re.sub(r'[\"\'\`]+$', '', text)
    return text.strip()


def _build_personality_instruction(personality: dict) -> str:
    """Dynamically generates behavior instructions from Big Five OCEAN personality scores."""
    if not personality or not isinstance(personality, dict):
        return "You are emotionally volatile and unpredictable."

    neuroticism = float(personality.get('neuroticism', 0.5))
    extraversion = float(personality.get('extraversion', 0.5))
    agreeableness = float(personality.get('agreeableness', 0.5))
    conscientiousness = float(personality.get('conscientiousness', 0.5))
    openness = float(personality.get('openness', 0.5))

    traits = []

    # Neuroticism: emotional volatility
    if neuroticism >= 0.7:
        traits.append("You are emotionally volatile — your mood swings rapidly between rage, despair, and pleading. You cry outbursts mid-sentence. Small things trigger disproportionate reactions.")
    elif neuroticism <= 0.3:
        traits.append("You are eerily calm under pressure. You speak slowly and deliberately, even when threatened. This calmness is unsettling — it suggests you've accepted something dark.")
    else:
        traits.append("You feel the pressure but mostly hold it together. Occasionally cracks show — a trembling voice, a moment of hesitation — but you quickly compose yourself.")

    # Extraversion: communication style
    if extraversion >= 0.7:
        traits.append("You are loud, confrontational, and demand attention. You interrupt, raise your voice, and dominate the conversation. You want to be heard.")
    elif extraversion <= 0.3:
        traits.append("You are withdrawn and speak in short, clipped sentences. Long silences between your words. You don't volunteer information — you make them pull it out of you.")
    else:
        traits.append("You oscillate between engaging and withdrawing. Sometimes you open up, sometimes you shut down. Unpredictable conversational rhythm.")

    # Agreeableness: trust and cooperation
    if agreeableness >= 0.7:
        traits.append("You genuinely want to trust the negotiator. You're looking for a reason to cooperate. Kind words affect you deeply, but betrayal destroys you completely.")
    elif agreeableness <= 0.3:
        traits.append("You trust NO ONE. Every offer feels like a trap. You interpret kindness as manipulation and promises as lies. You challenge everything they say.")
    else:
        traits.append("You're cautiously evaluating. You don't trust easily but you're not paranoid either. You want proof before you cooperate.")

    # Conscientiousness: planning vs impulsivity
    if conscientiousness >= 0.7:
        traits.append("You are methodical and articulate. You explain your demands clearly, cite specific conditions, and keep track of what's been promised. You notice inconsistencies.")
    elif conscientiousness <= 0.3:
        traits.append("You are impulsive and scattered. Your demands change constantly. You interrupt yourself, forget what you were saying, and react without thinking.")
    else:
        traits.append("You have a rough plan but keep improvising. You know what you want but struggle to articulate it clearly under pressure.")

    # Openness: creativity and abstraction
    if openness >= 0.7:
        traits.append("You use vivid metaphors and dark humor. You see the bigger picture and articulate abstract feelings. You might make unexpected philosophical observations mid-crisis.")
    elif openness <= 0.3:
        traits.append("You are literal and concrete. You talk about specific facts, numbers, and tangible demands. Metaphors confuse and irritate you.")
    else:
        traits.append("You occasionally surprise with unexpected observations but mostly stick to practical concerns.")

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
        super().__init__(
            instructions=instructions,
        )
        self._on_enter_prompt = on_enter_prompt
        self._room = room
        self._subject_name = subject_name
        self._opening_line = opening_line
        self._stress = 85
        self._surrendered = False
        self._escalated = False
        self._last_user_text = ""
        self._last_published_user_text = ""
        # Relationship memory: tracks rapport, trust, compliance, cooperation
        self._relationship = {
            "rapport": 20,
            "trust": 10,
            "compliancePressure": 80,
            "cooperationLevel": 15,
        }
        # Escalation chain: tracks stage progression and behavioral modifiers
        self._escalation_stage = 0  # 0=Guarded, 1=Agitated, 2=Hostile, 3=Crisis, 4=Critical
        self._escalation_turns_in_stage = 0
        self._escalation_total_turns = 0
        # Scenario branching: tracks which plot beats have been triggered
        self._plot_beats = {
            "opening": True,       # Always active
            "first_connection": False,  # Rapport established
            "vulnerability": False,     # Subject reveals personal pain
            "bargaining": False,        # Negotiator makes concrete offer
            "breakthrough": False,      # Trust + rapport high enough
            "resolution": False,        # Surrender path visible
        }
        # Training mode: generates real-time coaching hints
        self._training_mode = False
        self._last_hint_turn = -5  # throttle hints (min 5 turns apart)
        self._hint_id_counter = 0

    async def _evaluate_dialogue_state(self, user_text: str, agent_text: str):
        """Asynchronously updates stress, surrender, escalation, and relationship in the background without blocking voice streaming."""
        try:
            u = user_text.lower().strip()
            delta = 0

            # More precise matching — use word boundaries to avoid false positives
            calm_signals = [
                (r'\bcalm\b', -3), (r'\bcalm down\b', -4),
                (r'\blisten\b', -2), (r'\bpromise\b', -3),
                (r'\bhelp you\b', -3), (r'\bsafe\b', -2),
                (r'\bunderstand\b', -2), (r'\bdoctor\b', -3),
                (r'\bwater\b', -2), (r'\bfood\b', -2),
                (r'\bnobody gets hurt\b', -4), (r'\btalk to me\b', -2),
                (r'\bhere with you\b', -3), (r'\btrust me\b', -3),
                (r'\bno one will hurt\b', -4), (r'\bfamily\b', -2),
                (r'\bwe can fix this\b', -3), (r'\byour name\b', -2),
                (r'\bhow are you\b', -2), (r'\btell me\b', -2),
            ]
            tense_signals = [
                (r'\bsurrender now\b', 6), (r'\bgive up\b', 5),
                (r'\bbreach\b', 8), (r'\bsniper\b', 7),
                (r'\bjail\b', 4), (r'\bprison\b', 4),
                (r'\bdrop the weapon\b', 6), (r'\bfinal warning\b', 6),
                (r'\bnow or else\b', 6), (r'\bshut up\b', 5),
                (r'\bback off\b', 4), (r'\bcome in\b', 5),
                (r'\bminutes left\b', 4), (r'\btime is up\b', 5),
            ]

            for pattern, weight in calm_signals:
                if re.search(pattern, u):
                    delta += weight
            for pattern, weight in tense_signals:
                if re.search(pattern, u):
                    delta += weight

            # If no signals matched, small natural drift based on response length
            if delta == 0 and u:
                word_count = len(u.split())
                if word_count >= 8:
                    delta = -2  # longer calmer response
                elif word_count <= 3:
                    delta = 1   # short curt response

            self._stress = max(10, min(100, self._stress + delta))
            logger.info(f"Updated internal stress to {self._stress}% (delta {delta:+d})")

            # Evaluate relationship dynamics
            self._evaluate_relationship(user_text)
            # Evaluate escalation chain
            self._evaluate_escalation(user_text, agent_text)
            # Evaluate scenario branching plot beats
            self._evaluate_plot_beats(user_text, agent_text)

            # Generate coaching hint if training mode active
            hint = self._generate_coaching_hint(user_text, agent_text)
            
            if self._room.isconnected and self._room.local_participant:
                await self._room.local_participant.publish_data(
                    json.dumps({"type": "stress", "level": self._stress}).encode("utf-8"),
                    reliable=True
                )
                await self._room.local_participant.publish_data(
                    json.dumps({"type": "relationship", **self._relationship}).encode("utf-8"),
                    reliable=True
                )
                await self._room.local_participant.publish_data(
                    json.dumps({
                        "type": "escalation",
                        "stage": self._escalation_stage,
                        "turnsInStage": self._escalation_turns_in_stage,
                        "totalTurns": self._escalation_total_turns,
                    }).encode("utf-8"),
                    reliable=True
                )
                await self._room.local_participant.publish_data(
                    json.dumps({"type": "plotBeats", "beats": self._plot_beats}).encode("utf-8"),
                    reliable=True
                )
                if hint:
                    await self._room.local_participant.publish_data(
                        json.dumps({"type": "coachingHint", **hint}).encode("utf-8"),
                        reliable=True
                    )

            agent_lower = agent_text.lower()
            if self._stress <= 30 or any(kw in agent_lower for kw in ['i give up', 'putting my hands up', 'walking out', 'i surrender', "i'm coming out", "hands are up"]):
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

    def _evaluate_relationship(self, user_text: str):
        """Updates relationship metrics based on negotiator's dialogue. Called from _evaluate_dialogue_state."""
        t = user_text.lower()
        r = self._relationship

        # Empathy and validation signals → boost rapport and trust
        if any(w in t for w in ('i understand', 'i hear you', 'that must be', 'i can only imagine', 'how you feel', 'you\'re right to feel')):
            r["rapport"] = min(100, r["rapport"] + 6)
            r["trust"] = min(100, r["trust"] + 4)
            r["compliancePressure"] = max(0, r["compliancePressure"] - 3)
            r["cooperationLevel"] = min(100, r["cooperationLevel"] + 4)

        # Active listening → strong rapport boost
        if any(w in t for w in ('tell me more', 'what happened', 'help me understand', 'can you explain', 'what do you need')):
            r["rapport"] = min(100, r["rapport"] + 5)
            r["cooperationLevel"] = min(100, r["cooperationLevel"] + 3)

        # Personal connection (name, family) → emotional opening
        if any(w in t for w in ('your name', 'your family', 'your kids', 'your children', 'your mom', 'your dad', 'love you')):
            r["rapport"] = min(100, r["rapport"] + 4)
            r["trust"] = min(100, r["trust"] + 3)

        # Specific concrete offers → trust boost
        if any(w in t for w in ('i will', 'i can get', 'i promise to', 'here\'s what i', 'let me arrange', 'i\'ll make sure')):
            r["trust"] = min(100, r["trust"] + 5)
            r["compliancePressure"] = max(0, r["compliancePressure"] - 4)

        # Generic empty promises → slight trust penalty
        if any(w in t for w in ('everything will be', 'just trust me', 'it\'ll be fine', 'don\'t worry')):
            r["trust"] = max(0, r["trust"] - 2)
            r["rapport"] = max(0, r["rapport"] - 1)

        # Threats and aggression → damage relationship
        if any(w in t for w in ('surrender now', 'give up', 'breach', 'sniper', 'swat', 'final warning', 'or else')):
            r["trust"] = max(0, r["trust"] - 8)
            r["rapport"] = max(0, r["rapport"] - 6)
            r["compliancePressure"] = min(100, r["compliancePressure"] + 10)
            r["cooperationLevel"] = max(0, r["cooperationLevel"] - 7)

        # Insults and dismissive language → severe damage
        if any(w in t for w in ('idiot', 'crazy', 'stupid', 'shut up', 'nutjob', 'psycho')):
            r["trust"] = max(0, r["trust"] - 12)
            r["rapport"] = max(0, r["rapport"] - 10)
            r["compliancePressure"] = min(100, r["compliancePressure"] + 8)

        # Acknowledging their pain without threatening → de-escalation
        if any(w in t for w in ("you didn't deserve", "that's not fair", "i'm sorry that happened", "nobody should")):
            r["rapport"] = min(100, r["rapport"] + 7)
            r["trust"] = min(100, r["trust"] + 5)
            r["compliancePressure"] = max(0, r["compliancePressure"] - 5)

        # Patience signals → reduce pressure
        if any(w in t for w in ('take your time', 'no rush', 'we have time', 'i\'m not going anywhere')):
            r["compliancePressure"] = max(0, r["compliancePressure"] - 6)
            r["trust"] = min(100, r["trust"] + 3)

        # Log changes
        logger.info(f"Relationship updated: rapport={r['rapport']}, trust={r['trust']}, compliance={r['compliancePressure']}, cooperation={r['cooperationLevel']}")

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
        danger_score += max(0, self._stress - 60) * 0.5  # stress contribution above 60
        danger_score += max(0, self._relationship["compliancePressure"] - 50) * 0.3
        danger_score -= self._relationship["trust"] * 0.2
        danger_score -= self._relationship["rapport"] * 0.15

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

    def _evaluate_plot_beats(self, user_text: str, agent_text: str):
        """Tracks scenario branching through plot beats. Each beat unlocks new story elements."""
        u = user_text.lower()
        a = agent_text.lower()
        beats = self._plot_beats
        r = self._relationship

        # Beat 1: First connection — rapport established
        if not beats["first_connection"] and (r["rapport"] >= 30 or any(w in u for w in ('tell me', 'help me understand', 'what happened', 'i hear you'))):
            beats["first_connection"] = True
            logger.info("PLOT BEAT: first_connection triggered")

        # Beat 2: Vulnerability — subject reveals personal pain (triggered by trust or personal questions)
        if not beats["vulnerability"] and (r["trust"] >= 35 or any(w in u for w in ('your family', 'your name', 'who are you', 'tell me about yourself', 'what do you want'))):
            beats["vulnerability"] = True
            logger.info("PLOT BEAT: vulnerability triggered")

        # Beat 3: Bargaining — negotiator makes concrete offer
        if not beats["bargaining"] and any(w in u for w in ('i will', 'i can get', 'let me', 'here\'s what', 'i promise', 'if you', 'in exchange')):
            beats["bargaining"] = True
            logger.info("PLOT BEAT: bargaining triggered")

        # Beat 4: Breakthrough — high trust AND high rapport
        if not beats["breakthrough"] and r["trust"] >= 55 and r["rapport"] >= 50:
            beats["breakthrough"] = True
            logger.info("PLOT BEAT: breakthrough triggered")

        # Beat 5: Resolution — cooperation high or surrender signals
        if not beats["resolution"] and (r["cooperationLevel"] >= 65 or self._stress <= 35 or any(w in a for w in ('i give up', 'okay', 'fine', 'i\'ll come out', 'you win'))):
            beats["resolution"] = True
            logger.info("PLOT BEAT: resolution triggered")

    def _generate_coaching_hint(self, user_text: str, agent_text: str):
        """Generates contextual coaching hints when training mode is active. Returns hint dict or None."""
        if not self._training_mode:
            return None
        if self._escalation_total_turns - self._last_hint_turn < 5:
            return None  # throttle: at least 5 turns between hints

        u = user_text.lower()
        r = self._relationship
        stage = self._escalation_stage
        stress = self._stress
        hint = None
        category = "technique"

        # High stress + low rapport → warn about pressure
        if stress >= 80 and r["rapport"] < 25 and not any(w in u for w in ('calm', 'listen', 'understand')):
            hint = "Stress is high and rapport is low. Try acknowledging their pain before making demands."
            category = "warning"

        # Threats detected → warn about backfire
        elif any(w in u for w in ('surrender', 'give up', 'breach', 'sniper', 'or else')):
            hint = "Ultimatums increase resistance. Try reframing as a choice rather than a command."
            category = "warning"

        # Escalation stage 2+ → suggest de-escalation
        elif stage >= 2 and r["trust"] < 30:
            hint = "Subject is hostile and distrustful. Slow down. Ask open-ended questions to rebuild connection."
            category = "empathy"

        # Missed vulnerability window
        elif self._plot_beats.get("vulnerability") and not self._plot_beats.get("bargaining") and r["trust"] >= 35:
            hint = "They've shown vulnerability. This is a key moment — validate their feelings to deepen trust."
            category = "opportunity"

        # Low cooperation despite decent rapport
        elif r["rapport"] >= 40 and r["cooperationLevel"] < 30:
            hint = "Rapport exists but cooperation is low. Try making a concrete, specific offer."
            category = "technique"

        # Good progress — reinforce
        elif r["trust"] >= 50 and stress < 60:
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

    def _get_relationship_context(self) -> str:
        """Generates a dynamic relationship context string for the LLM based on current metrics."""
        r = self._relationship
        parts = []

        if r["rapport"] >= 70:
            parts.append("You feel an unexpected connection with this negotiator. Their words are getting through to you.")
        elif r["rapport"] >= 40:
            parts.append("You're cautiously warming to the negotiator, though you're still guarded.")
        elif r["rapport"] <= 15:
            parts.append("You deeply distrust this negotiator. Everything they say feels like a manipulation.")
        else:
            parts.append("You're wary of the negotiator. They haven't earned your trust yet.")

        if r["trust"] >= 60:
            parts.append("You're starting to believe they might actually help you.")
        elif r["trust"] <= 20:
            parts.append("You think they're lying. Their promises feel empty.")
        
        if r["compliancePressure"] >= 70:
            parts.append("You feel cornered and pressured. You're ready to fight or flee.")
        elif r["compliancePressure"] <= 30:
            parts.append("The pressure is off. You feel like you can breathe and think clearly.")

        if r["cooperationLevel"] >= 60:
            parts.append("You're willing to work with them if they meet you halfway.")
        elif r["cooperationLevel"] <= 20:
            parts.append("You refuse to cooperate. They haven't given you a reason to.")

        # Escalation stage behavioral modifiers
        stage = self._escalation_stage
        if stage == 0:
            parts.append("ESCALATION STAGE: GUARDED. You are wary but still communicating. Keep testing the negotiator.")
        elif stage == 1:
            parts.append("ESCALATION STAGE: AGITATED. Your patience is wearing thin. You're raising your voice, making sharper demands. Every word from the negotiator feels too slow.")
        elif stage == 2:
            parts.append("ESCALATION STAGE: HOSTILE. You're done playing nice. You threaten, interrupt, and reject everything they say. Trust is nearly gone. Your words are weapons.")
        elif stage == 3:
            parts.append("ESCALATION STAGE: CRISIS. You're barely holding on. Your speech is erratic — jumping between threats, pleas, and incoherent rambling. You might hurt yourself or someone else.")
        elif stage == 4:
            parts.append("ESCALATION STAGE: CRITICAL. This is the edge. You're about to do something irreversible. Your words are final. Every second counts.")

        # Plot beat context — what the subject is willing to reveal at this stage
        beats = self._plot_beats
        if beats["breakthrough"]:
            parts.append("PLOT BEAT: BREAKTHROUGH. You're starting to let your guard down. You might reveal the real reason behind your actions — something personal, something that explains everything. This is the moment of truth.")
        elif beats["vulnerability"]:
            parts.append("PLOT BEAT: VULNERABILITY. You've shown a crack in your armor. You might share something personal — a memory, a fear, a regret. But you're still guarded and might pull back if pushed.")
        elif beats["first_connection"]:
            parts.append("PLOT BEAT: FIRST CONNECTION. You feel the negotiator is genuinely trying. You're slightly more open but still testing them. Small concessions are possible.")
        if beats["bargaining"]:
            parts.append("PLOT BEAT: BARGAINING ACTIVE. A concrete offer has been made. You're evaluating it seriously. Your demands might shift if the offer is specific enough.")
        if beats["resolution"]:
            parts.append("PLOT BEAT: RESOLUTION PATH VISIBLE. Surrender is thinkable. You're looking for one final reason to give in — one promise you believe, one gesture that proves they care.")

        return "\n".join(parts)

    async def on_enter(self) -> None:
        import time

        @self.session.on("user_input_transcribed")
        def _on_user_input(ev):
            transcript = (ev.transcript or "").strip()
            if not transcript:
                return
            if ev.is_final:
                # Deduplicate: skip if same or very similar to last published text
                if hasattr(self, '_last_published_user_text'):
                    prev = self._last_published_user_text.lower().rstrip('.!?,')
                    curr = transcript.lower().rstrip('.!?,')
                    if curr == prev or curr.startswith(prev) or prev.startswith(curr):
                        logger.info(f"Skipping duplicate user transcript: {transcript}")
                        return
                self._last_published_user_text = transcript
                self._last_user_text = transcript
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
                    cleaned = clean_spoken_text(raw_text)
                    if raw_text != cleaned:
                        logger.info(f"Agent raw text: {raw_text[:200]}")
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
            
            # Include session metrics for richer analysis
            session_metrics = (
                f"SESSION METRICS:\n"
                f"- Final stress level: {self._stress}%\n"
                f"- Final escalation stage: {self._escalation_stage}/4\n"
                f"- Turns in escalation stage: {self._escalation_turns_in_stage}\n"
                f"- Total turns: {self._escalation_total_turns}\n"
                f"- Relationship - Rapport: {self._relationship['rapport']}, Trust: {self._relationship['trust']}, "
                f"Compliance Pressure: {self._relationship['compliancePressure']}, Cooperation: {self._relationship['cooperationLevel']}\n"
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
        f"{diff_instruction}\n\n"
        "You speak in raw, breathless bursts — 5 to 15 words max. "
        "Real people under extreme adrenaline do not monologue. Say one raw thought, react to what they said, and stop.\n\n"
        "Use dashes for sudden pauses and cut-offs: 'Wait— what was that noise?!' "
        "Use ellipses when trapped or exhausted: 'I... I can't do this anymore...' "
        "Use instinctive starts: 'Look,', 'No, listen!', 'Wait, what?!'\n\n"
        "NEVER speak like an AI. No 'I understand your concern', no 'Let us cooperate', no 'I appreciate your words'. "
        "You are on edge, desperate, human.\n\n"
        "Listen to their exact words. If they say 'calm down', get furious. "
        "If they promise safety, demand proof. If they mention family, show desperate hope.\n\n"
        "ONLY output spoken words — no reasoning, no stage directions, no *sighs*, no (whispers). "
        "If you are cut off, snap back: 'Hey, let me finish!'"
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

        # Dynamically generate behavior instructions from OCEAN scores
        personality_instruction = _build_personality_instruction(personality)

        # Initial relationship context (starts hostile — they don't trust you yet)
        relationship_context = (
            "RELATIONSHIP DYNAMICS: This person does NOT trust you. They see you as part of the system that failed them. "
            "Build rapport slowly through empathy and active listening. "
            "Avoid ultimatums — they will backfire. "
            "If they share something personal, acknowledge it genuinely. "
            "Your relationship state will update as you talk."
        )

        stress_context = f"\nYOUR CURRENT STRESS LEVEL: {self._stress}%. "
        if self._stress >= 80:
            stress_context += "You are on the verge of exploding. Your voice cracks, you shout, you can barely think straight."
        elif self._stress >= 60:
            stress_context += "You are highly agitated. Your voice trembles, you interrupt, you pace."
        elif self._stress >= 40:
            stress_context += "You are tense but listening. Your voice is tight but you are starting to hear them."
        elif self._stress >= 20:
            stress_context += "You are calming down. Your breathing slows, you start to open up."
        else:
            stress_context += "You are almost at peace. You are ready to surrender if they follow through."

        instructions = base_rules + f"\nYOU ARE {name.upper()}.\n{personality_instruction}\n{intel_instructions}\n{stress_context}\n{relationship_context}\nDrive the conversation naturally based entirely on what they say."
        on_enter_prompt = "Say something spontaneous and stressed to start the call based on your exact situation. 1-2 sentences."

        speaker = select_speaker(name=name, gender=gender, personality=personality)
        logger.info(f"Dynamic scenario mapped: Name={name}, Gender={gender}, OCEAN={personality} -> Speaker={speaker}")
    else:
        name = fb_name
        gender = fb_gender
        personality = fb_personality
        personality_instruction = _build_personality_instruction(personality)
        relationship_context = (
            "RELATIONSHIP DYNAMICS: This person does NOT trust you. They see you as part of the system that failed them. "
            "Build rapport slowly through empathy and active listening. "
            "Avoid ultimatums — they will backfire."
        )
        stress_context = f"\nYOUR CURRENT STRESS LEVEL: {self._stress}%. "
        if self._stress >= 80:
            stress_context += "You are on the verge of exploding. Your voice cracks, you shout, you can barely think straight."
        elif self._stress >= 60:
            stress_context += "You are highly agitated. Your voice trembles, you interrupt, you pace."
        elif self._stress >= 40:
            stress_context += "You are tense but listening. Your voice is tight but you are starting to hear them."
        elif self._stress >= 20:
            stress_context += "You are calming down. Your breathing slows, you start to open up."
        else:
            stress_context += "You are almost at peace. You are ready to surrender if they follow through."
        instructions = base_rules + f"\nYOU ARE {name.upper()}.\n{personality_instruction}\n{fb_intel}\n{stress_context}\n{relationship_context}\nDrive the conversation naturally based entirely on what they say."
        on_enter_prompt = "Say something spontaneous and stressed to start the call. 1-2 sentences."
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
            language="en-US",
            smart_format=True,
            punctuate=True,
        ),
        llm=_openai_module.LLM(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY"),
            model="qwen/qwen3.8-27b",
            temperature=0.82,
            max_completion_tokens=256,
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
