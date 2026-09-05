"""
Deterministic State Transition Engine for Psychological State.

This module provides the core state transition functions for the Causal Human Simulator.
It takes a current state, personality, and appraised deltas, and computes the new state,
accounting for inertia, bounded change, interaction effects, and recovery.

Equations & Logic:
1. **Inertia/Volatility**: 
   `effective_delta = raw_delta * (0.2 + 0.8 * personality.emotional_volatility)`
   This ensures even high volatility doesn't cause instant 0-100 swings from a single event.

2. **Personality Sensitivities**:
   - `fear` responds to `threat_delta`, mitigated by `personality.dominance`.
   - `anger` responds to negative `respect_delta` (pride), negative `control_delta` (need_for_control), and positive `threat_delta` (if high dominance).
   - `guilt` responds to `moral_significance` scaled by `guilt_tendency`.
   - `sense_of_control` responds to `control_delta` scaled by `need_for_control`.
   
3. **Recovery/Decay**:
   Variables naturally drift toward their baselines over time (or turns) if no new stimulus is applied.
   `decay_factor = 0.05` per turn.
   `V_new = V_old * (1 - decay_factor) + Baseline * decay_factor`
   Baselines are personality-dependent in some cases, but generally assumed to be resting states (e.g. anger=10, fear=20).

4. **Interaction Effects**:
   - High fear suppresses anger (if dominance < 0.4).
   - High anger suppresses fear (if dominance > 0.6).
   - Hope reduces fear.
   - Stress floor: `stress = max(stress, (fear + anger + desperation) / 3 * 0.7)`

5. **Emotional Pressure**:
   `emotional_pressure` accumulates when concealed intensity > expressed intensity. 
   (Calculated in the Expression layer, but we provide the hook or base math here if needed. 
   For Phase 2, we just ensure it remains bounded).

Expected Interfaces for Phase 3/4:
- `StateUpdateSignal`: The structured deltas produced by the Appraisal layer.
- `TransitionMetadata`: Observability payload detailing why a value changed.
- `apply_state_transition(...) -> (PsychologicalState, TransitionMetadata)`
"""

from dataclasses import dataclass, field
from pydantic import BaseModel
from cognition.schemas import PsychologicalState, Personality


class StateUpdateSignal(BaseModel):
    """
    Structured inputs representing the appraised impact of an event.
    Produced by the Appraisal model (Phase 4), consumed by State Engine (Phase 2).
    Values typically range from -50 to +50.
    """
    threat_delta: float = 0.0
    respect_delta: float = 0.0
    control_delta: float = 0.0
    moral_significance: float = 0.0  # 0 to 100, positive meaning moral violation by subject
    hope_delta: float = 0.0
    desperation_delta: float = 0.0
    time_elapsed_seconds: float = 0.0  # Time since last transition, for decay


class TransitionMetadata(BaseModel):
    """Observability metadata for a single transition."""
    previous_state: PsychologicalState
    new_state: PsychologicalState
    deltas: dict[str, float]
    primary_cause: str = ""


# Configurable Constants
BASELINES = {
    "fear": 20.0,
    "anger": 10.0,
    "stress": 30.0,
    "desperation": 20.0,
    "guilt": 10.0,
    "hope": 40.0,
    "sense_of_control": 50.0,
}

DECAY_RATES = {
    "fear": 0.05,       # Recovers relatively quickly when threat is gone
    "anger": 0.03,      # Lingers longer (resentment)
    "stress": 0.02,     # Slowest to dissipate
    "desperation": 0.01,
    "guilt": 0.01,
    "hope": 0.03,
    "sense_of_control": 0.04,
}


