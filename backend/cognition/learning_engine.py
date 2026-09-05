import json
import os
import uuid
from typing import Dict, Any
from cognition.experience_store import ExperienceStore, OutcomeSignal
from pydantic import BaseModel

class CalibrationPriors(BaseModel):
    version_id: str
    behavior_weight_modifiers: Dict[str, float] = {}
    expression_hesitation_modifier: float = 0.0
    appraisal_trust_discount: float = 0.0

class LearningCalibrationEngine:
    """
    Offline/Asynchronous statistical engine that aggregates experiences
    and generates non-destructive Bayesian priors for future sessions.
    """
    def __init__(self, store: ExperienceStore, config_path: str = "calibration_priors.json"):
        self.store = store
        self.config_path = config_path
        self.priors = self._load_priors()

    def _load_priors(self) -> CalibrationPriors:
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                return CalibrationPriors.model_validate_json(f.read())
        return CalibrationPriors(version_id="baseline")

    def _save_priors(self, priors: CalibrationPriors):
        with open(self.config_path, "w") as f:
            f.write(priors.model_dump_json(indent=2))

    def calibrate(self) -> CalibrationPriors:
        """
        Aggregates session outcomes and adjusts priors mathematically.
        Does NOT alter individual personality.
        """
        outcomes = self.store.get_all_outcomes()
        
        # We need a minimum sample size to avoid random skew
        if len(outcomes) < 5:
            return self.priors

        # Example global system learning:
        # If goals are systematically failing across many sessions, we might slightly
        # adjust a baseline behavior weight. Or if human_realism_rating is low.
        
        total_sessions = len(outcomes)
        success_rate = sum(1 for o in outcomes if o["goal_achieved"]) / total_sessions
        
        new_version = f"v_{uuid.uuid4().hex[:8]}"
        changes = {}
        
        new_priors = CalibrationPriors(version_id=new_version)
        
        # If success rate is extremely low, maybe we need to decrease stall tendency globally
        if success_rate < 0.2:
            new_priors.behavior_weight_modifiers["stall"] = -10.0
            changes["stall_modifier"] = -10.0
            
        # Example: Recalibrate appraisal trust based on broken promises
        total_promises_broken = sum(o["promises_broken"] for o in outcomes)
        if total_promises_broken > total_sessions * 0.5:
            # The system observes negotiators lie frequently across all sessions.
            # We apply a slight Bayesian discount to incoming credibility.
            new_priors.appraisal_trust_discount = 0.1
            changes["appraisal_trust_discount"] = 0.1
            
        self._save_priors(new_priors)
        self.store.store_calibration(new_version, total_sessions, changes)
        
        self.priors = new_priors
        return self.priors

    def get_active_priors(self) -> CalibrationPriors:
        return self.priors
