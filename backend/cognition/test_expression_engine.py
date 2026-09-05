import pytest
import time
from cognition.schemas import (
    HumanModel, Identity, Personality,
    Goals, CopingMechanisms, CommunicationStyle,
    PsychologicalState, RelationshipState,
    BehavioralDecision, BehavioralCandidate, ConsequencePrediction,
    Expression
)
from cognition.expression_engine import ExpressionEngine, ExpressionHistory

@pytest.fixture
def engine():
    return ExpressionEngine(momentum_weight=0.3)

@pytest.fixture
def base_human():
    return HumanModel(
        identity=Identity(name="Test", age=30, occupation="Test"),
        personality=Personality(
            dominance=0.5,
            pride=0.5, risk_tolerance=0.5,
            impulsivity=0.5,
            trust_tendency=0.5, emotional_volatility=0.5,
            need_for_control=0.5, guilt_tendency=0.5
        ),
        goals=Goals(primary="survive", secondary="escape", immediate="hide", hidden=""),
        coping=CopingMechanisms(fear_response="freeze", anger_response="yell", stress_response="withdraw"),
        communication_style=CommunicationStyle(
            verbosity=0.5, directness=0.5, politeness=0.5,
            formality=0.5, description="Normal"
        )
    )

@pytest.fixture
def base_decision():
    return BehavioralDecision(
        candidates=[],
        selected=BehavioralCandidate(
            action="demand",
            target="",
            intensity=0.8,
            information_strategy="truth",
            score=50.0,
            consequence_prediction=ConsequencePrediction(
                expected_negotiator_response="neutral_negotiation",
                expected_immediate_goal_effect="aligned",
                expected_longterm_goal_effect="unknown",
                risk=50.0,
                relationship_consequence="neutral",
                reversibility="reversible"
            ),
            rationale=""
        ),
        selection_method="highest_score",
        hesitation=False
    )

def test_personality_causality(engine, base_human, base_decision):
    """same behavior + diff personality -> diff expression"""
    state = PsychologicalState(fear=50.0)
    rel = RelationshipState()
    
    # Subject A: Highly controlled
    human_a = base_human.model_copy(deep=True)
    human_a.personality.impulsivity = 0.0
    history_a = ExpressionHistory()
    res_a = engine.generate_expression(human_a, state, rel, base_decision, history_a, seed=42)
    
    # Subject B: Poor control
    human_b = base_human.model_copy(deep=True)
    human_b.personality.impulsivity = 1.0
    history_b = ExpressionHistory()
    res_b = engine.generate_expression(human_b, state, rel, base_decision, history_b, seed=42)
    
    # Assert expression differs
    assert res_a.expression.speech_control > res_b.expression.speech_control
    assert res_a.expression.emotional_leakage < res_b.expression.emotional_leakage
    # Assert behavior did NOT change
    assert base_decision.selected.action == "demand"

def test_state_causality(engine, base_human, base_decision):
    """same person + diff state -> diff expression"""
    rel = RelationshipState()
    
    state_calm = PsychologicalState(fear=10.0, stress=10.0)
    res_calm = engine.generate_expression(base_human, state_calm, rel, base_decision, ExpressionHistory(), seed=42)
    
    state_panicked = PsychologicalState(fear=90.0, stress=90.0)
    res_panicked = engine.generate_expression(base_human, state_panicked, rel, base_decision, ExpressionHistory(), seed=42)
    
    assert res_calm.expression.hesitation_tendency < res_panicked.expression.hesitation_tendency
    assert res_calm.expression.emotional_leakage < res_panicked.expression.emotional_leakage

def test_behavior_causality(engine, base_human):
    """same person/state + diff behavior -> diff expression"""
    state = PsychologicalState()
    rel = RelationshipState()
    
    dec_demand = BehavioralDecision(
        candidates=[],
        selected=BehavioralCandidate(action="demand", intensity=0.8, information_strategy="truth", score=50.0, consequence_prediction=ConsequencePrediction(expected_negotiator_response="neutral_negotiation", expected_immediate_goal_effect="aligned", expected_longterm_goal_effect="unknown", risk=50.0, relationship_consequence="neutral", reversibility="reversible"), rationale=""),
        selection_method="highest_score", hesitation=False
    )
    res_demand = engine.generate_expression(base_human, state, rel, dec_demand, ExpressionHistory(), seed=42)
    
    dec_withdraw = BehavioralDecision(
        candidates=[],
        selected=BehavioralCandidate(action="withdraw", intensity=0.8, information_strategy="truth", score=50.0, consequence_prediction=ConsequencePrediction(expected_negotiator_response="neutral_negotiation", expected_immediate_goal_effect="aligned", expected_longterm_goal_effect="unknown", risk=50.0, relationship_consequence="neutral", reversibility="reversible"), rationale=""),
        selection_method="highest_score", hesitation=False
    )
    res_withdraw = engine.generate_expression(base_human, state, rel, dec_withdraw, ExpressionHistory(), seed=42)
    
    assert res_demand.expression.verbal_energy > res_withdraw.expression.verbal_energy
    assert res_demand.expression.directness > res_withdraw.expression.directness

