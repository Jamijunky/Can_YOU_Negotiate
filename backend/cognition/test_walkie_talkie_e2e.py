import pytest
from unittest.mock import MagicMock
from cognition.schemas import (
    WorldState, Resource, Capability, WorldUpdateSignal,
    HumanModel, Identity, Personality, Goals, CopingMechanisms, CommunicationStyle,
    PsychologicalState, RelationshipState, SituationModel, GoalState, StrategyHistory
)
from cognition.world_engine import update_world
from cognition.behavioral_policy import BehavioralPolicyEngine
from cognition.pipeline import CognitivePipeline
from cognition.appraisal_engine import AppraisalEngine, CognitiveAppraisal
from cognition.expression_engine import ExpressionEngine, ExpressionHistory
from cognition.speech_generator import SpeechGenerator

def test_walkie_talkie_e2e():
    world = WorldState(
        resources={"walkie_talkie": Resource(id="walkie_talkie", name="Walkie Talkie", holder="negotiator")},
        capabilities={"subject_can_use_walkie_talkie": Capability(id="subject_can_use_walkie_talkie", name="Use WT", enabled=False)}
    )
    
    signal = WorldUpdateSignal(action="transfer", object_id="walkie_talkie", actor="negotiator", target="subject")
    
    new_world, meta = update_world(world, signal)
    assert meta["status"] == "accepted"
    assert new_world.resources["walkie_talkie"].holder == "subject"
    assert new_world.capabilities["subject_can_use_walkie_talkie"].enabled == True
    
    policy_engine = BehavioralPolicyEngine()
    candidates = policy_engine.generate_candidates()
    
    # 1. Before world update: walkie talkie action is structurally filtered out
    feasible_before = policy_engine.filter_feasible(candidates, SituationModel(), world)
    assert not any(c.action == "use_walkie_talkie" for c in feasible_before)
    
    # 2. After world update: walkie talkie action is structurally feasible
    feasible_after = policy_engine.filter_feasible(candidates, SituationModel(), new_world)
    assert any(c.action == "use_walkie_talkie" for c in feasible_after)
    
    # 3. Full CognitivePipeline end-to-end integration test
    human = HumanModel(
        identity=Identity(name="Test Subject", age=30, occupation="Test"),
        personality=Personality(
            dominance=0.5, pride=0.5, risk_tolerance=0.5,
            impulsivity=0.5, trust_tendency=0.5, emotional_volatility=0.5,
            need_for_control=0.5, guilt_tendency=0.5
        ),
        goals=Goals(primary="survive", secondary="escape", immediate="hide", hidden=""),
        coping=CopingMechanisms(fear_response="freeze", anger_response="yell", stress_response="withdraw"),
        communication_style=CommunicationStyle(
            verbosity=0.5, directness=0.5, politeness=0.5,
            formality=0.5, description="Direct"
        )
    )
    
    from cognition.state_engine import StateUpdateSignal
    from cognition.relationship_engine import RelationshipUpdateSignal

    mock_appraisal_engine = MagicMock()
    mock_appraisal = CognitiveAppraisal(
        primary_intent="provide_walkie_talkie",
        primary_intent_confidence=95.0,
        alternative_interpretations=[],
        state_updates=StateUpdateSignal(),
        relationship_updates=RelationshipUpdateSignal(),
        belief_updates=[],
        situation_updates=[],
        commitment_updates=[],
        world_updates=[signal]
    )
    mock_appraisal_engine.appraise.return_value = mock_appraisal
    
    pipeline = CognitivePipeline(
        appraisal_engine=mock_appraisal_engine,
        policy_engine=policy_engine,
        expression_engine=ExpressionEngine(),
        speech_generator=SpeechGenerator(api_key="mock")
    )
    
    speech_res, trace = pipeline.process_turn(
        input_transcript="Here is your walkie-talkie.",
        human=human,
        state=PsychologicalState(),
        rel=RelationshipState(trust=60.0),
        situation=SituationModel(),
        beliefs=[],
        goals=GoalState(),
        strategy_history=StrategyHistory(),
        expression_history=ExpressionHistory(),
        recent_context=["I need a way to communicate."],
        world=world
    )
    
    # Verify authoritative world state mutated correctly in trace
    assert trace.world_state is not None
    assert trace.world_state["resources"]["walkie_talkie"]["holder"] == "subject"
    assert trace.world_state["capabilities"]["subject_can_use_walkie_talkie"]["enabled"] is True
    assert any(u.get("status") == "accepted" for u in trace.world_updates)

