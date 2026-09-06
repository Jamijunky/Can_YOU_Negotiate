"""
Causal Human Simulator — All Pydantic Schemas.

Every schema here is a data structure. No behavioral logic lives in this file.
Behavioral logic belongs in future phase modules (appraisal, state_engine,
behavioral_policy, expression, speech).

Validation rules enforce value ranges and structural consistency.
"""

from __future__ import annotations

import enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# ENUMS
# ============================================================================

class EpistemicStatus(str, enum.Enum):
    """How confident the subject is about a piece of information."""
    OBSERVED = "observed"       # Directly perceived
    INFERRED = "inferred"       # Logically derived from observations
    BELIEVED = "believed"       # Accepted without direct evidence
    SUSPECTED = "suspected"     # Considered possible but uncertain
    UNKNOWN = "unknown"         # Acknowledged gap in knowledge


class EventType(str, enum.Enum):
    NEGOTIATOR_SPEECH = "NEGOTIATOR_SPEECH"
    SILENCE_STARTED = "SILENCE_STARTED"
    SILENCE_ONGOING = "SILENCE_ONGOING"
    SILENCE_ENDED = "SILENCE_ENDED"
    SUBJECT_ACTION = "SUBJECT_ACTION"
    ENVIRONMENTAL = "ENVIRONMENTAL"


class BeliefChangePathway(str, enum.Enum):
    """How this belief can be changed."""
    EMOTIONAL = "emotional"         # Changes when emotional state shifts
    EVIDENTIAL = "evidential"       # Changes through logical evidence
    RELATIONAL = "relational"       # Changes through relationship quality
    EXPERIENTIAL = "experiential"   # Changes only through direct experience


class CommitmentStatus(str, enum.Enum):
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    VIOLATED = "violated"
    WITHDRAWN = "withdrawn"


# ============================================================================
# HUMAN MODEL (Static — immutable during session)
# ============================================================================

class Identity(BaseModel):
    name: str
    age: int = Field(ge=16, le=80)
    occupation: str


class Personality(BaseModel):
    """
    Each trait is [0.0, 1.0]. Every trait has explicit downstream consequences.
    See field descriptions for behavioral references.
    """
    impulsivity: float = Field(ge=0.0, le=1.0,
        description="Controls gap between internal state and external action. "
                    "High: acts on raw emotion. Low: filters, delays, suppresses. "
                    "Referenced by: expression.speech_control, behavioral policy temperature.")
    dominance: float = Field(ge=0.0, le=1.0,
        description="Routes threat toward anger (high) or fear (low). "
                    "Referenced by: state transitions, behavioral scoring.")
    trust_tendency: float = Field(ge=0.0, le=1.0,
        description="Baseline willingness to believe statements. "
                    "Referenced by: appraisal credibility, belief resistance, relationship init.")
    emotional_volatility: float = Field(ge=0.0, le=1.0,
        description="Magnitude and speed of state changes. High: low inertia. "
                    "Referenced by: state transition inertia coefficient.")
    need_for_control: float = Field(ge=0.0, le=1.0,
        description="Sensitivity to loss of agency. "
                    "Referenced by: appraisal control_threat, trigger sensitivity.")
    pride: float = Field(ge=0.0, le=1.0,
        description="Sensitivity to disrespect/humiliation. Resistance to showing weakness. "
                    "Referenced by: appraisal respect, expression concealment, behavioral scoring.")
    guilt_tendency: float = Field(ge=0.0, le=1.0,
        description="Tendency toward self-blame when moral dimension is present. "
                    "Referenced by: state transitions guilt delta, behavioral scoring disclosure.")
    risk_tolerance: float = Field(ge=0.0, le=1.0,
        description="Willingness to take dangerous actions under pressure. "
                    "Referenced by: behavioral scoring escalation/bluffing, alternatives risk weighting.")


