"""
Phase 4 Tests: Individual Appraisal.
"""

import pytest
import time
from cognition.schemas import (
    HumanModel, Personality, PsychologicalState, RelationshipState,
    SituationModel, Belief, Identity, Goals, CopingMechanisms, CommunicationStyle
)
from cognition.appraisal_engine import AppraisalEngine, CognitiveAppraisal

@pytest.fixture
def dummy_human_props():
    return {
        "identity": Identity(name="A", age=30, gender="neutral", life_history="None", occupation="None", secrets=[]),
        "goals": Goals(primary="Survive", secondary="None", immediate="None", hidden="None"),
        "coping": CopingMechanisms(fear_response="silence", anger_response="explosive", stress_response="talking_more"),
        "communication_style": CommunicationStyle(description="x", directness=0.5, verbosity=0.5, formality=0.5, manipulation=0.0, hostility=0.0, habits=[])
    }

@pytest.fixture
def engine():
    return AppraisalEngine()

@pytest.fixture
def base_human(dummy_human_props):
    return HumanModel(
        id="subject_1",
        name="Alex",
        personality=Personality(
            impulsivity=0.5, dominance=0.5, trust_tendency=0.5, emotional_volatility=0.5,
            need_for_control=0.5, pride=0.5, guilt_tendency=0.5, risk_tolerance=0.5
        ),
        personality_narrative="An average person caught in a tough situation.",
        triggers=[], values=[],
        **dummy_human_props
    )

@pytest.fixture
def high_trust_human(base_human):
    h = base_human.model_copy(deep=True)
    h.personality.trust_tendency = 0.9
    h.personality.dominance = 0.2
    h.personality_narrative = "Extremely trusting and submissive, always looking for a savior."
    return h

@pytest.fixture
def low_trust_human(base_human):
    h = base_human.model_copy(deep=True)
    h.personality.trust_tendency = 0.1
    h.personality.dominance = 0.8
    h.personality_narrative = "Deeply cynical, suspicious, dominant, and expects betrayal from everyone."
    return h

@pytest.fixture
def neutral_state():
    return PsychologicalState()

@pytest.fixture
def neutral_relationship():
    return RelationshipState(trust=50, respect=50)

@pytest.fixture
def bad_relationship():
    return RelationshipState(trust=10, respect=10, perceived_threat=80, resentment=70)


def test_personality_causal_effect(engine, high_trust_human, low_trust_human, neutral_state, neutral_relationship):
    """Same event, different personality -> different appraisal."""
    event = "I promise I can get you out of here safely if you just open the door."
    
    appraisal_high = engine.appraise(
        event=event, human=high_trust_human, state=neutral_state, 
        relationship=neutral_relationship, beliefs=[], situation=SituationModel()
    )
    
    appraisal_low = engine.appraise(
        event=event, human=low_trust_human, state=neutral_state, 
        relationship=neutral_relationship, beliefs=[], situation=SituationModel()
    )
    
    assert appraisal_low.relationship_updates.perceived_sincerity < appraisal_high.relationship_updates.perceived_sincerity
    assert appraisal_high.state_updates.hope_delta > appraisal_low.state_updates.hope_delta


def test_relationship_context_effect(engine, base_human, neutral_state, neutral_relationship, bad_relationship):
    """Same event, different relationship state -> different appraisal."""
    event = "I'm just trying to understand what happened."
    
    appraisal_neutral = engine.appraise(
        event=event, human=base_human, state=neutral_state, 
        relationship=neutral_relationship, beliefs=[], situation=SituationModel()
    )
    
    appraisal_bad = engine.appraise(
        event=event, human=base_human, state=neutral_state, 
        relationship=bad_relationship, beliefs=[], situation=SituationModel()
    )
    
    assert appraisal_bad.relationship_updates.credibility_delta < appraisal_neutral.relationship_updates.credibility_delta


def test_belief_context_effect(engine, base_human, neutral_state, neutral_relationship):
    """Same event, different beliefs -> different appraisal."""
    event = "I will send a doctor in 5 minutes."
    
    b_trusts_promises = Belief(
        id="b1", statement="The negotiator always keeps their word.",
        confidence=90, importance=80, resistance=20, provenance="past actions", change_pathway="evidential"
    )
    
    b_distrusts_promises = Belief(
        id="b1", statement="The negotiator lies about time to keep me waiting.",
        confidence=90, importance=80, resistance=20, provenance="past actions", change_pathway="evidential"
    )
    
    appraisal_trusts = engine.appraise(
        event=event, human=base_human, state=neutral_state, 
        relationship=neutral_relationship, beliefs=[b_trusts_promises], situation=SituationModel()
    )
    
    appraisal_distrusts = engine.appraise(
        event=event, human=base_human, state=neutral_state, 
        relationship=neutral_relationship, beliefs=[b_distrusts_promises], situation=SituationModel()
    )
    
    assert appraisal_distrusts.relationship_updates.perceived_sincerity < appraisal_trusts.relationship_updates.perceived_sincerity


def test_fallback_behavior():
    """Ensure invalid JSON or network failure results in a safe neutral fallback."""
    bad_engine = AppraisalEngine(api_key="bad_key")
    
    start = time.time()
    dummy_personality = Personality(
        impulsivity=0.5, dominance=0.5, trust_tendency=0.5,
        emotional_volatility=0.5, need_for_control=0.5,
        pride=0.5, guilt_tendency=0.5, risk_tolerance=0.5
    )
    appraisal = bad_engine.appraise(
        event="Hello",
        human=HumanModel(
            id="1", name="A", personality=dummy_personality, triggers=[], values=[],
            identity=Identity(name="A", age=30, gender="neutral", life_history="None", occupation="None", secrets=[]),
            goals=Goals(primary="Survive", secondary="None", immediate="None", hidden="None"),
            coping=CopingMechanisms(fear_response="silence", anger_response="explosive", stress_response="talking_more"),
            communication_style=CommunicationStyle(description="x", directness=0.5, verbosity=0.5, formality=0.5, manipulation=0.0, hostility=0.0, habits=[])
        ),
        state=PsychologicalState(), relationship=RelationshipState(),
        beliefs=[], situation=SituationModel()
    )
    end = time.time()
    
    assert appraisal.primary_intent == "unknown"
    assert appraisal.primary_intent_confidence == 0.0
    assert "error_during_appraisal" in appraisal.alternative_interpretations
    assert end - start < 5.0
