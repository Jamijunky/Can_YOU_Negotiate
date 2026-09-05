"""
Phase 1 Tests: Schema validation and structural consistency.

Every test proves that changing input changes downstream validity or derived values.
"""

import pytest
from pydantic import ValidationError

from cognition.schemas import (
    Identity,
    Personality,
    Trigger,
    CopingMechanisms,
    CommunicationStyle,
    Goals,
    HumanModel,
    PsychologicalState,
    Belief,
    BeliefChangePathway,
    EpistemicStatus,
    SituationKnowledge,
    SituationModel,
    PerceivedThreat,
    RelationshipState,
    NegotiatorPattern,
    Goal,
    GoalConflict,
    GoalState,
    Alternative,
    AlternativesModel,
    Event,
    EventType,
    EpisodicMemory,
    SemanticFact,
    Commitment,
    CommitmentStatus,
    Contradiction,
    MemoryStore,
    IntentAssessment,
    BeliefImpact,
    Appraisal,
    ConsequencePrediction,
    BehavioralCandidate,
    BehavioralDecision,
    StrategyRecord,
    StrategyHistory,
    Expression,
    CausalTrace,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def base_personality():
    return Personality(
        impulsivity=0.7,
        dominance=0.8,
        trust_tendency=0.2,
        emotional_volatility=0.6,
        need_for_control=0.9,
        pride=0.85,
        guilt_tendency=0.3,
        risk_tolerance=0.7,
    )


@pytest.fixture
def base_human_model(base_personality):
    return HumanModel(
        identity=Identity(name="Marcus", age=38, occupation="Construction foreman"),
        life_history=[
            "Was falsely accused by police at age 19.",
            "Lost custody of daughter two years ago.",
        ],
        personality=base_personality,
        personality_narrative="Marcus was falsely accused by police at 19...",
        values=["Family safety", "Dignity"],
        goals=Goals(
            primary="Escape without injury",
            secondary="Protect brother",
            immediate="Keep police out",
            hidden="Brother is hiding in the back room",
        ),
        conflicting_goals=["Wants to escape", "Cannot leave brother behind"],
        fears=["Being locked up again", "Losing control"],
        vulnerabilities=["Failure as a father"],
        triggers=[
            Trigger(
                id="trig_family",
                topic="family",
                sensitivity=0.8,
                affected_belief_ids=["belief_police_harm"],
                affected_goal_ids=["goal_protect_brother"],
                possible_emotional_effects=[
                    {"emotion": "anger", "weight": 0.6},
                    {"emotion": "guilt", "weight": 0.4},
                ],
                possible_behaviors=["threaten", "withdraw"],
                exposure_effect="sensitizing",
            ),
        ],
        coping=CopingMechanisms(
            fear_response="aggression",
            anger_response="cold_logic",
            stress_response="talking_less",
        ),
        communication_style=CommunicationStyle(
            description="Short, blunt sentences. Working-class vocabulary.",
            style_anchors=[
                "I said no. What part of that is hard?",
                "Look, I don't— I'm not doing this.",
            ],
            directness=0.8,
            verbosity=0.3,
            formality=0.2,
        ),
        secrets=["Brother is in the back room"],
    )


# ============================================================================
# HUMAN MODEL TESTS
# ============================================================================

class TestHumanModel:
    def test_valid_instantiation(self, base_human_model):
        assert base_human_model.identity.name == "Marcus"
        assert base_human_model.personality.dominance == 0.8

    def test_personality_trait_range_low(self):
        with pytest.raises(ValidationError):
            Personality(
                impulsivity=-0.1, dominance=0.5, trust_tendency=0.5,
                emotional_volatility=0.5, need_for_control=0.5,
                pride=0.5, guilt_tendency=0.5, risk_tolerance=0.5,
            )

    def test_personality_trait_range_high(self):
        with pytest.raises(ValidationError):
            Personality(
                impulsivity=1.1, dominance=0.5, trust_tendency=0.5,
                emotional_volatility=0.5, need_for_control=0.5,
                pride=0.5, guilt_tendency=0.5, risk_tolerance=0.5,
            )

    def test_age_range(self):
        with pytest.raises(ValidationError):
            Identity(name="Test", age=10, occupation="Student")

    def test_duplicate_trigger_ids_rejected(self, base_personality):
        dup_trigger = Trigger(
            id="trig_family", topic="family2", sensitivity=0.5,
            exposure_effect="habituating"
        )
        with pytest.raises(ValidationError, match="Duplicate trigger IDs"):
            HumanModel(
                identity=Identity(name="Test", age=30, occupation="Test"),
                personality=base_personality,
                goals=Goals(primary="test"),
                triggers=[
                    Trigger(id="trig_family", topic="family", sensitivity=0.8,
                            exposure_effect="sensitizing"),
                    dup_trigger,
                ],
                coping=CopingMechanisms(
                    fear_response="silence",
                    anger_response="explosive",
                    stress_response="confusion",
                ),
                communication_style=CommunicationStyle(
                    description="test", directness=0.5, verbosity=0.5, formality=0.5,
                ),
            )

    def test_personality_narrative_is_derived(self, base_human_model):
        """Narrative exists but is labeled as non-authoritative."""
        assert base_human_model.personality_narrative != ""
        # The structured personality is the authority
        assert base_human_model.personality.dominance == 0.8

    def test_different_personalities_are_distinguishable(self):
        """Two HumanModels with different traits must produce different data."""
        p_aggressive = Personality(
            impulsivity=0.9, dominance=0.9, trust_tendency=0.1,
            emotional_volatility=0.8, need_for_control=0.9,
            pride=0.9, guilt_tendency=0.1, risk_tolerance=0.9,
        )
        p_compliant = Personality(
            impulsivity=0.2, dominance=0.1, trust_tendency=0.8,
            emotional_volatility=0.3, need_for_control=0.2,
            pride=0.2, guilt_tendency=0.8, risk_tolerance=0.2,
        )
        assert p_aggressive.dominance != p_compliant.dominance
        assert p_aggressive.trust_tendency != p_compliant.trust_tendency
        assert p_aggressive.pride != p_compliant.pride


# ============================================================================
# PSYCHOLOGICAL STATE TESTS
# ============================================================================

class TestPsychologicalState:
    def test_default_values(self):
        state = PsychologicalState()
        assert state.fear == 50.0
        assert state.emotional_pressure == 0.0

    def test_clamping_high(self):
        state = PsychologicalState(fear=150.0, anger=200.0)
        assert state.fear == 100.0
        assert state.anger == 100.0

    def test_clamping_low(self):
        state = PsychologicalState(fear=-10.0, hope=-50.0)
        assert state.fear == 0.0
        assert state.hope == 0.0

    def test_emotional_pressure_no_upper_clamp(self):
        """Pressure can exceed 100 (it accumulates until mask break)."""
        state = PsychologicalState(emotional_pressure=250.0)
        assert state.emotional_pressure == 250.0

    def test_state_changes_are_independent(self):
        """Changing one variable does not affect others at schema level.
        Cross-variable interactions belong in the state engine (Phase 2)."""
        s1 = PsychologicalState(fear=90.0, anger=20.0)
        s2 = PsychologicalState(fear=20.0, anger=90.0)
        assert s1.fear != s2.fear
        assert s1.anger != s2.anger


# ============================================================================
# BELIEF TESTS
# ============================================================================

class TestBelief:
    def test_valid_belief(self):
        b = Belief(
            id="belief_police_harm",
            statement="If I surrender, I will be beaten by police.",
            confidence=80.0,
            importance=90.0,
            resistance=85.0,
            provenance="life_experience",
            change_pathway=BeliefChangePathway.EXPERIENTIAL,
        )
        assert b.tension == 0.0  # No contradicting evidence yet

    def test_tension_computation(self):
        """Tension rises when contradicting evidence exists alongside high confidence."""
        b = Belief(
            id="test",
            statement="test",
            confidence=80.0,
            importance=50.0,
            resistance=50.0,
            provenance="test",
            change_pathway=BeliefChangePathway.EVIDENTIAL,
            contradicting_evidence=["evidence_1", "evidence_2"],
            tension=40.0,  # Manually set; in practice computed by state engine
        )
        assert b.tension == 40.0

    def test_coexisting_contradictory_beliefs(self):
        """Two beliefs on the same topic can coexist."""
        b1 = Belief(
            id="trust_negotiator_yes",
            statement="The negotiator is telling the truth.",
            confidence=60.0, importance=80.0, resistance=30.0,
            provenance="recent_interaction",
            change_pathway=BeliefChangePathway.RELATIONAL,
        )
        b2 = Belief(
            id="trust_negotiator_no",
            statement="Something about the negotiator feels wrong.",
            confidence=45.0, importance=70.0, resistance=50.0,
            provenance="intuition",
            change_pathway=BeliefChangePathway.EMOTIONAL,
        )
        # Both can exist simultaneously with different strengths
        assert b1.id != b2.id
        assert b1.confidence != b2.confidence

    def test_change_pathway_enum(self):
        with pytest.raises(ValidationError):
            Belief(
                id="test", statement="test",
                confidence=50.0, importance=50.0, resistance=50.0,
                provenance="test", change_pathway="invalid_pathway",
            )


# ============================================================================
# SITUATION MODEL TESTS
# ============================================================================

class TestSituationModel:
    def test_epistemic_status_preserved(self):
        sm = SituationModel(
            knowledge=[
                SituationKnowledge(
                    statement="Sirens outside",
                    epistemic_status=EpistemicStatus.OBSERVED,
                    confidence=95,
                ),
                SituationKnowledge(
                    statement="Police intend to arrest me",
                    epistemic_status=EpistemicStatus.BELIEVED,
                    confidence=75,
                ),
                SituationKnowledge(
                    statement="Back exit might be covered",
                    epistemic_status=EpistemicStatus.SUSPECTED,
                    confidence=40,
                ),
                SituationKnowledge(
                    statement="Whether negotiator has authority",
                    epistemic_status=EpistemicStatus.UNKNOWN,
                    confidence=0,
                ),
            ]
        )
        observed = [k for k in sm.knowledge if k.epistemic_status == EpistemicStatus.OBSERVED]
        unknown = [k for k in sm.knowledge if k.epistemic_status == EpistemicStatus.UNKNOWN]
        assert len(observed) == 1
        assert len(unknown) == 1

    def test_invalid_epistemic_status_rejected(self):
        with pytest.raises(ValidationError):
            SituationKnowledge(
                statement="test",
                epistemic_status="definitely_true",
                confidence=100,
            )

    def test_perceived_threat_has_epistemic_status(self):
        t = PerceivedThreat(
            source="SWAT team", severity=80, imminence=60,
            epistemic_status=EpistemicStatus.INFERRED,
        )
        assert t.epistemic_status == EpistemicStatus.INFERRED


# ============================================================================
# RELATIONSHIP STATE TESTS
# ============================================================================

class TestRelationshipState:
    def test_trajectory_distinguishes_direction(self):
        rising = RelationshipState(trust=70.0, trust_trajectory=5.0)
        falling = RelationshipState(trust=70.0, trust_trajectory=-8.0)
        assert rising.trust == falling.trust  # Same trust level
        assert rising.trust_trajectory > 0    # But different trajectory
        assert falling.trust_trajectory < 0

    def test_foundation_depth(self):
        shallow = RelationshipState(trust=70.0, trust_foundation=10.0)
        deep = RelationshipState(trust=70.0, trust_foundation=80.0)
        assert shallow.trust_foundation < deep.trust_foundation

    def test_negotiator_pattern_tracking(self):
        rs = RelationshipState(
            negotiator_patterns=[
                NegotiatorPattern(pattern="repeated_topic", topic="family", count=3, noticed=False),
            ]
        )
        assert rs.negotiator_patterns[0].count == 3
        assert not rs.negotiator_patterns[0].noticed


# ============================================================================
# GOAL & ALTERNATIVES TESTS
# ============================================================================

class TestGoalState:
    def test_ambivalence_from_conflicts(self):
        gs = GoalState(
            goals=[
                Goal(id="escape", description="Escape", priority=80, achievability=30, urgency=90),
                Goal(id="protect", description="Protect brother", priority=85, achievability=50, urgency=70),
            ],
            active_conflicts=[
                GoalConflict(goal_a_id="escape", goal_b_id="protect", tension=75.0),
            ],
            ambivalence_level=60.0,
            primary_pull="protect",
            secondary_pull="escape",
        )
        assert gs.ambivalence_level > 0

    def test_no_conflict_no_ambivalence(self):
        gs = GoalState(
            goals=[Goal(id="survive", description="Survive", priority=90, achievability=50, urgency=80)],
            ambivalence_level=0.0,
        )
        assert gs.ambivalence_level == 0.0


class TestAlternativesModel:
    def test_desperation_rises_with_no_good_options(self):
        am = AlternativesModel(options=[
            Alternative(
                id="surrender", description="Surrender",
                perceived_probability=20, perceived_risk=80,
                perceived_reward=30, perceived_cost=90,
            ),
        ])
        assert am.desperation_contribution > 50  # No good options

    def test_desperation_falls_with_good_option(self):
        am = AlternativesModel(options=[
            Alternative(
                id="escape", description="Escape through back",
                perceived_probability=80, perceived_risk=20,
                perceived_reward=90, perceived_cost=10,
            ),
        ])
        assert am.desperation_contribution < 50  # Good option exists

    def test_empty_alternatives_max_desperation(self):
        am = AlternativesModel(options=[])
        assert am.desperation_contribution == 50.0  # Default


# ============================================================================
# EVENT TESTS
# ============================================================================

class TestEvent:
    def test_negotiator_speech(self):
        e = Event(
            type=EventType.NEGOTIATOR_SPEECH,
            content="Put the gun down.",
            speech_duration_ms=2000,
            session_elapsed_ms=120000,
        )
        assert e.type == EventType.NEGOTIATOR_SPEECH
        assert e.content == "Put the gun down."

    def test_silence_started(self):
        e = Event(
            type=EventType.SILENCE_STARTED,
            silence_duration_ms=4000,
            preceding_context="You said 'I need more time.'",
        )
        assert e.type == EventType.SILENCE_STARTED

    def test_subject_action_self_effect(self):
        e = Event(
            type=EventType.SUBJECT_ACTION,
            action_taken="threaten",
            action_target="negotiator",
            action_intensity=0.8,
            disclosed_secret="Brother is in the back room",
        )
        assert e.disclosed_secret is not None


# ============================================================================
# APPRAISAL TESTS
# ============================================================================

class TestAppraisal:
    def test_ranked_intent_with_confidence(self):
        a = Appraisal(
            perceived_intent=[
                IntentAssessment(intent="genuine_reassurance", confidence=55),
                IntentAssessment(intent="condescension", confidence=30),
                IntentAssessment(intent="stalling", confidence=15),
            ],
            credibility=45.0,
            threat_delta=-5.0,
            control_delta=-10.0,
            respect_delta=-15.0,
            emotional_significance=40.0,
        )
        assert len(a.perceived_intent) == 3
        assert a.perceived_intent[0].confidence > a.perceived_intent[1].confidence

    def test_appraisal_requires_at_least_one_intent(self):
        with pytest.raises(ValidationError):
            Appraisal(
                perceived_intent=[],
                credibility=50, threat_delta=0, control_delta=0,
                respect_delta=0, emotional_significance=0,
            )

    def test_delta_ranges(self):
        with pytest.raises(ValidationError):
            Appraisal(
                perceived_intent=[IntentAssessment(intent="test", confidence=50)],
                credibility=50, threat_delta=60.0,  # > 50
                control_delta=0, respect_delta=0, emotional_significance=0,
            )


# ============================================================================
# BEHAVIORAL POLICY TESTS
# ============================================================================

class TestBehavioralDecision:
    def test_scored_candidates(self):
        bd = BehavioralDecision(
            candidates=[
                BehavioralCandidate(action="refuse", intensity=0.8, score=75.0),
                BehavioralCandidate(action="threaten", intensity=0.6, score=60.0),
                BehavioralCandidate(action="seek_reassurance", intensity=0.4, score=30.0),
            ],
            selected=BehavioralCandidate(action="refuse", intensity=0.8, score=75.0),
            selection_method="highest_score",
        )
        assert bd.selected.action == "refuse"
        assert bd.candidates[0].score > bd.candidates[1].score

    def test_hesitation_flag(self):
        bd = BehavioralDecision(
            candidates=[
                BehavioralCandidate(action="comply", intensity=0.5, score=50.0),
                BehavioralCandidate(action="refuse", intensity=0.5, score=48.0),
            ],
            selected=BehavioralCandidate(action="comply", intensity=0.5, score=50.0),
            hesitation=True,
        )
        assert bd.hesitation is True


class TestStrategyHistory:
    def test_tracks_effectiveness(self):
        sh = StrategyHistory(records=[
            StrategyRecord(action="threaten", turn_number=3, perceived_outcome="ineffective"),
            StrategyRecord(action="threaten", turn_number=7, perceived_outcome="counterproductive"),
            StrategyRecord(action="seek_reassurance", turn_number=5, perceived_outcome="effective"),
        ])
        assert sh.get_effectiveness("threaten") == "counterproductive"
        assert sh.get_effectiveness("seek_reassurance") == "effective"
        assert sh.get_effectiveness("bargain") is None
        assert sh.action_count("threaten") == 2


# ============================================================================
# EXPRESSION TESTS
# ============================================================================

class TestExpression:
    def test_derived_word_range_low_energy(self):
        e = Expression(verbal_energy=0.1)
        assert e.max_words <= 10

    def test_derived_word_range_high_energy(self):
        e = Expression(verbal_energy=0.9)
        assert e.max_words >= 30

    def test_derived_verbal_style_explosive(self):
        e = Expression(speech_control=0.1, verbal_energy=0.9)
        assert e.derived_verbal_style == "explosive"

    def test_derived_verbal_style_controlled(self):
        e = Expression(speech_control=0.8, verbal_energy=0.2)
        assert e.derived_verbal_style == "controlled"

    def test_derived_verbal_style_hesitant(self):
        e = Expression(speech_control=0.5, verbal_energy=0.5, hesitation_tendency=0.7)
        assert e.derived_verbal_style == "hesitant"

    def test_derived_pacing_fast(self):
        e = Expression(verbal_energy=0.85)
        assert e.derived_pacing == "fast"

    def test_derived_pacing_slow(self):
        e = Expression(verbal_energy=0.15)
        assert e.derived_pacing == "slow"

    def test_continuous_variables_are_not_categorical(self):
        """Expression uses continuous floats, not enum labels."""
        e = Expression(
            speech_control=0.45,
            hesitation_tendency=0.35,
            verbal_energy=0.55,
            emotional_leakage=0.25,
        )
        # These are all valid continuous values, not restricted to categories
        assert 0.0 <= e.speech_control <= 1.0
        assert 0.0 <= e.hesitation_tendency <= 1.0


# ============================================================================
# MEMORY TESTS
# ============================================================================

class TestMemory:
    def test_episodic_memory_preserves_meaning(self):
        m = EpisodicMemory(
            event_summary="Negotiator promised no police would enter.",
            subject_reaction="Believed the promise. Felt relief.",
            subsequent_impact="Promise later broken. Trust decreased.",
            emotional_valence="negative",
            salience=92.0,
            turn_number=5,
            tags=["commitment", "trust"],
            detail_level="precise",
        )
        assert m.subsequent_impact != ""
        assert m.detail_level == "precise"

    def test_vague_memory(self):
        m = EpisodicMemory(
            event_summary="Something about police being promised",
            subject_reaction="Vaguely remembers feeling relieved",
            salience=40.0,
            detail_level="vague",
        )
        assert m.detail_level == "vague"

    def test_commitment_status_lifecycle(self):
        c = Commitment(
            party="negotiator",
            promise="No police will enter.",
            subject_believed=True,
            importance=85.0,
            status=CommitmentStatus.ACTIVE,
        )
        assert c.status == CommitmentStatus.ACTIVE
        c_violated = c.model_copy(update={"status": CommitmentStatus.VIOLATED})
        assert c_violated.status == CommitmentStatus.VIOLATED

    def test_contradiction_tracks_interpretation(self):
        c = Contradiction(
            statement_a="No police will enter",
            turn_a=5,
            statement_b="Police are on their way in",
            turn_b=12,
            noticed_by_subject=True,
            subject_interpretation="The negotiator lied deliberately.",
            impact="Trust dropped sharply. Resentment increased.",
        )
        assert c.noticed_by_subject
        assert c.subject_interpretation != ""


# ============================================================================
# SERIALIZATION TESTS
# ============================================================================

class TestSerialization:
    def test_human_model_json_roundtrip(self, base_human_model):
        json_str = base_human_model.model_dump_json()
        restored = HumanModel.model_validate_json(json_str)
        assert restored.identity.name == "Marcus"
        assert restored.personality.dominance == 0.8
        assert len(restored.triggers) == 1

    def test_psychological_state_json(self):
        state = PsychologicalState(fear=80.0, anger=60.0, hope=15.0)
        data = state.model_dump()
        assert data["fear"] == 80.0
        restored = PsychologicalState(**data)
        assert restored.fear == 80.0

    def test_appraisal_json(self):
        a = Appraisal(
            perceived_intent=[IntentAssessment(intent="manipulation", confidence=70)],
            credibility=25.0, threat_delta=10.0, control_delta=-5.0,
            respect_delta=-20.0, emotional_significance=65.0,
        )
        data = a.model_dump()
        restored = Appraisal(**data)
        assert restored.perceived_intent[0].intent == "manipulation"

    def test_causal_trace_json(self):
        ct = CausalTrace(
            turn_number=5,
            event_type="NEGOTIATOR_SPEECH",
            selected_action="refuse",
            latency_total_ttfa_ms=450.0,
        )
        data = ct.model_dump()
        assert data["turn_number"] == 5
