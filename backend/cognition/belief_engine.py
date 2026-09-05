"""
Phase 3: Belief and Situation Engine.

Manages deterministic updates to the SituationModel and Beliefs.
LLMs do not mutate these structures; they provide structured interpretation signals
(e.g., BeliefUpdateSignal) which are processed here according to resistance, credibility,
and existing confidence.
"""

from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel, Field

from cognition.schemas import (
    Belief,
    SituationModel,
    SituationKnowledge,
    Commitment,
    CommitmentStatus,
    EpistemicStatus,
)


class BeliefUpdateSignal(BaseModel):
    """Signal from Appraisal proposing a change to a belief."""
    belief_id: str
    evidence_statement: str
    direction: str = Field(description="'support' or 'contradict'")
    evidence_strength: float = Field(ge=0.0, le=100.0, default=50.0)
    source_credibility: float = Field(ge=0.0, le=100.0, default=50.0)


class SituationUpdateSignal(BaseModel):
    """Signal from Appraisal proposing a new or updated situation fact."""
    statement: str
    epistemic_status: EpistemicStatus
    confidence: float = Field(ge=0.0, le=100.0)
    source: str = ""


class CommitmentSignal(BaseModel):
    """Signal indicating a commitment was made, fulfilled, or violated."""
    promise: str
    party: str = "negotiator"
    action: str = Field(description="'created', 'fulfilled', 'violated', 'withdrawn'")
    importance: float = Field(ge=0.0, le=100.0, default=50.0)
    violation_magnitude: float = Field(ge=0.0, le=100.0, default=0.0)
    subject_believed: bool = True
    subject_interpretation: str = ""


@dataclass
class BeliefMetadata:
    belief_id: str
    old_confidence: float
    new_confidence: float
    old_tension: float
    new_tension: float
    evidence_added: str
    cause: str


def update_belief(
    belief: Belief, 
    signal: BeliefUpdateSignal,
    existing_beliefs: dict[str, Belief]
) -> tuple[Belief, BeliefMetadata]:
    """
    Deterministically update a belief based on evidence strength, credibility, and resistance.
    """
    old_conf = belief.confidence
    old_tension = belief.tension
    
    # Calculate effective impact
    # High resistance means it's hard to change
    resistance_factor = (100.0 - belief.resistance) / 100.0
    
    # Credibility scales the evidence strength
    credibility_factor = signal.source_credibility / 100.0
    
    effective_shift = signal.evidence_strength * resistance_factor * credibility_factor * 0.5
    
    new_confidence = belief.confidence
    new_evidence = []
    new_contradicting = []
    
    if signal.direction == "support":
        new_confidence = min(100.0, old_conf + effective_shift)
        new_evidence = list(belief.supporting_evidence)
        new_contradicting = list(belief.contradicting_evidence)
        if signal.evidence_statement not in new_evidence:
            new_evidence.append(signal.evidence_statement)
            if len(new_evidence) > 5:
                new_evidence.pop(0)
    elif signal.direction == "contradict":
        new_confidence = max(0.0, old_conf - effective_shift)
        new_evidence = list(belief.supporting_evidence)
        new_contradicting = list(belief.contradicting_evidence)
        if signal.evidence_statement not in new_contradicting:
            new_contradicting.append(signal.evidence_statement)
            if len(new_contradicting) > 5:
                new_contradicting.pop(0)
                
    # Recalculate tension
    # Tension rises when confidence is moderate-high but contradicting evidence exists.
    # It also rises when confidence is exactly 50 (maximum uncertainty).
    uncertainty = 50.0 - abs(new_confidence - 50.0)  # max 50 when conf is 50
    evidence_conflict = min(len(new_evidence), len(new_contradicting)) * 10.0
    
    new_tension = min(100.0, uncertainty + evidence_conflict)
    
    updated = belief.model_copy(update={
        "confidence": new_confidence,
        "tension": new_tension,
        "supporting_evidence": new_evidence,
        "contradicting_evidence": new_contradicting,
    })
    
    meta = BeliefMetadata(
        belief_id=belief.id,
        old_confidence=old_conf,
        new_confidence=new_confidence,
        old_tension=old_tension,
        new_tension=new_tension,
        evidence_added=signal.evidence_statement,
        cause=f"{signal.direction} with strength {signal.evidence_strength} and credibility {signal.source_credibility}"
    )
    
    return updated, meta


def update_situation(
    situation: SituationModel, 
    signal: SituationUpdateSignal
) -> tuple[SituationModel, dict]:
    """
    Adds or updates a fact in the SituationModel.
    Unknowns remain unknowns, they are not collapsed into facts.
    """
    updated_knowledge = list(situation.knowledge)
    
    found = False
    for i, k in enumerate(updated_knowledge):
        # Very simple matching for Phase 3. 
        # In reality, might use semantic ID or exact string match
        if k.statement == signal.statement:
            updated_knowledge[i] = SituationKnowledge(
                statement=signal.statement,
                epistemic_status=signal.epistemic_status,
                confidence=signal.confidence,
                source=signal.source
            )
            found = True
            break
            
    if not found:
        updated_knowledge.append(
            SituationKnowledge(
                statement=signal.statement,
                epistemic_status=signal.epistemic_status,
                confidence=signal.confidence,
                source=signal.source
            )
        )
        
    updated_situation = situation.model_copy(update={"knowledge": updated_knowledge})
    return updated_situation, {"action": "updated_fact", "statement": signal.statement, "status": signal.epistemic_status}


def handle_commitment(
    commitments: list[Commitment], 
    signal: CommitmentSignal
) -> tuple[list[Commitment], dict]:
    """
    Process creation, fulfillment, or violation of a commitment.
    """
    new_commitments = list(commitments)
    impact_meta = {}
    
    if signal.action == "created":
        c = Commitment(
            party=signal.party,
            promise=signal.promise,
            subject_believed=signal.subject_believed,
            importance=signal.importance,
            status=CommitmentStatus.ACTIVE
        )
        new_commitments.append(c)
        impact_meta = {"created": True, "promise": c.promise}
        
    elif signal.action in ("fulfilled", "violated", "withdrawn"):
        found = False
        for i, c in enumerate(new_commitments):
            if c.promise == signal.promise and c.status == CommitmentStatus.ACTIVE:
                status_map = {
                    "fulfilled": CommitmentStatus.FULFILLED,
                    "violated": CommitmentStatus.VIOLATED,
                    "withdrawn": CommitmentStatus.WITHDRAWN
                }
                new_commitments[i] = c.model_copy(update={"status": status_map[signal.action]})
                found = True
                impact_meta = {
                    "action": signal.action, 
                    "promise": c.promise, 
                    "violation_magnitude": signal.violation_magnitude if signal.action == "violated" else 0.0
                }
                break
        if not found:
            impact_meta = {"action": "failed", "reason": "active commitment not found"}
            
    return new_commitments, impact_meta