class Trigger(BaseModel):
    """
    A topic that causes heightened emotional response. Context-sensitive.
    """
    id: str
    topic: str
    sensitivity: float = Field(ge=0.0, le=1.0,
        description="Base sensitivity. Modified by current state at evaluation time.")
    affected_belief_ids: list[str] = Field(default_factory=list,
        description="Belief IDs that become salient when this trigger fires.")
    affected_goal_ids: list[str] = Field(default_factory=list,
        description="Goal IDs that become more urgent.")
    possible_emotional_effects: list[dict] = Field(default_factory=list,
        description="List of {emotion: str, weight: float}. Actual effect depends on "
                    "personality and current state.")
    possible_behaviors: list[str] = Field(default_factory=list,
        description="Actions that become more likely. Added as scoring bonuses.")
    exposure_effect: str = Field(default="sensitizing",
        description="'sensitizing' (each mention cuts deeper) or 'habituating' (gets tired of reacting). "
                    "Depends on personality and whether probing is perceived as deliberate.")


class CopingMechanisms(BaseModel):
    """Behavioral tendencies under specific emotional states. These are scoring bonuses, not guarantees."""
    fear_response: str = Field(
        description="Tendency when afraid: 'silence', 'aggression', 'compliance', "
                    "'rambling', 'control_seeking', 'denial'")
    anger_response: str = Field(
        description="Tendency when angry: 'cold_logic', 'explosive', 'sarcasm', "
                    "'withdrawal', 'demands', 'threats'")
    stress_response: str = Field(
        description="Tendency under sustained stress: 'precision', 'confusion', "
                    "'talking_more', 'talking_less', 'humor', 'repetition'")


class CommunicationStyle(BaseModel):
    """Controls the voice and phrasing of generated speech."""
    description: str = Field(
        description="Natural language description: 'Short, blunt sentences. Working-class vocabulary.'")
    style_anchors: list[str] = Field(default_factory=list, max_length=3,
        description="2-3 example sentences in the character's voice. "
                    "Style references, NOT reusable dialogue.")
    directness: float = Field(ge=0.0, le=1.0, description="Low = indirect/evasive. High = blunt.")
    verbosity: float = Field(ge=0.0, le=1.0, description="Low = terse. High = talkative.")
    formality: float = Field(ge=0.0, le=1.0, description="Low = slang. High = formal.")


class Goals(BaseModel):
    primary: str
    secondary: str = ""
    immediate: str = ""
    hidden: str = ""


class HumanModel(BaseModel):
    """
    The static psychological blueprint. Immutable during a session.
    Defines how the individual appraises events, regulates emotion,
    copes with stress, and communicates.

    AUTHORITY: This is the authoritative source for personality.
    The personality_narrative is a DERIVED representation for LLM consumption.
    """
    identity: Identity
    life_history: list[str] = Field(default_factory=list,
        description="Formative experiences shaping appraisal biases.")
    personality: Personality
    personality_narrative: str = Field(default="",
        description="Natural-language rendering of traits + life_history. "
                    "Generated once at session start. Used only as LLM context. "
                    "DERIVED, not authoritative.")
    values: list[str] = Field(default_factory=list,
        description="What the subject protects at all costs.")
    goals: Goals
    conflicting_goals: list[str] = Field(default_factory=list)
    fears: list[str] = Field(default_factory=list)
    vulnerabilities: list[str] = Field(default_factory=list)
    triggers: list[Trigger] = Field(default_factory=list)
    coping: CopingMechanisms
    communication_style: CommunicationStyle
    secrets: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_trigger_references(self) -> "HumanModel":
        """Ensure trigger affected_belief_ids and affected_goal_ids exist in context.
        (Full validation requires Beliefs and Goals to be instantiated;
        this validator checks structural completeness only.)"""
        trigger_ids = [t.id for t in self.triggers]
        if len(trigger_ids) != len(set(trigger_ids)):
            raise ValueError("Duplicate trigger IDs found")
        return self


# ============================================================================
# PSYCHOLOGICAL STATE (Mutable — updated each turn via deterministic math)
# ============================================================================

