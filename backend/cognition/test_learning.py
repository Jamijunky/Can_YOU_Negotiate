import pytest
import os
from cognition.experience_store import ExperienceStore, OutcomeSignal
from cognition.learning_engine import LearningCalibrationEngine

@pytest.fixture
def store():
    db_path = "test_experience.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    s = ExperienceStore(db_path)
    yield s
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def engine(store):
    config_path = "test_calibration.json"
    if os.path.exists(config_path):
        os.remove(config_path)
    e = LearningCalibrationEngine(store, config_path)
    yield e
    if os.path.exists(config_path):
        os.remove(config_path)

def test_system_level_learning(store, engine):
    """
    Simulate many bad negotiations (promises broken) globally.
    Verify the system calibrates the appraisal_trust_discount globally.
    """
    # Under minimum sample size
    store.store_outcome("sub1", OutcomeSignal(session_id="1", goal_achieved=False, negotiator_complied=False, promises_broken=1))
    
    priors_before = engine.calibrate()
    assert priors_before.appraisal_trust_discount == 0.0
    
    # Exceed minimum sample size
    for i in range(2, 6):
        store.store_outcome(f"sub{i}", OutcomeSignal(session_id=str(i), goal_achieved=False, negotiator_complied=False, promises_broken=1))
        
    priors_after = engine.calibrate()
    assert priors_after.appraisal_trust_discount > 0.0
    assert "baseline" not in priors_after.version_id

def test_subject_level_learning_independence():
    """
    This is handled implicitly by the existing BeliefEngine tracking specific beliefs about the negotiator 
    within the session, but we verify here that subject A's beliefs do not pollute subject B.
    """
    from cognition.schemas import Belief, BeliefChangePathway
    from cognition.belief_engine import update_belief, BeliefUpdateSignal
    from cognition.schemas import Personality
    
    b1 = Belief(id="b1", statement="Negotiator lies", confidence=50.0, tension=0.0, epistemic_status="INFERRED", supporting_evidence=["A"], contradicting_evidence=[], resistance=10.0, change_pathway=BeliefChangePathway.EVIDENTIAL, importance=50.0, provenance="observation")
    b2 = Belief(id="b1", statement="Negotiator lies", confidence=50.0, tension=0.0, epistemic_status="INFERRED", supporting_evidence=["B"], contradicting_evidence=[], resistance=10.0, change_pathway=BeliefChangePathway.EVIDENTIAL, importance=50.0, provenance="observation")
    
    p = Personality(dominance=0.5, pride=0.5, risk_tolerance=0.5, impulsivity=0.5, trust_tendency=0.5, emotional_volatility=0.5, need_for_control=0.5, guilt_tendency=0.5)
    
    # Subject A experiences a lie
    sig = BeliefUpdateSignal(belief_id="b1", direction="support", evidence_statement="Lied", evidence_strength=50.0)
    updated_b1, _ = update_belief(b1, sig, {})
    
    assert updated_b1.confidence > 50.0
    assert b2.confidence == 50.0 # Subject B unaffected!
