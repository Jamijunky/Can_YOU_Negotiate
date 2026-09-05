import pytest
from cognition.schemas import (
    HumanModel, Personality, PsychologicalState, RelationshipState,
    SituationModel, Belief, Identity, Goals, CopingMechanisms, CommunicationStyle,
    StrategyHistory, StrategyRecord
)
from cognition.behavioral_policy import BehavioralPolicyEngine

@pytest.fixture
def dummy_human_props():
    return {
        "identity": Identity(name="Alex", age=30, gender="neutral", life_history="None", occupation="None", secrets=[]),
        "goals": Goals(primary="Survive", secondary="None", immediate="None", hidden="None"),
        "coping": CopingMechanisms(fear_response="silence", anger_response="explosive", stress_response="talking_more"),
        "communication_style": CommunicationStyle(description="x", directness=0.5, verbosity=0.5, formality=0.5, manipulation=0.0, hostility=0.0, habits=[])
    }

@pytest.fixture
def base_human(dummy_human_props):
    return HumanModel(
        id="subject_1",
        name="Alex",
        personality=Personality(
            impulsivity=0.5, dominance=0.5, trust_tendency=0.5, emotional_volatility=0.5,
            need_for_control=0.5, pride=0.5, guilt_tendency=0.5, risk_tolerance=0.5
        ),
        personality_narrative="Average person.",
        triggers=[], values=[],
        **dummy_human_props
    )

@pytest.fixture
def engine():
    return BehavioralPolicyEngine(seed=42)

def test_personality_effect(engine, base_human):
    """Test that dominance and risk tolerance change behavior."""
    state = PsychologicalState(anger=50.0)
    relationship = RelationshipState(perceived_threat=50.0)
    history = StrategyHistory()
    
    # 1. Dominant, proud, high risk
    aggro_human = base_human.model_copy(deep=True)
    aggro_human.personality.dominance = 0.9
    aggro_human.personality.pride = 0.9
    aggro_human.personality.risk_tolerance = 0.9
    
    dec_aggro = engine.select_action(aggro_human, state, relationship, SituationModel(), [], history, temperature=0.0)
    assert dec_aggro.selected.action in ["escalate", "threaten", "challenge", "demand"]
    
    # 2. Submissive, fearful, low risk
    sub_human = base_human.model_copy(deep=True)
    sub_human.personality.dominance = 0.1
    sub_human.personality.pride = 0.1
    sub_human.personality.risk_tolerance = 0.1
    state_fear = PsychologicalState(fear=80.0, desperation=80.0)
    
    dec_sub = engine.select_action(sub_human, state_fear, relationship, SituationModel(), [], history, temperature=0.0)
    assert dec_sub.selected.action in ["surrender", "seek_reassurance", "withdraw"]


def test_relationship_effect(engine, base_human):
    """Test that relationship trust changes behavior."""
    state = PsychologicalState()
    history = StrategyHistory()
    
    # High trust
    rel_high_trust = RelationshipState(trust=90.0)
    dec_trust = engine.select_action(base_human, state, rel_high_trust, SituationModel(), [], history, temperature=0.0)
    
    # Low trust
    rel_low_trust = RelationshipState(trust=10.0, perceived_threat=90.0)
    dec_distrust = engine.select_action(base_human, state, rel_low_trust, SituationModel(), [], history, temperature=0.0)
    
    assert dec_trust.selected.action != dec_distrust.selected.action
    # High trust encourages disclosure/reassurance/bargaining
    # Low trust + high threat encourages withdrawal/lying/evading


def test_psychological_state_effect(engine, base_human):
    """Test that psychological state (fear vs anger) changes behavior."""
    rel = RelationshipState(perceived_threat=50.0)
    history = StrategyHistory()
    
    state_angry = PsychologicalState(anger=90.0)
    dec_angry = engine.select_action(base_human, state_angry, rel, SituationModel(), [], history, temperature=0.0)
    
    state_fear = PsychologicalState(fear=90.0)
    dec_fear = engine.select_action(base_human, state_fear, rel, SituationModel(), [], history, temperature=0.0)
    
    assert dec_angry.selected.action != dec_fear.selected.action


