"""
Cognition Engine for the Causal Human Simulator.

ARCHITECTURAL INVARIANTS:
1. Only one cognitive transaction may modify the subject's authoritative state at a time.
   If a new negotiator event arrives during processing, it is QUEUED, not processed concurrently.
2. The appraisal LLM proposes interpretations. All state updates are deterministic.
   The speech LLM renders decisions. Neither LLM owns state.
3. Turn lifecycle commit order:
   T0 snapshot → T1 event → T2 appraisal → T3 deterministic updates →
   T4 memory retrieval → T5 alternatives/goals → T6 behavioral decision →
   T7 expression → T8 self-effect → T9 STATE COMMIT → T10 speech generation →
   T11 memory consolidation (async) → T12 observability (async)
4. Speech generation reads behavioral decision + expression, never raw state.
"""

from cognition.schemas import (
    # Identity & Personality
    Identity,
    Personality,
    Trigger,
    CopingMechanisms,
    CommunicationStyle,
    Goals,
    HumanModel,
    # State
    PsychologicalState,
    # Beliefs
    Belief,
    EpistemicStatus,
    # Situation
    SituationKnowledge,
    PerceivedThreat,
    PerceivedConsequence,
    ImportantPerson,
    SituationModel,
    # Relationship
    RelationshipState,
    # Goals & Alternatives
    Goal,
    GoalConflict,
    GoalState,
    Alternative,
    AlternativesModel,
    # Events
    EventType,
    Event,
    # Memory
    EpisodicMemory,
    SemanticFact,
    Commitment,
    Contradiction,
    MemoryStore,
    # Appraisal
    IntentAssessment,
    BeliefImpact,
    SituationUpdate,
    Appraisal,
    # Behavior
    ConsequencePrediction,
    BehavioralCandidate,
    BehavioralDecision,
    StrategyRecord,
    StrategyHistory,
    # Expression
    Expression,
    # Observability
    CausalTrace,
)