def apply_state_transition(
    current_state: PsychologicalState,
    personality: Personality,
    signal: StateUpdateSignal
) -> tuple[PsychologicalState, TransitionMetadata]:
    """
    Core deterministic transition function.
    """
    # 1. Base Volatility Multiplier
    # Volatility scales from 0.2 (very sluggish) to 1.0 (highly reactive)
    volatility_mult = 0.2 + (0.8 * personality.emotional_volatility)
    
    # Time-based decay modifier (if time elapsed is large, more decay, but cap it so it doesn't instantly zero out)
    # 1 turn ~ approx 5-10 seconds of interaction. Let's say default decay is per-turn.
    decay_modifier = 1.0
    if signal.time_elapsed_seconds > 0:
        decay_modifier = min(5.0, signal.time_elapsed_seconds / 10.0)

    # Dictionary to hold the intermediate values before clamping
    raw_new = {}
    
    # 2. Compute Target Deltas based on Personality Sensitivities
    # Fear responds to threat, mitigated by dominance
    raw_fear_delta = signal.threat_delta * (1.0 - (personality.dominance * 0.7))
    
    # Anger responds to disrespect, loss of control, and threat (if dominant)
    raw_anger_delta = (
        max(0, -signal.respect_delta) * personality.pride * 0.8 +
        max(0, -signal.control_delta) * personality.need_for_control * 0.6 +
        (signal.threat_delta * personality.dominance * 0.5 if signal.threat_delta > 0 else 0)
    )
    # If respect increases, anger can decrease slightly
    if signal.respect_delta > 0:
        raw_anger_delta -= signal.respect_delta * 0.3
        
    # Guilt responds to moral significance
    raw_guilt_delta = signal.moral_significance * personality.guilt_tendency
    
    # Sense of control responds to control delta
    raw_control_delta = signal.control_delta * (0.5 + 0.5 * personality.need_for_control)
    
    # Apply volatility and add to current state
    raw_new["fear"] = current_state.fear + (raw_fear_delta * volatility_mult)
    raw_new["anger"] = current_state.anger + (raw_anger_delta * volatility_mult)
    raw_new["guilt"] = current_state.guilt + (raw_guilt_delta * volatility_mult)
    raw_new["sense_of_control"] = current_state.sense_of_control + (raw_control_delta * volatility_mult)
    raw_new["hope"] = current_state.hope + (signal.hope_delta * volatility_mult)
    raw_new["desperation"] = current_state.desperation + (signal.desperation_delta * volatility_mult)
    raw_new["stress"] = current_state.stress  # Stress is mostly driven by floor/interactions + decay

    # 3. Apply Decay/Recovery towards baseline
    for var in BASELINES:
        current_val = raw_new[var]
        baseline = BASELINES[var]
        rate = DECAY_RATES[var] * decay_modifier
        # Decay towards baseline
        raw_new[var] = current_val * (1 - rate) + baseline * rate

    # 4. Cross-Variable Interactions
    # High fear suppresses anger for submissive personalities
    if personality.dominance < 0.4:
        raw_new["anger"] *= (1.0 - (raw_new["fear"] / 500.0))  # Max 20% suppression
        
    # High anger suppresses fear for dominant personalities
    if personality.dominance > 0.6:
        raw_new["fear"] *= (1.0 - (raw_new["anger"] / 500.0))
        
    # Hope reduces fear gently
    raw_new["fear"] *= (1.0 - (raw_new["hope"] / 800.0))
    
    # Stress floor
    # Stress is driven by fear, anger, desperation, and also directly by lack of control
    stress_floor = (raw_new["fear"] + raw_new["anger"] + raw_new["desperation"] + (100 - raw_new["sense_of_control"])) / 4.0 * 1.5
    raw_new["stress"] = max(raw_new["stress"], stress_floor)

    # Stress also naturally climbs if multiple negative emotions are high, but bounded
    if (raw_new["fear"] > 30 or raw_new["anger"] > 30) and raw_new["hope"] < 40:
        target_stress = raw_new["stress"] + 15.0
        raw_new["stress"] = (raw_new["stress"] * 0.8) + (target_stress * 0.2)

    # 5. Clamping to [0, 100] via the schema validation
    # emotional_pressure is unchanged here; it's updated in expression/appraisal steps, but we carry it forward
    new_state = PsychologicalState(
        fear=raw_new["fear"],
        anger=raw_new["anger"],
        stress=raw_new["stress"],
        desperation=raw_new["desperation"],
        guilt=raw_new["guilt"],
        hope=raw_new["hope"],
        sense_of_control=raw_new["sense_of_control"],
        emotional_pressure=current_state.emotional_pressure
    )

    # Compute actual deltas for observability
    actual_deltas = {
        "fear": new_state.fear - current_state.fear,
        "anger": new_state.anger - current_state.anger,
        "stress": new_state.stress - current_state.stress,
        "desperation": new_state.desperation - current_state.desperation,
        "guilt": new_state.guilt - current_state.guilt,
        "hope": new_state.hope - current_state.hope,
        "sense_of_control": new_state.sense_of_control - current_state.sense_of_control,
    }

    # Determine primary cause roughly
    primary_cause = max(actual_deltas.items(), key=lambda x: abs(x[1]))
    cause_str = f"{primary_cause[0]} changed by {primary_cause[1]:.1f}" if abs(primary_cause[1]) > 1.0 else "natural decay"

    meta = TransitionMetadata(
        previous_state=current_state,
        new_state=new_state,
        deltas=actual_deltas,
        primary_cause=cause_str
    )

    return new_state, meta
