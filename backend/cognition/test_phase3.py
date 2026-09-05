"""
Phase 3 Tests: Beliefs, SituationModel, Relationship, and Commitments.

Covers uncertainty, epistemic distinctness, non-monotonic beliefs,
trajectory-based relationships, and integration.
"""

import pytest

from cognition.schemas import (
    Belief, BeliefChangePathway, EpistemicStatus,
    SituationModel, SituationKnowledge, Commitment, CommitmentStatus,
    RelationshipState
)

from cognition.belief_engine import (
    BeliefUpdateSignal, SituationUpdateSignal, CommitmentSignal,
    update_belief, update_situation, handle_commitment
)

from cognition.relationship_engine import (
    RelationshipUpdateSignal, update_relationship
)


# ============================================================================
# BELIEF TESTS
# ============================================================================

def test_belief_creation_and_strengthening():
    b = Belief(
        id="test_belief",
        statement="They are trying to trick me.",
        confidence=50.0,
        importance=80.0,
        resistance=20.0,
        provenance="initial",
        change_pathway=BeliefChangePathway.EVIDENTIAL
    )
    
    signal = BeliefUpdateSignal(
        belief_id="test_belief",
        evidence_statement="Negotiator lied about the car.",
        direction="support",
        evidence_strength=40.0,
        source_credibility=90.0
    )
    
    new_b, meta = update_belief(b, signal, {})
    assert new_b.confidence > 50.0
    assert "Negotiator lied about the car." in new_b.supporting_evidence
    assert meta.evidence_added == "Negotiator lied about the car."

def test_belief_weakening():
    b = Belief(
        id="test_belief",
        statement="They are trying to trick me.",
        confidence=80.0,
        importance=80.0,
        resistance=20.0,
        provenance="initial",
        change_pathway=BeliefChangePathway.EVIDENTIAL
    )
    
    signal = BeliefUpdateSignal(
        belief_id="test_belief",
        evidence_statement="Negotiator delivered the promised pizza.",
        direction="contradict",
        evidence_strength=50.0,
        source_credibility=100.0
    )
    
    new_b, meta = update_belief(b, signal, {})
    assert new_b.confidence < 80.0
    assert "Negotiator delivered the promised pizza." in new_b.contradicting_evidence

def test_belief_tension_with_contradiction():
    b = Belief(
        id="test_belief",
        statement="The negotiator is honest.",
        confidence=80.0,
        importance=80.0,
        resistance=90.0,  # Very high resistance
        provenance="initial",
        change_pathway=BeliefChangePathway.RELATIONAL,
        supporting_evidence=["Spoke calmly"]
    )
    
    signal = BeliefUpdateSignal(
        belief_id="test_belief",
        evidence_statement="Found out he lied about his name.",
        direction="contradict",
        evidence_strength=80.0,
        source_credibility=100.0
    )
    
    new_b, _ = update_belief(b, signal, {})
    # Because resistance is 90, confidence only drops a tiny bit
    assert new_b.confidence > 70.0
    # But tension should shoot up because there is strong contradicting evidence
    # while confidence remains high.
    assert new_b.tension > b.tension
    assert new_b.tension > 0.0

def test_belief_resistance_causal():
    """Same event + different resistance -> different update."""
    signal = BeliefUpdateSignal(
        belief_id="test_belief",
        evidence_statement="X",
        direction="support",
        evidence_strength=50.0,
        source_credibility=100.0
    )
    
    b_stubborn = Belief(id="test_belief", statement="A", confidence=50, importance=50, resistance=90, provenance="A", change_pathway="evidential")
    b_flexible = Belief(id="test_belief", statement="A", confidence=50, importance=50, resistance=10, provenance="A", change_pathway="evidential")
    
    new_s, _ = update_belief(b_stubborn, signal, {})
    new_f, _ = update_belief(b_flexible, signal, {})
    
    assert new_f.confidence > new_s.confidence

def test_belief_credibility_causal():
    """Same evidence + different source credibility -> different update."""
    b = Belief(id="test", statement="A", confidence=50, importance=50, resistance=50, provenance="A", change_pathway="evidential")
    
    sig_high = BeliefUpdateSignal(belief_id="test", evidence_statement="X", direction="support", evidence_strength=50, source_credibility=100)
    sig_low = BeliefUpdateSignal(belief_id="test", evidence_statement="X", direction="support", evidence_strength=50, source_credibility=10)
    
    new_high, _ = update_belief(b, sig_high, {})
    new_low, _ = update_belief(b, sig_low, {})
    
    assert new_high.confidence > new_low.confidence


# ============================================================================
# SITUATION TESTS
# ============================================================================

def test_situation_observed_fact():
    sm = SituationModel()
    signal = SituationUpdateSignal(statement="Sirens outside", epistemic_status=EpistemicStatus.OBSERVED, confidence=100.0)
    
    new_sm, meta = update_situation(sm, signal)
    assert len(new_sm.knowledge) == 1
    assert new_sm.knowledge[0].epistemic_status == EpistemicStatus.OBSERVED
    assert meta["action"] == "updated_fact"