class PsychologicalState(BaseModel):
    """
    Continuous internal emotional variables. Have inertia and momentum.
    Values are [0, 100]. Cross-variable interactions are computed in
    the state engine (Phase 2), not here.
    """
    fear: float = Field(default=50.0, ge=0.0, le=100.0)
    anger: float = Field(default=20.0, ge=0.0, le=100.0)
    stress: float = Field(default=60.0, ge=0.0, le=100.0)
    desperation: float = Field(default=30.0, ge=0.0, le=100.0,
        description="Partially derived from alternatives evaluation.")
    guilt: float = Field(default=10.0, ge=0.0, le=100.0)
    hope: float = Field(default=30.0, ge=0.0, le=100.0)
    sense_of_control: float = Field(default=40.0, ge=0.0, le=100.0)

    # Expression mask accumulator
    emotional_pressure: float = Field(default=0.0, ge=0.0,
        description="Accumulates when concealed intensity exceeds expressed intensity. "
                    "Resets on mask break.")

    @field_validator("*", mode="before")
    @classmethod
    def clamp_values(cls, v, info):
        if isinstance(v, (int, float)):
            if info.field_name == "emotional_pressure":
                return max(0.0, float(v))
            return max(0.0, min(100.0, float(v)))
        return v


# ============================================================================
# BELIEFS (Mutable — updated deterministically from appraisal)
# ============================================================================

class Belief(BaseModel):
    """
    An evaluative judgment. Distinct from situation facts.
    Supports non-monotonic change and coexisting contradictions.

    Multiple beliefs on the same topic can coexist with different strengths.
    The subject can simultaneously hold "I trust him" and "He may be lying."
    """
    id: str
    statement: str
    confidence: float = Field(ge=0.0, le=100.0,
        description="Current strength of belief.")
    importance: float = Field(ge=0.0, le=100.0,
        description="How much this belief matters to goals/values.")
    resistance: float = Field(ge=0.0, le=100.0,
        description="How difficult to change through evidence alone.")
    provenance: str = Field(
        description="Where the belief originated: 'life_experience', 'turn_3', 'assumption'")
    change_pathway: BeliefChangePathway = Field(
        description="How this belief can be changed: emotional, evidential, relational, experiential.")
    supporting_evidence: list[str] = Field(default_factory=list, max_length=5)
    contradicting_evidence: list[str] = Field(default_factory=list, max_length=5)
    tension: float = Field(default=0.0, ge=0.0, le=100.0,
        description="Internal contradiction level. High tension = subject is uncertain, "
                    "may flip-flop, express ambivalence. "
                    "Rises when contradicting evidence is strong but confidence remains high.")


# ============================================================================
# SITUATION MODEL (Mutable — the subject's perceived world)
# ============================================================================

class SituationKnowledge(BaseModel):
    """A piece of situational information with epistemic status."""
    statement: str
    epistemic_status: EpistemicStatus
    confidence: float = Field(ge=0.0, le=100.0)
    source: str = ""


class PerceivedThreat(BaseModel):
    source: str
    severity: float = Field(ge=0.0, le=100.0)
    imminence: float = Field(ge=0.0, le=100.0)
    epistemic_status: EpistemicStatus = EpistemicStatus.INFERRED


class ImportantPerson(BaseModel):
    name: str
    relation: str
    status: str
    epistemic_status: EpistemicStatus = EpistemicStatus.BELIEVED
    emotional_significance: float = Field(ge=0.0, le=100.0)


class PerceivedConsequence(BaseModel):
    scenario: str
    believed_outcome: str
    confidence: float = Field(ge=0.0, le=100.0)


class SituationModel(BaseModel):
    """
    The subject's internal model of the external world.
    This model can be WRONG. It represents perceived reality.
    Every piece of information carries an epistemic status.
    """
    knowledge: list[SituationKnowledge] = Field(default_factory=list)
    perceived_threats: list[PerceivedThreat] = Field(default_factory=list)
    perceived_resources: list[str] = Field(default_factory=list)
    important_people: list[ImportantPerson] = Field(default_factory=list)
    perceived_constraints: list[str] = Field(default_factory=list)
    perceived_consequences: list[PerceivedConsequence] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


# ============================================================================
# RELATIONSHIP STATE (Mutable — tracks interpersonal dynamic)
# ============================================================================

class NegotiatorPattern(BaseModel):
    pattern: str
    topic: str = ""
    count: int = Field(default=0, ge=0)
    noticed: bool = False


