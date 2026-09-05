"""
Phase 3: Relationship Engine.

Manages deterministic updates to RelationshipState.
Ensures history and trajectory are preserved. Differentiates trust growth/decay.
Updates are driven by structured relationship signals.
"""

from pydantic import BaseModel, Field

from cognition.schemas import RelationshipState


class RelationshipUpdateSignal(BaseModel):
    """Signal from Appraisal proposing relationship changes."""
    respect_delta: float = 0.0
    threat_delta: float = 0.0
    perceived_sincerity: float = 0.0  # -100 to 100. Negative = manipulative, Positive = genuine
    credibility_delta: float = 0.0
    rapport_delta: float = 0.0
    violation_magnitude: float = 0.0  # Positive when a promise is broken
    importance: float = Field(ge=0.0, le=100.0, default=50.0)


def update_relationship(
    state: RelationshipState, 
    signal: RelationshipUpdateSignal
) -> tuple[RelationshipState, dict]:
    """
    Deterministically update relationship dimensions based on the signal.
    """
    raw_trust = state.trust
    raw_respect = state.respect
    raw_resentment = state.resentment
    raw_honesty = state.perceived_honesty
    raw_threat = state.perceived_threat
    
    # 1. Honesty & Trust
    # Sincerity heavily impacts perceived honesty, which pulls trust
    if signal.perceived_sincerity != 0:
        honesty_shift = signal.perceived_sincerity * (signal.importance / 100.0)
        raw_honesty = max(0.0, min(100.0, raw_honesty + honesty_shift * 0.5))
        
    # Violation destroys trust quickly, heavily dependent on foundation
    if signal.violation_magnitude > 0:
        # High foundation cushions the blow
        foundation_cushion = (state.trust_foundation / 100.0) * 0.5
        violation_impact = signal.violation_magnitude * (1.0 - foundation_cushion)
        raw_trust -= violation_impact
        raw_honesty -= violation_impact * 1.5
        raw_resentment += violation_impact
        
    # Gradual trust build if sincere and no violations
    elif signal.perceived_sincerity > 20 and signal.credibility_delta >= 0:
        trust_build = (signal.perceived_sincerity / 100.0) * (signal.importance / 100.0) * 10.0
        raw_trust += trust_build
        
    raw_trust = max(0.0, min(100.0, raw_trust))
    raw_honesty = max(0.0, min(100.0, raw_honesty))
    
    # 2. Respect & Resentment
    raw_respect += signal.respect_delta * (signal.importance / 100.0)
    raw_respect = max(0.0, min(100.0, raw_respect))
    
    if signal.respect_delta < -10:
        raw_resentment += abs(signal.respect_delta) * 0.5
        
    # Resentment decays slowly if treated with respect
    if signal.respect_delta > 10 and signal.perceived_sincerity > 0:
        raw_resentment -= signal.respect_delta * 0.2
        
    raw_resentment = max(0.0, min(100.0, raw_resentment))
    
    # 3. Threat
    raw_threat += signal.threat_delta
    raw_threat = max(0.0, min(100.0, raw_threat))
    
    # 4. Trajectories & Foundation
    # Exponential moving average for trajectories
    alpha = 0.3
    trust_delta = raw_trust - state.trust
    new_trust_traj = (state.trust_trajectory * (1 - alpha)) + (trust_delta * alpha)
    
    respect_delta = raw_respect - state.respect
    new_respect_traj = (state.respect_trajectory * (1 - alpha)) + (respect_delta * alpha)
    
    # Foundation grows slowly when trust is high and rising steadily (not spiking)
    new_foundation = state.trust_foundation
    if trust_delta > 0 and new_trust_traj > 0 and raw_trust > 50:
        # Grows a tiny bit per positive turn
        new_foundation = min(100.0, new_foundation + 1.0)
    # Foundation drops if trust plummets
    if trust_delta < -15:
        new_foundation = max(0.0, new_foundation - 5.0)
        
    new_state = state.model_copy(update={
        "trust": raw_trust,
        "trust_trajectory": new_trust_traj,
        "trust_foundation": new_foundation,
        "respect": raw_respect,
        "respect_trajectory": new_respect_traj,
        "perceived_honesty": raw_honesty,
        "resentment": raw_resentment,
        "perceived_threat": raw_threat,
        "rapport": max(0.0, min(100.0, state.rapport + signal.rapport_delta)),
    })
    
    meta = {
        "trust_delta": trust_delta,
        "trust_traj": new_trust_traj,
        "respect_delta": respect_delta,
        "honesty_delta": raw_honesty - state.perceived_honesty,
        "foundation_delta": new_foundation - state.trust_foundation
    }
    
    return new_state, meta