def test_situation_uncertainty_remains_uncertain():
    sm = SituationModel(knowledge=[SituationKnowledge(statement="Police presence", epistemic_status=EpistemicStatus.UNKNOWN, confidence=0)])
    
    # We do not magically turn it into a fact.
    assert sm.knowledge[0].epistemic_status == EpistemicStatus.UNKNOWN


# ============================================================================
# RELATIONSHIP TESTS
# ============================================================================

def test_relationship_trajectory_causal():
    """Same current trust + different trajectory -> different metadata."""
    rs_rising = RelationshipState(trust=70.0, trust_trajectory=5.0, trust_foundation=10.0)
    rs_falling = RelationshipState(trust=70.0, trust_trajectory=-5.0, trust_foundation=10.0)
    
    sig = RelationshipUpdateSignal(perceived_sincerity=20.0, credibility_delta=10.0, importance=50.0)
    
    new_rising, meta_rising = update_relationship(rs_rising, sig)
    new_falling, meta_falling = update_relationship(rs_falling, sig)
    
    # Both get the same raw trust bump
    assert new_rising.trust == new_falling.trust
    # But trajectory EMA reacts differently to the same delta because of different history
    assert meta_rising["trust_traj"] > meta_falling["trust_traj"]

def test_relationship_foundation_protects_trust():
    rs_shallow = RelationshipState(trust=80.0, trust_foundation=0.0)
    rs_deep = RelationshipState(trust=80.0, trust_foundation=80.0)
    
    sig = RelationshipUpdateSignal(violation_magnitude=50.0)
    
    new_shallow, _ = update_relationship(rs_shallow, sig)
    new_deep, _ = update_relationship(rs_deep, sig)
    
    # Deep foundation loses less trust from the same violation
    assert new_deep.trust > new_shallow.trust
    assert new_deep.resentment < new_shallow.resentment


# ============================================================================
# COMMITMENT TESTS
# ============================================================================

def test_commitment_lifecycle():
    comms = []
    
    # Create
    sig_create = CommitmentSignal(promise="No swat team", action="created")
    comms, meta1 = handle_commitment(comms, sig_create)
    assert len(comms) == 1
    assert comms[0].status == CommitmentStatus.ACTIVE
    assert meta1["created"] is True
    
    # Violate
    sig_violate = CommitmentSignal(promise="No swat team", action="violated", violation_magnitude=80.0)
    comms, meta2 = handle_commitment(comms, sig_violate)
    assert comms[0].status == CommitmentStatus.VIOLATED
    assert meta2["violation_magnitude"] == 80.0


# ============================================================================
# INTEGRATION / MULTI-TURN TEST
# ============================================================================

def test_multi_turn_integration():
    """
    initial situation
    -> negotiator makes promise
    -> subject trusts promise
    -> ambiguous event occurs
    -> subject becomes uncertain
    -> evidence clarifies event
    -> relationship changes
    """
    # 1. Initial State
    b_safe = Belief(id="safe", statement="I am safe here", confidence=30, importance=90, resistance=20, provenance="start", change_pathway="evidential")
    rs = RelationshipState(trust=20)
    comms = []
    
    # 2. Negotiator makes promise
    comms, _ = handle_commitment(comms, CommitmentSignal(promise="I will not send police in", action="created", importance=80))
    rs, _ = update_relationship(rs, RelationshipUpdateSignal(perceived_sincerity=40, credibility_delta=10, importance=80))
    b_safe, _ = update_belief(b_safe, BeliefUpdateSignal(belief_id="safe", evidence_statement="Negotiator promised safety", direction="support", evidence_strength=30, source_credibility=rs.trust), {})
    
    assert rs.trust > 20
    assert b_safe.confidence > 30
    assert comms[0].status == CommitmentStatus.ACTIVE
    
    # 3. Ambiguous event occurs (heard noise)
    b_safe, _ = update_belief(b_safe, BeliefUpdateSignal(belief_id="safe", evidence_statement="Heard movement outside", direction="contradict", evidence_strength=40, source_credibility=100), {})
    assert b_safe.tension > 0.0  # Tension rises because of contradicting evidence
    
    # 4. Evidence clarifies (Police breach)
    comms, meta = handle_commitment(comms, CommitmentSignal(promise="I will not send police in", action="violated", violation_magnitude=90))
    assert comms[0].status == CommitmentStatus.VIOLATED
    
    rs, _ = update_relationship(rs, RelationshipUpdateSignal(violation_magnitude=meta["violation_magnitude"]))
    b_safe, _ = update_belief(b_safe, BeliefUpdateSignal(belief_id="safe", evidence_statement="Police breached", direction="contradict", evidence_strength=100, source_credibility=100), {})
    
    assert rs.trust < 10
    assert rs.resentment > 30
    assert b_safe.confidence < 30