class RelationshipState(BaseModel):
    """
    Interpersonal dynamic with the negotiator.
    Includes trajectory (rate of change) and foundation depth.

    trust=70 rising is behaviorally different from trust=70 falling.
    trust_foundation determines resilience to trust destruction.
    """
    trust: float = Field(default=30.0, ge=0.0, le=100.0)
    trust_trajectory: float = Field(default=0.0,
        description="EMA of recent trust deltas. Positive = rising.")
    trust_foundation: float = Field(default=0.0, ge=0.0, le=100.0,
        description="How deeply rooted. Increases slowly with gradual trust. "
                    "High-foundation trust resists single negative events.")

    respect: float = Field(default=30.0, ge=0.0, le=100.0)
    respect_trajectory: float = Field(default=0.0)

    perceived_honesty: float = Field(default=40.0, ge=0.0, le=100.0,
        description="Per-statement assessment. Can diverge from cumulative trust.")
    perceived_competence: float = Field(default=40.0, ge=0.0, le=100.0)
    resentment: float = Field(default=0.0, ge=0.0, le=100.0,
        description="Accumulated frustration at negotiator. Decays slowly.")
    dependency: float = Field(default=10.0, ge=0.0, le=100.0)
    perceived_threat: float = Field(default=20.0, ge=0.0, le=100.0)
    rapport: float = Field(default=10.0, ge=0.0, le=100.0,
        description="Sense of mutual human connection. Distinct from trust.")

    negotiator_patterns: list[NegotiatorPattern] = Field(default_factory=list)


# ============================================================================
# GOALS, CONFLICTS, AND ALTERNATIVES
# ============================================================================

class Goal(BaseModel):
    id: str
    description: str
    priority: float = Field(ge=0.0, le=100.0)
    achievability: float = Field(ge=0.0, le=100.0,
        description="Perceived, from alternatives evaluation.")
    urgency: float = Field(ge=0.0, le=100.0)


class GoalConflict(BaseModel):
    goal_a_id: str
    goal_b_id: str
    tension: float = Field(ge=0.0, le=100.0,
        description="How actively these goals conflict right now.")


class GoalState(BaseModel):
    """
    Tracks goal priorities, active conflicts, and ambivalence.
    Ambivalence is computed from active conflicts and belief tensions.
    """
    goals: list[Goal] = Field(default_factory=list)
    active_conflicts: list[GoalConflict] = Field(default_factory=list)

    ambivalence_level: float = Field(default=0.0, ge=0.0, le=100.0,
        description="Computed from active_conflicts. High = hesitation, reversal, bargaining.")
    primary_pull: str = Field(default="",
        description="Which goal is slightly winning.")
    secondary_pull: str = Field(default="",
        description="Which goal is pulling against.")


class Alternative(BaseModel):
    """A perceived option available to the subject."""
    id: str
    description: str
    perceived_probability: float = Field(ge=0.0, le=100.0)
    perceived_risk: float = Field(ge=0.0, le=100.0)
    perceived_reward: float = Field(ge=0.0, le=100.0)
    perceived_cost: float = Field(ge=0.0, le=100.0)
    conflicts_with_values: bool = False
    requires_trust: bool = False
    epistemic_status: EpistemicStatus = EpistemicStatus.BELIEVED


class AlternativesModel(BaseModel):
    options: list[Alternative] = Field(default_factory=list)
    best_option_utility: float = Field(default=0.0,
        description="max(probability * reward - risk * cost) across options.")
    desperation_contribution: float = Field(default=50.0, ge=0.0, le=100.0,
        description="100 - best_option_utility, clamped.")

    @model_validator(mode="after")
    def compute_derived(self) -> "AlternativesModel":
        if self.options:
            utilities = []
            for opt in self.options:
                u = (opt.perceived_probability / 100) * (opt.perceived_reward / 100) * 100
                r = (opt.perceived_risk / 100) * (opt.perceived_cost / 100) * 100
                utilities.append(max(0, u - r))
            self.best_option_utility = max(utilities) if utilities else 0.0
            self.desperation_contribution = max(0.0, min(100.0, 100.0 - self.best_option_utility))
        return self


