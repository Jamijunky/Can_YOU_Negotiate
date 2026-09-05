import pytest
from cognition.schemas import WorldState, WorldUpdateSignal, Resource, Capability
from cognition.world_engine import update_world

def test_resource_transfer():
    world = WorldState(
        resources={"walkie_talkie": Resource(id="walkie_talkie", name="Walkie Talkie", holder="negotiator")},
        capabilities={"subject_can_use_walkie_talkie": Capability(id="subject_can_use_walkie_talkie", name="Use WT", enabled=False)}
    )
    signal = WorldUpdateSignal(action="transfer", object_id="walkie_talkie", actor="negotiator", target="subject")
    new_world, meta = update_world(world, signal)
    
    assert meta["status"] == "accepted"
    assert new_world.resources["walkie_talkie"].holder == "subject"
    assert new_world.capabilities["subject_can_use_walkie_talkie"].enabled == True

def test_invalid_resource_transfer():
    world = WorldState(
        resources={"walkie_talkie": Resource(id="walkie_talkie", name="Walkie Talkie", holder="system")}
    )
    # Negotiator doesn't have it
    signal = WorldUpdateSignal(action="transfer", object_id="walkie_talkie", actor="negotiator", target="subject")
    new_world, meta = update_world(world, signal)
    
    assert meta["status"] == "rejected"
    assert new_world.resources["walkie_talkie"].holder == "system"

def test_negotiator_claim_vs_authoritative_reality():
    world = WorldState()
    # Negotiator claims they have a helicopter
    signal = WorldUpdateSignal(action="claim", object_id="helicopter", actor="negotiator", validity="CLAIMED")
    new_world, meta = update_world(world, signal)
    
    assert meta["status"] == "rejected"
    assert "helicopter" not in new_world.resources


def test_resource_consumption():
    world = WorldState(
        resources={"first_aid": Resource(id="first_aid", name="First Aid Kit", holder="subject", available=True)}
    )
    # Subject consumes the resource
    signal = WorldUpdateSignal(action="consume", object_id="first_aid", actor="subject")
    new_world, meta = update_world(world, signal)
    
    assert meta["status"] == "accepted"
    assert new_world.resources["first_aid"].available is False

    # Second consumption must be rejected
    second_world, meta2 = update_world(new_world, signal)
    assert meta2["status"] == "rejected"


def test_invalid_resource_creation_via_claim():
    world = WorldState()
    # Negotiator says "There's a helicopter outside"
    # Even if claim is proposed, world does not gain helicopter
    signal = WorldUpdateSignal(action="claim", object_id="helicopter", actor="negotiator", validity="CLAIMED")
    new_world, meta = update_world(world, signal)
    assert "helicopter" not in new_world.resources
    assert meta["status"] == "rejected"


def test_policy_respects_world_constraints():
    from cognition.behavioral_policy import BehavioralPolicyEngine
    from cognition.schemas import SituationModel
    
    policy = BehavioralPolicyEngine()
    candidates = policy.generate_candidates()
    
    # World where subject does NOT have walkie-talkie capability enabled
    world_no_wt = WorldState(
        resources={"walkie_talkie": Resource(id="walkie_talkie", name="Walkie Talkie", holder="negotiator")},
        capabilities={"subject_can_use_walkie_talkie": Capability(id="subject_can_use_walkie_talkie", name="Use WT", enabled=False)}
    )
    feasible = policy.filter_feasible(candidates, SituationModel(), world_no_wt)
    assert not any(c.action == "use_walkie_talkie" for c in feasible)

    # World where capability IS enabled
    world_has_wt = WorldState(
        resources={"walkie_talkie": Resource(id="walkie_talkie", name="Walkie Talkie", holder="subject")},
        capabilities={"subject_can_use_walkie_talkie": Capability(id="subject_can_use_walkie_talkie", name="Use WT", enabled=True)}
    )
    feasible_wt = policy.filter_feasible(candidates, SituationModel(), world_has_wt)
    assert any(c.action == "use_walkie_talkie" for c in feasible_wt)


def test_speech_generator_incorporates_world_facts():
    from unittest.mock import MagicMock
    from cognition.speech_generator import SpeechGenerator
    from cognition.schemas import (
        HumanModel, Identity, Personality, Goals, CopingMechanisms, CommunicationStyle,
        PsychologicalState, RelationshipState, SituationModel, BehavioralDecision, BehavioralCandidate
    )
    
    gen = SpeechGenerator(api_key="mock")
    gen.client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"spoken_text": "I copy you loud and clear on the radio.", "confidence": 1.0, "behavioral_fidelity": 1.0}'
    gen.client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
    
    world = WorldState(
        resources={"walkie_talkie": Resource(id="walkie_talkie", name="Walkie Talkie", holder="subject")},
        capabilities={"subject_can_use_walkie_talkie": Capability(id="subject_can_use_walkie_talkie", name="Use WT", enabled=True)}
    )
    human = HumanModel(
        identity=Identity(name="Alex", age=30, occupation="Subject"),
        personality=Personality(
            dominance=0.5, pride=0.5, risk_tolerance=0.5,
            impulsivity=0.5, trust_tendency=0.5, emotional_volatility=0.5,
            need_for_control=0.5, guilt_tendency=0.5
        ),
        goals=Goals(primary="Survive", secondary="None", immediate="None", hidden="None"),
        coping=CopingMechanisms(fear_response="silence", anger_response="explosive", stress_response="talking_more"),
        communication_style=CommunicationStyle(description="Direct", directness=0.8, verbosity=0.4, formality=0.3, manipulation=0.0, hostility=0.0, habits=[])
    )
    decision = BehavioralDecision(
        candidates=[],
        selected=BehavioralCandidate(action="use_walkie_talkie", intensity=0.7, score=60.0)
    )
    from cognition.schemas import Expression
    expr = Expression(speech_control=0.5, hesitation_tendency=0.2, verbal_energy=0.5, emotional_leakage=0.3, directness=0.8, self_correction_tendency=0.2)
    
    res = gen.generate(
        human=human,
        state=PsychologicalState(),
        rel=RelationshipState(trust=60.0),
        decision=decision,
        expression=expr,
        beliefs=[],
        situation=SituationModel(),
        world=world
    )
    assert res.spoken_text == "I copy you loud and clear on the radio."
    assert res.confidence == 1.0
    
    # Check that prompt sent to OpenAI includes authoritative world facts
    call_args = gen.client.chat.completions.create.call_args[1]
    prompt_sent = call_args["messages"][0]["content"]
    assert "AUTHORITATIVE WORLD FACTS" in prompt_sent
    assert "Subject physically possesses: Walkie Talkie" in prompt_sent
    assert "Subject capability enabled: Use WT" in prompt_sent