def test_stochasticity_and_bounds(engine, base_human, base_decision):
    """Check bounds and seed determinism."""
    state = PsychologicalState()
    rel = RelationshipState()
    
    # Same seed -> same result
    res1 = engine.generate_expression(base_human, state, rel, base_decision, ExpressionHistory(), seed=99)
    res2 = engine.generate_expression(base_human, state, rel, base_decision, ExpressionHistory(), seed=99)
    assert res1.expression.dict() == res2.expression.dict()
    
    # Different seed -> small variation (jitter)
    res3 = engine.generate_expression(base_human, state, rel, base_decision, ExpressionHistory(), seed=100)
    assert res1.expression.dict() != res3.expression.dict()
    
    # Bounds check
    assert 0.0 <= res1.expression.speech_control <= 1.0
    assert 0.0 <= res1.expression.verbal_energy <= 1.0
    assert 0.0 <= res1.expression.hesitation_tendency <= 1.0
    
def test_momentum(engine, base_human, base_decision):
    """Expression should have temporal continuity."""
    state = PsychologicalState()
    rel = RelationshipState()
    history = ExpressionHistory()
    
    res1 = engine.generate_expression(base_human, state, rel, base_decision, history, seed=42)
    
    # Extreme state change
    state_extreme = PsychologicalState(fear=100.0, anger=100.0)
    # Generate without history
    res_no_hist = engine.generate_expression(base_human, state_extreme, rel, base_decision, ExpressionHistory(), seed=42)
    # Generate with history
    res_with_hist = engine.generate_expression(base_human, state_extreme, rel, base_decision, history, seed=42)
    
    # The one with history should be closer to res1 than the one without history
    diff_with = abs(res_with_hist.expression.verbal_energy - res1.expression.verbal_energy)
    diff_without = abs(res_no_hist.expression.verbal_energy - res1.expression.verbal_energy)
    assert diff_with < diff_without

def test_latency(engine, base_human, base_decision):
    """Phase 6 execution time must be low millisecond."""
    state = PsychologicalState()
    rel = RelationshipState()
    history = ExpressionHistory()
    
    start = time.perf_counter()
    engine.generate_expression(base_human, state, rel, base_decision, history)
    end = time.perf_counter()
    
    latency_ms = (end - start) * 1000.0
    assert latency_ms < 5.0  # Must be under 5ms

def test_multi_turn_simulation(engine, base_human):
    """Simulate gradual state changes and check expression continuity."""
    history = ExpressionHistory()
    dec = BehavioralDecision(
        candidates=[],
        selected=BehavioralCandidate(action="negotiate", intensity=0.5, information_strategy="truth", score=50.0, consequence_prediction=ConsequencePrediction(expected_negotiator_response="neutral", expected_immediate_goal_effect="aligned", expected_longterm_goal_effect="unknown", risk=0.0, relationship_consequence="neutral", reversibility="reversible"), rationale=""),
        selection_method="highest_score", hesitation=False
    )
    
    # T1: Calm
    st1 = PsychologicalState(fear=10, stress=10)
    r1 = engine.generate_expression(base_human, st1, RelationshipState(), dec, history, seed=1)
    
    # T2: Pressure rising
    st2 = PsychologicalState(fear=30, stress=40)
    r2 = engine.generate_expression(base_human, st2, RelationshipState(), dec, history, seed=2)
    
    # T3: Panic
    st3 = PsychologicalState(fear=90, stress=90)
    r3 = engine.generate_expression(base_human, st3, RelationshipState(), dec, history, seed=3)
    
    # T4: Recovery
    st4 = PsychologicalState(fear=50, stress=50)
    r4 = engine.generate_expression(base_human, st4, RelationshipState(), dec, history, seed=4)
    
    # Hesitation should peak at T3
    assert r1.expression.hesitation_tendency < r3.expression.hesitation_tendency
    assert r3.expression.hesitation_tendency > r4.expression.hesitation_tendency
    # Emotional leakage should peak at T3
    assert r1.expression.emotional_leakage < r3.expression.emotional_leakage