# ============================================================================
# EVENTS
# ============================================================================

class Event(BaseModel):
    """First-class representation of everything the subject perceives."""
    type: EventType
    timestamp_ms: float = 0.0
    session_elapsed_ms: float = 0.0

    # NEGOTIATOR_SPEECH fields
    content: str = ""
    speech_duration_ms: float = 0.0
    was_interrupted: bool = False

    # SILENCE fields
    silence_duration_ms: float = 0.0
    preceding_context: str = ""

    # SUBJECT_ACTION fields (for self-effect)
    action_taken: str = ""
    action_target: str = ""
    action_intensity: float = Field(default=0.0, ge=0.0, le=1.0)
    disclosed_secret: Optional[str] = None
    contradicted_self: bool = False

    # ENVIRONMENTAL
    environmental_description: str = ""


# ============================================================================
# MEMORY (V1 — simple, functional, preserves meaning)
# ============================================================================

class EpisodicMemory(BaseModel):
    """An emotionally or goal-significant event, stored with consequences."""
    event_summary: str
    subject_reaction: str
    subsequent_impact: str = ""
    emotional_valence: str = Field(default="neutral",
        description="'positive', 'negative', 'neutral'")
    salience: float = Field(ge=0.0, le=100.0)
    turn_number: int = 0
    tags: list[str] = Field(default_factory=list,
        description="Goal IDs, trigger IDs, belief IDs for retrieval.")
    detail_level: str = Field(default="precise",
        description="'precise', 'approximate', 'vague'. Affects recall fidelity.")


class SemanticFact(BaseModel):
    fact: str
    confidence: float = Field(default=100.0, ge=0.0, le=100.0)
    source: str = ""


class Commitment(BaseModel):
    party: str = Field(description="'negotiator' or 'subject'")
    promise: str
    subject_believed: bool = True
    importance: float = Field(ge=0.0, le=100.0)
    status: CommitmentStatus = CommitmentStatus.ACTIVE


class Contradiction(BaseModel):
    statement_a: str
    turn_a: int
    statement_b: str
    turn_b: int
    noticed_by_subject: bool = False
    subject_interpretation: str = ""
    impact: str = ""


class MemoryStore(BaseModel):
    """V1 memory: functional, preserves meaning. Not over-engineered."""
    episodic: list[EpisodicMemory] = Field(default_factory=list)
    semantic: list[SemanticFact] = Field(default_factory=list)
    commitments: list[Commitment] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)


# ============================================================================


# ============================================================================
# AUTHORITATIVE WORLD STATE (Objective Reality)
# ============================================================================

class Resource(BaseModel):
    id: str
    name: str
    exists: bool = True
    available: bool = True
    holder: str = "system" # 'negotiator', 'subject', 'system'

class Capability(BaseModel):
    id: str
    name: str
    enabled: bool = False

class WorldState(BaseModel):
    resources: dict[str, Resource] = Field(default_factory=dict)
    capabilities: dict[str, Capability] = Field(default_factory=dict)
    constraints: dict[str, bool] = Field(default_factory=dict)

class WorldUpdateSignal(BaseModel):
    action: str = Field(description="'transfer', 'consume', 'enable', 'disable', 'claim'")
    object_id: str
    actor: str = Field(description="'negotiator' or 'subject'")
    target: Optional[str] = None
    validity: str = Field(description="'UNKNOWN', 'CLAIMED'", default="UNKNOWN")


# APPRAISAL (Output of the appraisal LLM — proposals, not authoritative)
# ============================================================================

class IntentAssessment(BaseModel):
    """Ranked interpretation of negotiator's intent, with confidence."""
    intent: str
    confidence: float = Field(ge=0.0, le=100.0)


class BeliefImpact(BaseModel):
    belief_id: str
    evidence: str
    direction: str = Field(description="'support' or 'contradict'")


class SituationUpdate(BaseModel):
    statement: str
    epistemic_status: EpistemicStatus
    confidence: float = Field(ge=0.0, le=100.0)


