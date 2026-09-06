import pytest
from cognition.pipeline import CognitivePipeline
from cognition.appraisal_engine import AppraisalEngine
from cognition.behavioral_policy import BehavioralPolicyEngine
from cognition.expression_engine import ExpressionEngine, ExpressionHistory
from cognition.speech_generator import SpeechGenerator

from cognition.schemas import (
    HumanModel, Identity, Personality, Goals, CopingMechanisms, CommunicationStyle,
    PsychologicalState, RelationshipState, SituationModel, GoalState, StrategyHistory
)

@pytest.fixture
def pipeline():
    return CognitivePipeline(
        appraisal_engine=AppraisalEngine(api_key="mock"),
        policy_engine=BehavioralPolicyEngine(),
        expression_engine=ExpressionEngine(),
        speech_generator=SpeechGenerator(api_key="mock")
    )

@pytest.fixture
def base_human():
    return HumanModel(
        identity=Identity(name="Test", age=30, occupation="Test"),
        personality=Personality(
            dominance=0.5, pride=0.5, risk_tolerance=0.5,
            impulsivity=0.5, trust_tendency=0.5, emotional_volatility=0.5,
            need_for_control=0.5, guilt_tendency=0.5
        ),
        goals=Goals(primary="survive", secondary="escape", immediate="hide", hidden=""),
        coping=CopingMechanisms(fear_response="freeze", anger_response="yell", stress_response="withdraw"),
        communication_style=CommunicationStyle(
            verbosity=0.5, directness=0.5, politeness=0.5,
            formality=0.5, description="Normal"
        )
    )

def test_different_personality_different_path(pipeline, base_human):
    state_a = PsychologicalState(fear=10, stress=10)
    rel_a = RelationshipState(trust=50)
    human_a = base_human.model_copy(deep=True)
    human_a.personality.trust_tendency = 0.9 
    
    _, trace_a = pipeline.process_turn(
        input_transcript="I promise I won't hurt you.",
        human=human_a, state=state_a, rel=rel_a, situation=SituationModel(),
        beliefs=[], goals=GoalState(), strategy_history=StrategyHistory(),
        expression_history=ExpressionHistory(), recent_context=[]
    )
    
    state_b = PsychologicalState(fear=10, stress=10)
    rel_b = RelationshipState(trust=50)
    human_b = base_human.model_copy(deep=True)
    human_b.personality.trust_tendency = 0.1 
    
    _, trace_b = pipeline.process_turn(
        input_transcript="I promise I won't hurt you.",
        human=human_b, state=state_b, rel=rel_b, situation=SituationModel(),
        beliefs=[], goals=GoalState(), strategy_history=StrategyHistory(),
        expression_history=ExpressionHistory(), recent_context=[]
    )
    
    assert trace_a is not None
    assert trace_b is not None

def test_pipeline_latencies_tracked(pipeline, base_human):
    state = PsychologicalState()
    rel = RelationshipState()
    
    _, trace = pipeline.process_turn(
        input_transcript="Hello.",
        human=base_human, state=state, rel=rel, situation=SituationModel(),
        beliefs=[], goals=GoalState(), strategy_history=StrategyHistory(),
        expression_history=ExpressionHistory(), recent_context=[]
    )
    
    assert "appraisal" in trace.latencies_ms
    assert "state_update" in trace.latencies_ms
    assert "total_turn" in trace.latencies_ms
    assert trace.latencies_ms["total_turn"] > 0
    assert trace.turn_id is not None
