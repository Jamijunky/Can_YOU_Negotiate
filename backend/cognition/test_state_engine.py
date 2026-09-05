"""
Phase 2 Tests: Deterministic State Engine

Covers momentum, bounded changes, recovery, personality sensitivities, 
and realistic trajectory evaluation.
"""

import pytest
import math
from cognition.schemas import PsychologicalState, Personality
from cognition.state_engine import (
    StateUpdateSignal, 
    apply_state_transition, 
    BASELINES
)


@pytest.fixture
def neutral_state():
    return PsychologicalState(
        fear=20.0, anger=10.0, stress=30.0, desperation=20.0,
        guilt=10.0, hope=40.0, sense_of_control=50.0
    )


@pytest.fixture
def average_personality():
    return Personality(
        impulsivity=0.5, dominance=0.5, trust_tendency=0.5,
        emotional_volatility=0.5, need_for_control=0.5,
        pride=0.5, guilt_tendency=0.5, risk_tolerance=0.5
    )


@pytest.fixture
def volatile_aggressive_personality():
    return Personality(
        impulsivity=0.9, dominance=0.9, trust_tendency=0.1,
        emotional_volatility=0.9, need_for_control=0.9,
        pride=0.9, guilt_tendency=0.1, risk_tolerance=0.8
    )


@pytest.fixture
def submissive_stable_personality():
    return Personality(
        impulsivity=0.2, dominance=0.1, trust_tendency=0.8,
        emotional_volatility=0.1, need_for_control=0.2,
        pride=0.2, guilt_tendency=0.8, risk_tolerance=0.2
    )


class TestStateEngineBasic:
    def test_ordinary_event_small_change(self, neutral_state, average_personality):
        signal = StateUpdateSignal(threat_delta=10.0)
        new_state, meta = apply_state_transition(neutral_state, average_personality, signal)
        
        # Fear should go up, but not by a massive amount
        assert new_state.fear > neutral_state.fear
        assert meta.deltas["fear"] < 15.0
        assert meta.deltas["fear"] > 2.0

    def test_severe_event_large_change(self, neutral_state, average_personality):
        signal = StateUpdateSignal(threat_delta=50.0)
        new_state, meta = apply_state_transition(neutral_state, average_personality, signal)
        
        assert new_state.fear > neutral_state.fear
        # Severe event should produce significantly larger change than ordinary
        assert meta.deltas["fear"] > 15.0

    def test_bounded_ranges(self, neutral_state, average_personality):
        # Apply massive, repeated threats
        state = neutral_state
        for _ in range(10):
            signal = StateUpdateSignal(threat_delta=100.0, respect_delta=-100.0)
            state, _ = apply_state_transition(state, average_personality, signal)
            
        assert state.fear <= 100.0
        assert state.anger <= 100.0
        assert state.stress <= 100.0
        assert state.fear >= 0.0

    def test_deterministic_repeatability(self, neutral_state, average_personality):
        signal = StateUpdateSignal(threat_delta=30.0)
        s1, m1 = apply_state_transition(neutral_state, average_personality, signal)
        s2, m2 = apply_state_transition(neutral_state, average_personality, signal)
        
        assert s1.fear == s2.fear
        assert s1.anger == s2.anger
        assert m1.deltas == m2.deltas

    def test_no_negative_or_nan(self, neutral_state, average_personality):
        signal = StateUpdateSignal(threat_delta=-1000.0, hope_delta=-1000.0)
        state, _ = apply_state_transition(neutral_state, average_personality, signal)
        
        for val in [state.fear, state.anger, state.hope, state.stress, state.guilt, state.sense_of_control]:
            assert not math.isnan(val)
            assert not math.isinf(val)
            assert val >= 0.0
            assert val <= 100.0


