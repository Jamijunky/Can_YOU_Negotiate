import os
import sys
import json
import time
import random
from typing import List, Dict, Any

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from cognition.schemas import (
    HumanModel, Identity, Personality, Goals, CopingMechanisms, CommunicationStyle,
    PsychologicalState, RelationshipState, SituationModel, GoalState, StrategyHistory,
    WorldState, Resource, Capability, Trigger
)
from cognition.state_engine import apply_state_transition, StateUpdateSignal
from cognition.relationship_engine import update_relationship, RelationshipUpdateSignal
from cognition.behavioral_policy import BehavioralPolicyEngine
from cognition.expression_engine import ExpressionEngine, ExpressionHistory
from cognition.world_engine import update_world
from cognition.experience_store import ExperienceStore, OutcomeSignal
from cognition.learning_engine import LearningCalibrationEngine

ARCHETYPES = [
    {"role": "Panicked Student", "age_range": (18, 24), "primary_goal": "survive without going to jail", "dominance": (0.1, 0.4), "fear_resp": "compliance"},
    {"role": "Desperate Parent", "age_range": (28, 45), "primary_goal": "protect family and secure medical funds", "dominance": (0.4, 0.7), "fear_resp": "plead"},
    {"role": "Corporate Embezzler", "age_range": (35, 58), "primary_goal": "avoid public ruin and prison", "dominance": (0.5, 0.8), "fear_resp": "control_seeking"},
    {"role": "Hardened Bank Robber", "age_range": (30, 50), "primary_goal": "escape with the cash unharmed", "dominance": (0.7, 0.95), "fear_resp": "aggression"},
    {"role": "Paranoid Whistleblower", "age_range": (26, 42), "primary_goal": "expose conspiracy before getting killed", "dominance": (0.3, 0.6), "fear_resp": "withdrawal"},
    {"role": "Rogue Ex-Military Veteran", "age_range": (35, 62), "primary_goal": "demand justice for fallen comrades", "dominance": (0.8, 0.95), "fear_resp": "cold_logic"},
    {"role": "Erratic Hacktivist", "age_range": (20, 32), "primary_goal": "leak corrupt database to the world", "dominance": (0.4, 0.7), "fear_resp": "rambling"},
    {"role": "Trapped Courier", "age_range": (22, 38), "primary_goal": "deliver the package or escape alive", "dominance": (0.3, 0.6), "fear_resp": "silence"},
    {"role": "Vengeful Investor", "age_range": (40, 65), "primary_goal": "force recovery of life savings", "dominance": (0.6, 0.85), "fear_resp": "demands"},
    {"role": "Disgruntled Lab Technician", "age_range": (27, 48), "primary_goal": "halt dangerous corporate project", "dominance": (0.3, 0.6), "fear_resp": "precision"}
]

FIRST_NAMES_MALE = ["Marcus", "Yusuf", "Arthur", "Sam", "David", "Carlos", "Viktor", "Chen", "Darius", "Liam", "Tariq", "Elena", "Mateo", "Kenji", "Rashid"]
FIRST_NAMES_FEMALE = ["Maria", "Elara", "Sarah", "Amina", "Chloe", "Priya", "Nadia", "Ling", "Fatima", "Leila", "Zoe", "Ingrid", "Keiko", "Maya", "Valeria"]

def generate_profile(idx: int) -> HumanModel:
    arch = ARCHETYPES[idx % len(ARCHETYPES)]
    is_female = (idx % 2 == 1)
    name = (FIRST_NAMES_FEMALE if is_female else FIRST_NAMES_MALE)[idx % len(FIRST_NAMES_FEMALE)] + f"_{idx}"
    age = random.randint(arch["age_range"][0], arch["age_range"][1])
    
    dom_min, dom_max = arch["dominance"]
    dominance = round(random.uniform(dom_min, dom_max), 2)
    impulsivity = round(random.uniform(0.1, 0.95), 2)
    trust_tendency = round(random.uniform(0.05, 0.75), 2)
    risk_tolerance = round(random.uniform(0.1, 0.9), 2)
    emotional_volatility = round(random.uniform(0.2, 0.95), 2)
    need_for_control = round(random.uniform(0.3, 0.95), 2)
    pride = round(random.uniform(0.2, 0.95), 2)
    guilt_tendency = round(random.uniform(0.1, 0.8), 2)

    return HumanModel(
        identity=Identity(name=name, age=age, occupation=arch["role"]),
        personality=Personality(
            dominance=dominance,
            impulsivity=impulsivity,
            trust_tendency=trust_tendency,
            risk_tolerance=risk_tolerance,
            emotional_volatility=emotional_volatility,
            need_for_control=need_for_control,
            pride=pride,
            guilt_tendency=guilt_tendency,
        ),
        goals=Goals(
            primary=arch["primary_goal"],
            secondary="avoid bodily harm",
            immediate="assess negotiator credibility",
            hidden="hide the escape contingency"
        ),
        coping=CopingMechanisms(
            fear_response=arch["fear_resp"],
            anger_response=random.choice(["explosive", "cold_logic", "demands", "threats", "sarcasm"]),
            stress_response=random.choice(["talking_more", "talking_less", "confusion", "precision", "repetition"])
        ),
        communication_style=CommunicationStyle(
            description=f"Speaks as a {arch['role']} under severe duress.",
            directness=round(random.uniform(0.2, 0.9), 2),
            verbosity=round(random.uniform(0.2, 0.8), 2),
            formality=round(random.uniform(0.1, 0.8), 2)
        ),
        triggers=[
            Trigger(id="t1", topic="prison", sensitivity=0.8),
            Trigger(id="t2", topic="family", sensitivity=0.7)
        ]
    )

