import json
import os
import time
import random
from typing import Optional
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

from cognition.schemas import (
    WorldState,
    HumanModel, PsychologicalState, RelationshipState,
    SituationModel, Belief, BehavioralDecision, Expression
)

class SpeechGenerationResult(BaseModel):
    spoken_text: str = Field(description="The exact words spoken by the subject.")
    confidence: float = Field(default=1.0)
    behavioral_fidelity: float = Field(default=1.0)

FALLBACKS = {
    "seek_reassurance": "Are you sure?",
    "stall": "I need a minute.",
    "probe": "What do you mean?",
    "partial_disclosure": "There's something else.",
    "full_disclosure": "I'll tell you everything.",
    "cooperate": "Fine. I agree.",
    "refuse": "No. I won't.",
    "threaten": "Don't make me do something we both regret.",
    "withdraw": "...",
    "demand": "I need it right now.",
    "lie": "I don't know anything about that.",
    "use_walkie_talkie": "I'm on the radio now. Can you hear me?"
}

class SpeechGenerator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            # We allow empty for tests, but warn
            pass
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=self.api_key or "test-key"
        )
        self.model = "openai/gpt-oss-20b"
        
    def _validate_speech(self, text: str) -> str:
        """Removes stage directions and narrative formatting."""
        # Simple cleanup for common LLM failure modes
        import re
        text = re.sub(r'\*[^\*]+\*', '', text) # Remove *sigh*
        text = re.sub(r'\[[^\]]+\]', '', text) # Remove [angry]
        text = re.sub(r'\([^\)]+\)', '', text) # Remove (hesitates)
        return text.strip()

    def generate(
        self,
        human: HumanModel,
        state: PsychologicalState,
        rel: RelationshipState,
        decision: BehavioralDecision,
        expression: Expression,
        beliefs: list[Belief],
        situation: SituationModel,
        world: Optional[WorldState] = None,
        recent_context: list[str] = None
    ) -> SpeechGenerationResult:
        
        recent_context = recent_context or []
        context_str = "\n".join(recent_context)
        
        # Filter beliefs to only highly relevant ones (tension > 50 or confidence > 80)
        rel_beliefs = [b for b in beliefs if b.tension > 50.0 or b.confidence > 80.0]
        beliefs_str = "\n".join([f"- {b.statement}" for b in rel_beliefs])

        # Filter authoritative world facts relevant to subject
        world_facts = []
        if world:
            for r_id, res in world.resources.items():
                if res.holder == "subject":
                    world_facts.append(f"Subject physically possesses: {res.name} ({r_id})")
                elif res.holder == "negotiator":
                    world_facts.append(f"Negotiator possesses: {res.name} ({r_id})")
            for c_id, cap in world.capabilities.items():
                if cap.enabled and "subject" in c_id:
                    world_facts.append(f"Subject capability enabled: {cap.name} ({c_id})")
        world_str = "\n".join([f"- {f}" for f in world_facts])

        prompt = f"""
SYSTEM:
You are a pure rendering engine translating cognitive state into spoken text for a human subject in a crisis simulator.
DO NOT decide what the subject wants, believes, or does. The Behavioral Decision is authoritative.
DO NOT write stage directions (no *sigh*, no [angry]).
DO NOT narrate. Provide ONLY the exact words spoken.
DO NOT use overly polished prose. Use natural spoken structure (short clauses, contractions, implicit meaning).
DO NOT use AI explanation tropes ("I feel anxious because...").

AUTHORITATIVE WORLD FACTS (DO NOT CONTRADICT PHYSICAL REALITY):
{world_str if world_str else "None"}

STATE:
Personality: {human.personality_narrative}
Communication Style: {human.communication_style.description} (Verbosity: {human.communication_style.verbosity}, Directness: {human.communication_style.directness})
Fear: {state.fear:.1f}, Anger: {state.anger:.1f}, Stress: {state.stress:.1f}
Trust in Negotiator: {rel.trust:.1f}
Relevant Beliefs: {beliefs_str if beliefs_str else "None"}

BEHAVIOR:
Authoritative Action: {decision.selected.action}
Intensity: {decision.selected.intensity}
Information Strategy: {decision.selected.information_strategy}
Rationale: {decision.selected.rationale}

EXPRESSION (Delivery Metadata):
Pacing: {expression.derived_pacing}
Verbal Style: {expression.derived_verbal_style}
Hesitation Tendency: {expression.hesitation_tendency:.2f} (If high, use natural disfluency sparingly)
Directness: {expression.directness:.2f}
Word Range: {expression.min_words} to {expression.max_words} words.

CONTEXT (Recent turns):
{context_str if context_str else "None"}

TASK:
Output the generated speech in strictly valid JSON format.
Example valid output:
{{
    "spoken_text": "I want the money now.",
    "confidence": 1.0,
    "behavioral_fidelity": 1.0
}}
Ensure the response is ONLY a JSON object.
"""
        
        # Attempt generation
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7, # allow slight variation
                max_tokens=256,
                timeout=5.0 # Strict latency requirement
            )
            raw = response.choices[0].message.content
            # Strip markdown if present
            if raw.startswith("```json"):
                raw = raw.replace("```json", "", 1)
                if raw.endswith("```"):
                    raw = raw[:-3]
            raw = raw.strip()
            res = SpeechGenerationResult.model_validate_json(raw)
            
            # Post-process to strip stage directions if LLM misbehaved
            clean_text = self._validate_speech(res.spoken_text)
            
            if not clean_text:
                raise ValueError("Empty output after cleanup")
                
            res.spoken_text = clean_text
            return res
            
        except Exception as e:
            print(f"Speech Gen Error: {e}. Falling back.")
            action = decision.selected.action
            fallback_text = FALLBACKS.get(action, "I don't know.")
            return SpeechGenerationResult(spoken_text=fallback_text, confidence=0.0, behavioral_fidelity=1.0)