class Appraisal(BaseModel):
    """
    The subject's subjective interpretation of an event.
    Produced by the appraisal LLM. These are PROPOSALS.
    The deterministic state engine decides what to do with them.
    """
    perceived_intent: list[IntentAssessment] = Field(
        default_factory=list, min_length=1,
        description="Ranked list of interpretations with confidence. Primary drives updates.")
    credibility: float = Field(ge=0.0, le=100.0)
    threat_delta: float = Field(ge=-50.0, le=50.0)
    control_delta: float = Field(ge=-50.0, le=50.0)
    respect_delta: float = Field(ge=-50.0, le=50.0)
    emotional_significance: float = Field(ge=0.0, le=100.0)
    goal_relevance: Optional[str] = None
    trigger_activation: Optional[str] = None
    belief_impacts: list[BeliefImpact] = Field(default_factory=list)
    situation_updates: list[SituationUpdate] = Field(default_factory=list)
    commitment_detected: Optional[Commitment] = None
    contradiction_detected: Optional[Contradiction] = None


# ============================================================================
# BEHAVIORAL POLICY
# ============================================================================

class ConsequencePrediction(BaseModel):
    """Expected outcome of taking an action. Based on beliefs, not reality."""
    expected_negotiator_response: str
    expected_immediate_goal_effect: str
    expected_longterm_goal_effect: str
    risk: float = Field(ge=0.0, le=100.0)
    relationship_consequence: str
    reversibility: str = Field(description="'reversible', 'partially_reversible', 'irreversible'")


class BehavioralCandidate(BaseModel):
    """A scored candidate action."""
    action: str = Field(
        description="One of: answer, refuse, evade, bargain, lie, partially_disclose, "
                    "fully_disclose, question, challenge, accuse, seek_reassurance, "
                    "change_topic, withdraw, remain_silent, correct, test, threaten, "
                    "backtrack, admit, deny, demand, surrender, escalate")
    target: str = ""
    intensity: float = Field(ge=0.0, le=1.0)
    information_strategy: str = Field(default="concealment",
        description="'full_disclosure', 'partial_disclosure', 'concealment', 'deception'")
    score: float = 0.0
    consequence_prediction: Optional[ConsequencePrediction] = None
    rationale: str = Field(default="",
        description="For debugging/observability only. Never exposed to user or dialogue LLM.")


class BehavioralDecision(BaseModel):
    candidates: list[BehavioralCandidate] = Field(default_factory=list)
    selected: Optional[BehavioralCandidate] = None
    selection_method: str = Field(default="highest_score",
        description="'highest_score' or 'stochastic_near_top'")
    hesitation: bool = Field(default=False,
        description="True when ambivalence is high and top candidates serve conflicting goals.")


class StrategyRecord(BaseModel):
    """Record of a past behavioral strategy and its perceived outcome."""
    action: str
    turn_number: int
    perceived_outcome: str = Field(
        description="'effective', 'ineffective', 'counterproductive', 'unknown'")


class StrategyHistory(BaseModel):
    """Tracks what strategies the subject has tried and whether they worked."""
    records: list[StrategyRecord] = Field(default_factory=list, max_length=20)

    def get_effectiveness(self, action: str) -> Optional[str]:
        """Returns the most recent perceived outcome for an action type."""
        for r in reversed(self.records):
            if r.action == action:
                return r.perceived_outcome
        return None

    def action_count(self, action: str) -> int:
        return sum(1 for r in self.records if r.action == action)


# ============================================================================
# EXPRESSION (Continuous underlying variables with derived labels)
# ============================================================================