def audit_profiles(num_profiles: int = 100) -> Dict[str, Any]:
    print(f"Starting audit across {num_profiles} distinct psychological profiles...")
    policy_engine = BehavioralPolicyEngine(seed=42)
    expr_engine = ExpressionEngine()
    store = ExperienceStore(db_path="audit_experience.db")
    learning_engine = LearningCalibrationEngine(store=store, config_path="audit_calibration.json")
    
    anomalies = []
    profile_results = []
    
    start_time = time.time()
    
    for i in range(num_profiles):
        profile = generate_profile(i)
        
        # Initialize initial states
        state = PsychologicalState(
            fear=round(random.uniform(30.0, 85.0), 1),
            anger=round(random.uniform(10.0, 70.0), 1),
            stress=round(random.uniform(40.0, 90.0), 1),
            desperation=round(random.uniform(20.0, 80.0), 1),
            guilt=round(random.uniform(5.0, 60.0), 1),
            hope=round(random.uniform(10.0, 50.0), 1),
            sense_of_control=round(random.uniform(10.0, 60.0), 1),
        )
        relationship = RelationshipState(
            trust=round(profile.personality.trust_tendency * 50.0, 1),
            respect=40.0,
            familiarity=10.0,
            perceived_threat=60.0,
            rapport=20.0
        )
        situation = SituationModel()
        history = StrategyHistory()
        world = WorldState()
        
        # Simulate Turn 1: Opening Contact
        decision = policy_engine.select_action(
            human=profile,
            state=state,
            relationship=relationship,
            situation=situation,
            beliefs=[],
            history=history,
            world=world
        )
        
        # Validation checks
        if not decision or not decision.selected or not decision.selected.action:
            anomalies.append(f"Profile {i} ({profile.identity.name}): Empty decision returned")
            
        # Check for state boundary violations
        for attr in ["fear", "anger", "stress", "desperation", "guilt", "hope", "sense_of_control"]:
            val = getattr(state, attr)
            if val < 0.0 or val > 100.0 or val != val: # NaN check
                anomalies.append(f"Profile {i} ({profile.identity.name}): State {attr} out of bounds: {val}")

        # Simulate Turn 2: Negotiator pushes or tests
        state_sig = StateUpdateSignal(
            threat_delta=random.uniform(-10.0, 15.0),
            insult_delta=random.uniform(-5.0, 20.0),
            loss_of_control_delta=random.uniform(-5.0, 15.0)
        )
        state, _ = apply_state_transition(state, profile.personality, state_sig)
        
        # Verify post-transition bounds
        for attr in ["fear", "anger", "stress"]:
            val = getattr(state, attr)
            if val < 0.0 or val > 100.0 or val != val:
                anomalies.append(f"Profile {i} ({profile.identity.name}) after transition: State {attr} out of bounds: {val}")

        # Evaluate expression
        expr_hist = ExpressionHistory()
        expr_result = expr_engine.generate_expression(
            human=profile,
            state=state,
            rel=relationship,
            decision=decision,
            history=expr_hist
        )
        
        if expr_result.expression.verbal_energy < 0 or expr_result.expression.verbal_energy > 1.0:
            anomalies.append(f"Profile {i} ({profile.identity.name}): Abnormal verbal energy {expr_result.expression.verbal_energy}")

        # Record outcome in experience store
        outcome = OutcomeSignal(
            session_id=f"audit_session_{i}",
            goal_achieved=(state.fear < 40 and state.anger < 30 and relationship.trust > 50),
            negotiator_complied=random.choice([True, False]),
            promises_broken=1 if profile.personality.dominance > 0.8 and state.anger > 50 else 0,
            promises_kept=1 if relationship.trust > 40 else 0,
            human_realism_rating=0.92,
            final_trust=relationship.trust
        )
        store.store_outcome(profile.identity.name, outcome)
        
        profile_results.append({
            "id": i,
            "name": profile.identity.name,
            "role": profile.identity.occupation,
            "dominance": profile.personality.dominance,
            "pride": profile.personality.pride,
            "chosen_action": decision.selected.action,
            "intensity": decision.selected.intensity,
            "speech_control": round(expr_result.expression.speech_control, 2),
            "verbal_energy": round(expr_result.expression.verbal_energy, 2),
            "hesitation_tendency": round(expr_result.expression.hesitation_tendency, 2),
            "final_fear": round(state.fear, 1),
            "final_anger": round(state.anger, 1),
            "final_stress": round(state.stress, 1)
        })

    # Calibrate learning across all 100 sessions
    priors = learning_engine.calibrate()
    
    elapsed = time.time() - start_time
    
    report = {
        "total_profiles_tested": num_profiles,
        "elapsed_seconds": round(elapsed, 2),
        "total_anomalies_detected": len(anomalies),
        "anomalies": anomalies,
        "calibrated_priors": priors.model_dump(),
        "sample_profiles": profile_results[:10],
        "action_distribution": {}
    }
    
    for r in profile_results:
        act = r["chosen_action"]
        report["action_distribution"][act] = report["action_distribution"].get(act, 0) + 1
        
    return report

if __name__ == "__main__":
    report = audit_profiles(100)
    print("\nAUDIT SUMMARY:")
    print(f"Profiles tested: {report['total_profiles_tested']}")
    print(f"Total anomalies: {report['total_anomalies_detected']}")
    print(f"Time taken: {report['elapsed_seconds']}s")
    print("Action distribution:", json.dumps(report["action_distribution"], indent=2))
    print("Calibrated Priors:", json.dumps(report["calibrated_priors"], indent=2))
    
    with open("audit_100_profiles_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nSaved full audit report to audit_100_profiles_report.json")
