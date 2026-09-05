import pytest
import time
from unittest.mock import patch, MagicMock
from cognition.schemas import (
    HumanModel, Identity, Personality,
    Goals, CopingMechanisms, CommunicationStyle,
    PsychologicalState, RelationshipState,
    BehavioralDecision, BehavioralCandidate, ConsequencePrediction,
    Expression, SituationModel
)
from cognition.speech_generator import SpeechGenerator, SpeechGenerationResult

@pytest.fixture
def base_human():
    return HumanModel(
        identity=Identity(name="Test", age=30, occupation="Test"),
        personality=Personality(
            dominance=0.5, pride=0.5, risk_tolerance=0.5,
            impulsivity=0.5, trust_tendency=0.5, emotional_volatility=0.5,
            need_for_control=0.5, guilt_tendency=0.5
        ),
        goals=Goals(primary="survive", secondary="escape", immediate="hide", hidden=""),
        coping=CopingMechanisms(fear_response="freeze", anger_response="yell", stress_response="withdraw"),
        communication_style=CommunicationStyle(
            verbosity=0.5, directness=0.5, politeness=0.5,
            formality=0.5, description="Normal"
        )
    )

@pytest.fixture
def base_decision():
    return BehavioralDecision(
        candidates=[],
        selected=BehavioralCandidate(
            action="demand", target="", intensity=0.8, information_strategy="truth",
            score=50.0, consequence_prediction=ConsequencePrediction(
                expected_negotiator_response="neutral", expected_immediate_goal_effect="aligned",
                expected_longterm_goal_effect="unknown", risk=0.0,
                relationship_consequence="neutral", reversibility="reversible"
            ), rationale=""
        ),
        selection_method="highest_score", hesitation=False
    )

@pytest.fixture
def base_expression():
    return Expression(
        speech_control=0.5, hesitation_tendency=0.5, verbal_energy=0.5,
        emotional_leakage=0.5, directness=0.5, self_correction_tendency=0.5
    )

@patch("cognition.speech_generator.OpenAI")
def test_speech_generation_success(mock_openai, base_human, base_decision, base_expression):
    # Mock LLM response
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"spoken_text": "I want the money now.", "confidence": 1.0, "behavioral_fidelity": 1.0}'
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client
    
    gen = SpeechGenerator(api_key="mock")
    state = PsychologicalState()
    rel = RelationshipState()
    sit = SituationModel()
    
    res = gen.generate(base_human, state, rel, base_decision, base_expression, [], sit)
    
    assert res.spoken_text == "I want the money now."
    assert res.confidence == 1.0
    
@patch("cognition.speech_generator.OpenAI")
def test_speech_generation_removes_stage_directions(mock_openai, base_human, base_decision, base_expression):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"spoken_text": "*sighs* [angry] I want the money now. (looks away)", "confidence": 1.0, "behavioral_fidelity": 1.0}'
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client
    
    gen = SpeechGenerator(api_key="mock")
    state = PsychologicalState()
    rel = RelationshipState()
    sit = SituationModel()
    
    res = gen.generate(base_human, state, rel, base_decision, base_expression, [], sit)
    
    # Assert stage directions removed
    assert res.spoken_text == "I want the money now."

@patch("cognition.speech_generator.OpenAI")
def test_speech_generation_fallback_on_failure(mock_openai, base_human, base_decision, base_expression):
    mock_client = MagicMock()
    # Raise exception
    mock_client.chat.completions.create.side_effect = Exception("API Timeout")
    mock_openai.return_value = mock_client
    
    gen = SpeechGenerator(api_key="mock")
    state = PsychologicalState()
    rel = RelationshipState()
    sit = SituationModel()
    
    res = gen.generate(base_human, state, rel, base_decision, base_expression, [], sit)
    
    # Assert fallback used
    assert res.spoken_text == "I need it right now."
    assert res.confidence == 0.0

@patch("cognition.speech_generator.OpenAI")
def test_latency_is_measured(mock_openai, base_human, base_decision, base_expression):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"spoken_text": "I want the money now.", "confidence": 1.0, "behavioral_fidelity": 1.0}'
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client
    
    gen = SpeechGenerator(api_key="mock")
    state = PsychologicalState()
    rel = RelationshipState()
    sit = SituationModel()
    
    start = time.perf_counter()
    gen.generate(base_human, state, rel, base_decision, base_expression, [], sit)
    end = time.perf_counter()
    
    assert (end - start) < 0.5  # With mock it should be tiny


import os

@pytest.mark.skipif(not os.environ.get("GROQ_API_KEY"), reason="Requires real API key")
def test_live_api_latency_and_fidelity(base_human, base_decision, base_expression):
    gen = SpeechGenerator()
    state = PsychologicalState(fear=90.0)
    rel = RelationshipState(trust=10.0)
    sit = SituationModel()
    
    # Test 1: Demand
    base_decision.selected.action = "demand"
    
    start = time.perf_counter()
    res1 = gen.generate(base_human, state, rel, base_decision, base_expression, [], sit)
    end = time.perf_counter()
    
    assert res1.spoken_text != "I don't know." # Should not fallback
    assert len(res1.spoken_text) > 2 # Should say something
    
    print(f"Speech Gen Latency (Demand): {(end-start)*1000:.1f}ms")
    
    # Test 2: Withdraw
    base_decision.selected.action = "withdraw"
    start = time.perf_counter()
    res2 = gen.generate(base_human, state, rel, base_decision, base_expression, [], sit)
    end = time.perf_counter()
    
    print(f"Speech Gen Latency (Withdraw): {(end-start)*1000:.1f}ms")
