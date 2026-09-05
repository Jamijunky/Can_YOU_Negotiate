import json
import os
import time
from typing import Optional
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

from cognition.schemas import (
    HumanModel, PsychologicalState, RelationshipState,
    SituationModel, Belief, EpistemicStatus, WorldUpdateSignal
)
from cognition.state_engine import StateUpdateSignal
from cognition.belief_engine import (
    BeliefUpdateSignal, SituationUpdateSignal, CommitmentSignal
)
from cognition.relationship_engine import RelationshipUpdateSignal


class CognitiveAppraisal(BaseModel):
    """
    Structured output from the Appraisal LLM.
    Provides signals for deterministic engines. Does NOT decide behavior.
    """
    primary_intent: str = Field(description="What the subject thinks the negotiator is trying to do.")
    primary_intent_confidence: float = Field(ge=0.0, le=100.0)
    alternative_interpretations: list[str] = Field(description="Other plausible interpretations if ambiguous.")
    
    state_updates: StateUpdateSignal = Field(description="Proposed pressure on internal psychological state.")
    relationship_updates: RelationshipUpdateSignal = Field(description="Proposed changes to relationship perception.")
    belief_updates: list[BeliefUpdateSignal] = Field(default_factory=list, description="Proposed evidence for/against existing beliefs.")
    situation_updates: list[SituationUpdateSignal] = Field(default_factory=list, description="Proposed new or updated situation facts.")
    commitment_updates: list[CommitmentSignal] = Field(default_factory=list, description="Proposed commitment lifecycle events.")
    world_updates: list[WorldUpdateSignal] = Field(default_factory=list, description="Proposed world reality updates.")


class AppraisalEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is required for AppraisalEngine.")
            
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=self.api_key
        )
        self.model = "openai/gpt-oss-20b"
        
    def _build_context(
        self,
        event: str,
        recent_context: list[str],
        human: HumanModel,
        state: PsychologicalState,
        relationship: RelationshipState,
        beliefs: list[Belief],
        situation: SituationModel
    ) -> str:
        # Format active beliefs efficiently
        active_beliefs_str = "\n".join([
            f"- ID: {b.id}, Statement: {b.statement}, Confidence: {b.confidence}, Tension: {b.tension}" 
            for b in beliefs
        ])
        
        # Format situation efficiently
        situation_str = "\n".join([
            f"- {k.statement} (Status: {k.epistemic_status.value}, Confidence: {k.confidence})" 
            for k in situation.knowledge
        ])
        
        # Format context
        context_str = "\n".join(recent_context)
        
        prompt = f"""
You are the cognitive appraisal layer of a simulated human.
Your job is ONLY to interpret what the negotiator's latest action means to THIS specific individual.
DO NOT decide what the individual should say or do. DO NOT hallucinate facts.
Output JSON matching the requested schema.

### THE INDIVIDUAL
Personality: {human.personality_narrative}
Dominance: {human.personality.dominance}
Trust Tendency: {human.personality.trust_tendency}
Emotional Volatility: {human.personality.emotional_volatility}
Risk Tolerance: {human.personality.risk_tolerance}

### CURRENT INTERNAL STATE
Fear: {state.fear:.1f}, Anger: {state.anger:.1f}, Stress: {state.stress:.1f}, Hope: {state.hope:.1f}
Desperation: {state.desperation:.1f}, Sense of Control: {state.sense_of_control:.1f}

### CURRENT RELATIONSHIP WITH NEGOTIATOR
Trust: {relationship.trust:.1f}, Respect: {relationship.respect:.1f}, Resentment: {relationship.resentment:.1f}
Perceived Honesty: {relationship.perceived_honesty:.1f}, Perceived Threat: {relationship.perceived_threat:.1f}

### ACTIVE BELIEFS
{active_beliefs_str if active_beliefs_str else "None"}

### SITUATION MODEL
{situation_str if situation_str else "None"}

### RECENT CONVERSATION CONTEXT
{context_str if context_str else "None"}

### NEW EVENT TO APPRAISE
"{event}"

### INSTRUCTIONS
Evaluate the event strictly from the subjective perspective of the individual.
CRITICAL: Your numerical outputs for `relationship_updates.perceived_sincerity` and `credibility_delta` MUST heavily reflect the subject's baseline trust and beliefs.
- If their trust is low or they believe the negotiator lies, `perceived_sincerity` and `credibility_delta` MUST be significantly lower (or negative) than if they trust the negotiator.
- If they are terrified, they might overreact to ambiguity.
Provide the appraisal in valid JSON matching the exact schema.

Schema definition:
{CognitiveAppraisal.model_json_schema()}
"""
        return prompt

    def appraise(
        self,
        event: str,
        human: HumanModel,
        state: PsychologicalState,
        relationship: RelationshipState,
        beliefs: list[Belief],
        situation: SituationModel,
        recent_context: list[str] = None
    ) -> CognitiveAppraisal:
        recent_context = recent_context or []
        prompt = self._build_context(event, recent_context, human, state, relationship, beliefs, situation)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=1024,
                timeout=10.0,
            )
            
            raw_json = response.choices[0].message.content
            return CognitiveAppraisal.model_validate_json(raw_json)
            
        except Exception as e:
            # Fallback behavior: neutral/empty appraisal on failure
            print(f"Appraisal failed: {e}. Returning neutral fallback.")
            return CognitiveAppraisal(
                primary_intent="unknown",
                primary_intent_confidence=0.0,
                alternative_interpretations=["error_during_appraisal"],
                state_updates=StateUpdateSignal(),
                relationship_updates=RelationshipUpdateSignal(),
                belief_updates=[],
                situation_updates=[],
                commitment_updates=[]
            )