class Expression(BaseModel):
    """
    Mediates between internal state and external presentation.
    Underlying representation is continuous floats.
    Derived labels are for human readability and LLM narrative rendering.
    """
    # Underlying continuous variables
    speech_control: float = Field(default=0.5, ge=0.0, le=1.0,
        description="How much the subject is suppressing internal state. "
                    "1.0 = fully controlled. 0.0 = raw unfiltered.")
    hesitation_tendency: float = Field(default=0.3, ge=0.0, le=1.0,
        description="Likelihood of pauses, false starts, unfinished thoughts.")
    verbal_energy: float = Field(default=0.5, ge=0.0, le=1.0,
        description="0.0 = withdrawn/quiet. 1.0 = loud/fast.")
    emotional_leakage: float = Field(default=0.2, ge=0.0, le=1.0,
        description="How much concealed emotion breaks through.")
    directness: float = Field(default=0.5, ge=0.0, le=1.0,
        description="How directly the subject addresses the topic.")
    self_correction_tendency: float = Field(default=0.1, ge=0.0, le=1.0,
        description="How often the subject starts saying something then takes it back.")

    # Concealment state
    concealed_states: list[str] = Field(default_factory=list)
    leaked_states: list[str] = Field(default_factory=list)

    # Ambivalence flag
    hesitation: bool = False

    # Dynamic word range (derived from verbal_energy)
    min_words: int = Field(default=5, ge=1)
    max_words: int = Field(default=35, ge=1)

    @model_validator(mode="after")
    def derive_word_range(self) -> "Expression":
        e = self.verbal_energy
        if e < 0.2:
            self.min_words, self.max_words = 1, 10
        elif e < 0.4:
            self.min_words, self.max_words = 5, 20
        elif e < 0.6:
            self.min_words, self.max_words = 10, 35
        elif e < 0.8:
            self.min_words, self.max_words = 20, 50
        else:
            self.min_words, self.max_words = 30, 70
        return self

    @property
    def derived_verbal_style(self) -> str:
        """Human-readable label derived from continuous variables."""
        if self.speech_control > 0.7 and self.verbal_energy < 0.3:
            return "controlled"
        if self.speech_control < 0.3 and self.verbal_energy > 0.7:
            return "explosive"
        if self.speech_control > 0.6 and self.verbal_energy < 0.4:
            return "cold"
        if self.hesitation_tendency > 0.6:
            return "hesitant"
        if self.verbal_energy > 0.7 and self.directness < 0.3:
            return "rambling"
        if self.directness > 0.7 and self.verbal_energy < 0.5:
            return "precise"
        return "measured"

    @property
    def derived_pacing(self) -> str:
        if self.verbal_energy > 0.7:
            return "fast"
        if self.verbal_energy < 0.3:
            return "slow"
        if abs(self.verbal_energy - 0.5) < 0.15 and self.hesitation_tendency > 0.5:
            return "erratic"
        return "moderate"


# ============================================================================
# OBSERVABILITY / CAUSAL TRACE
# ============================================================================

class CausalTrace(BaseModel):
    """Full causal trace for a single turn. For debugging only."""
    turn_number: int = 0
    event_type: str = ""
    event_content: str = ""

    appraisal_intent: list[IntentAssessment] = Field(default_factory=list)
    appraisal_credibility: float = 0.0
    appraisal_threat_delta: float = 0.0
    appraisal_control_delta: float = 0.0
    appraisal_respect_delta: float = 0.0
    trigger_activated: Optional[str] = None
    beliefs_affected: list[str] = Field(default_factory=list)

    state_before: Optional[PsychologicalState] = None
    state_after: Optional[PsychologicalState] = None
    state_deltas: dict[str, float] = Field(default_factory=dict)

    relationship_before_trust: float = 0.0
    relationship_after_trust: float = 0.0
    relationship_before_respect: float = 0.0
    relationship_after_respect: float = 0.0

    belief_changes: list[dict] = Field(default_factory=list)
    ambivalence: float = 0.0
    alternatives_best_utility: float = 0.0

    behavioral_candidates_top5: list[dict] = Field(default_factory=list)
    selected_action: str = ""
    expression_summary: dict = Field(default_factory=dict)
    mask_break: bool = False

    memory_stored: list[str] = Field(default_factory=list)
    memory_retrieved: list[str] = Field(default_factory=list)
    self_effect: dict[str, float] = Field(default_factory=dict)

    dialogue_word_count: int = 0
    latency_appraisal_ms: float = 0.0
    latency_state_ms: float = 0.0
    latency_dialogue_ttft_ms: float = 0.0
    latency_rime_ttfa_ms: float = 0.0
    latency_total_ttfa_ms: float = 0.0