class TestStateEngineMechanics:
    def test_recovery_no_event(self, average_personality):
        # Start with extreme state
        high_state = PsychologicalState(
            fear=90.0, anger=90.0, stress=90.0, desperation=90.0,
            guilt=90.0, hope=10.0, sense_of_control=10.0
        )
        empty_signal = StateUpdateSignal(time_elapsed_seconds=10.0) # 1 turn elapsed
        
        new_state, _ = apply_state_transition(high_state, average_personality, empty_signal)
        
        # Variables should decay towards baselines
        assert new_state.fear < high_state.fear
        assert new_state.anger < high_state.anger
        assert new_state.hope > high_state.hope
        
    def test_personality_sensitivity(self, neutral_state, volatile_aggressive_personality, submissive_stable_personality):
        signal = StateUpdateSignal(threat_delta=30.0, respect_delta=-30.0)
        
        s_agg, _ = apply_state_transition(neutral_state, volatile_aggressive_personality, signal)
        s_sub, _ = apply_state_transition(neutral_state, submissive_stable_personality, signal)
        
        # Aggressive personality should have more anger and less fear due to dominance
        assert s_agg.anger > s_sub.anger
        # Submissive personality should have more fear
        assert s_sub.fear > s_agg.fear

    def test_interaction_stress_floor(self, neutral_state, average_personality):
        # High fear + anger should automatically raise stress
        high_state = PsychologicalState(fear=90.0, anger=90.0, desperation=90.0, stress=10.0)
        signal = StateUpdateSignal()
        new_state, _ = apply_state_transition(high_state, average_personality, signal)
        
        assert new_state.stress > 50.0  # Floor should pull it up significantly

    def test_conflicting_influences(self, neutral_state, average_personality):
        # Threat pushes fear up, but massive hope pushes it down
        signal = StateUpdateSignal(threat_delta=40.0, hope_delta=80.0)
        s_threat_only, _ = apply_state_transition(neutral_state, average_personality, StateUpdateSignal(threat_delta=40.0))
        s_both, _ = apply_state_transition(neutral_state, average_personality, signal)
        
        # The presence of hope should mitigate the fear increase
        assert s_both.fear < s_threat_only.fear

    def test_momentum_repeated_events(self, neutral_state, average_personality):
        signal = StateUpdateSignal(respect_delta=-10.0) # Small disrespect
        
        s1, _ = apply_state_transition(neutral_state, average_personality, signal)
        s2, _ = apply_state_transition(s1, average_personality, signal)
        s3, _ = apply_state_transition(s2, average_personality, signal)
        
        # Anger should accumulate over time, not just stay at the first delta
        assert s3.anger > s1.anger


class TestRealisticTrajectories:
    def test_trajectory_escalation_and_deescalation(self, neutral_state, average_personality):
        # Turn 1: Mild pressure
        s1, _ = apply_state_transition(neutral_state, average_personality, StateUpdateSignal(threat_delta=15.0, control_delta=-10.0))
        # Turn 2: Escalation (shouting)
        s2, _ = apply_state_transition(s1, average_personality, StateUpdateSignal(threat_delta=30.0, respect_delta=-20.0))
        # Turn 3: Broken promise
        s3, _ = apply_state_transition(s2, average_personality, StateUpdateSignal(respect_delta=-40.0, hope_delta=-30.0))
        
        # Midpoint check: Subject should be highly stressed, angry, and afraid
        assert s3.stress > 50.0
        assert s3.anger > 30.0
        
        # Turn 4: Silence / backing off
        s4, _ = apply_state_transition(s3, average_personality, StateUpdateSignal(time_elapsed_seconds=20.0))
        # Turn 5: Reassurance
        s5, _ = apply_state_transition(s4, average_personality, StateUpdateSignal(threat_delta=-20.0, hope_delta=20.0))
        
        # End check: Should be recovering, but not completely reset
        assert s5.anger < s3.anger
        assert s5.stress < 65.0  # Stress can peak in silence (s4) then start recovering in s5
        assert s5.anger > neutral_state.anger  # Resentment lingers

    def test_property_bounded_input_output(self, average_personality):
        state = PsychologicalState(fear=50, anger=50, stress=50)
        # Apply maximum possible extremes in all directions
        signal_extreme = StateUpdateSignal(
            threat_delta=100.0, respect_delta=-100.0, control_delta=-100.0, 
            moral_significance=100.0, hope_delta=100.0, desperation_delta=100.0
        )
        s_new, _ = apply_state_transition(state, average_personality, signal_extreme)
        
        # Validate all properties are within [0, 100]
        for field, value in s_new.model_dump().items():
            if field == "emotional_pressure":
                continue
            assert 0.0 <= value <= 100.0, f"{field} is {value}, out of bounds"