def test_belief_effect(engine, base_human):
    """Test that beliefs can override defaults."""
    state = PsychologicalState(desperation=80.0)  # Wants to surrender
    rel = RelationshipState(trust=50.0)
    history = StrategyHistory()
    
    # Normally might surrender due to desperation
    sub_human = base_human.model_copy(deep=True)
    sub_human.personality.pride = 0.1
    dec_normal = engine.select_action(sub_human, state, rel, SituationModel(), [], history, temperature=0.0)
    
    # Add belief that negotiator will kill them
    b = Belief(id="b1", statement="If I surrender they will kill me", confidence=90, importance=100, resistance=20, provenance="past", change_pathway="evidential")
    dec_paranoid = engine.select_action(sub_human, state, rel, SituationModel(), [b], history, temperature=0.0)
    
    assert dec_normal.selected.action != dec_paranoid.selected.action


def test_action_history_anti_repetition(engine, base_human):
    """Test that repeatedly failing a strategy lowers its utility."""
    state = PsychologicalState(anger=50.0)
    rel = RelationshipState()
    
    # Initial preference without history
    history = StrategyHistory()
    dec1 = engine.select_action(base_human, state, rel, SituationModel(), [], history, temperature=0.0)
    top_action = dec1.selected.action
    
    # Now simulate that action failing repeatedly
    history.records.append(StrategyRecord(action=top_action, turn_number=1, perceived_outcome="ineffective"))
    history.records.append(StrategyRecord(action=top_action, turn_number=2, perceived_outcome="ineffective"))
    
    dec2 = engine.select_action(base_human, state, rel, SituationModel(), [], history, temperature=0.0)
    assert dec2.selected.action != top_action


def test_stochasticity(base_human):
    """Test that temperature > 0.0 allows variance for near-tied actions."""
    state = PsychologicalState(anger=50.0, fear=50.0)  # Conflict
    rel = RelationshipState()
    history = StrategyHistory()
    
    # Zero temp should always return the exact same thing
    engine_det = BehavioralPolicyEngine(seed=42)
    action1 = engine_det.select_action(base_human, state, rel, SituationModel(), [], history, temperature=0.0).selected.action
    action2 = engine_det.select_action(base_human, state, rel, SituationModel(), [], history, temperature=0.0).selected.action
    assert action1 == action2
    
    # High temp across different seeds should yield different results
    actions = set()
    for i in range(10):
        engine_rand = BehavioralPolicyEngine(seed=i)
        dec = engine_rand.select_action(base_human, state, rel, SituationModel(), [], history, temperature=1.0)
        actions.add(dec.selected.action)
        
    assert len(actions) > 1


def test_multi_turn_simulation(base_human):
    """Simulate adaptation over several turns."""
    engine = BehavioralPolicyEngine(seed=123)
    history = StrategyHistory()
    rel = RelationshipState(trust=20.0, perceived_threat=80.0)
    state = PsychologicalState(fear=70.0)
    
    # Turn 1: High fear, low trust -> likely evade or withdraw
    dec1 = engine.select_action(base_human, state, rel, SituationModel(), [], history, temperature=0.0)
    assert dec1.selected.action in ["withdraw", "remain_silent", "evade", "lie"]
    
    # Negotiator reassures, fear drops, trust increases
    state.fear = 40.0
    state.hope = 60.0
    rel.trust = 60.0
    rel.perceived_threat = 40.0
    
    # Turn 2: Should change to more cooperative action
    dec2 = engine.select_action(base_human, state, rel, SituationModel(), [], history, temperature=0.0)
    assert dec2.selected.action not in ["withdraw", "remain_silent"]
    assert dec2.selected.action in ["seek_reassurance", "bargain", "question", "fully_disclose", "admit"]


def test_fallback_behavior(base_human):
    """Ensure engine fails gracefully."""
    engine = BehavioralPolicyEngine()
    
    # Passing None to state should cause exception in goal weight calc
    dec = engine.select_action(base_human, None, RelationshipState(), SituationModel(), [], StrategyHistory())
    
    assert dec.selection_method == "fallback"
    assert dec.selected.action == "remain_silent"
