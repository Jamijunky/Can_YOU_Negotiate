import random
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from cognition.schemas import (
    HumanModel,
    PsychologicalState,
    RelationshipState,
    BehavioralDecision,
    Expression
)

class ExpressionHistory(BaseModel):
    recent_expressions: List[Expression] = Field(default_factory=list)

class ExpressionResult(BaseModel):
    expression: Expression
    metadata: Dict[str, Any]

class ExpressionEngine:
    """
    Computes HOW a subject will express a decided behavior.
    Uses continuous state dimensions, personality, and relationship bounds.
    """
    def __init__(self, momentum_weight: float = 0.3):
        self.momentum_weight = momentum_weight

    def generate_expression(
        self,
        human: HumanModel,
        state: PsychologicalState,
        rel: RelationshipState,
        decision: BehavioralDecision,
        history: ExpressionHistory,
        seed: Optional[int] = None
    ) -> ExpressionResult:
        if seed is not None:
            random.seed(seed)
        else:
            seed = random.randint(0, 1000000)
            random.seed(seed)

        # 1. Base traits
        dom = human.personality.dominance
        imp = human.personality.impulsivity
        ctrl = 1.0 - imp  # emotional control is inverse of impulsivity
        risk = human.personality.risk_tolerance

        # 2. State
        fear = state.fear / 100.0
        anger = state.anger / 100.0
        stress = state.stress / 100.0
        desp = state.desperation / 100.0
        
        trust = rel.trust / 100.0
        threat = rel.perceived_threat / 100.0
        
        action = decision.selected.action
        intensity = decision.selected.intensity
        hesitation_flag = decision.hesitation

        metadata = {
            "seed": seed,
            "primary_causes": [],
            "input_snapshot": {
                "fear": fear, "anger": anger, "stress": stress, "desp": desp,
                "dom": dom, "ctrl": ctrl, "action": action
            }
        }

        # --- Speech Control ---
        base_control = ctrl
        pressure = (fear + anger + stress + desp) / 4.0
        control_drain = max(0.0, pressure - (ctrl * 0.8))
        speech_control = base_control - control_drain
        
        if action in ["escalate", "threaten", "accuse"]:
            speech_control -= 0.2 * intensity
            metadata["primary_causes"].append("Action highly aggressive, lower speech control")
            
        speech_control = max(0.0, min(1.0, speech_control))

        # --- Verbal Energy ---
        base_energy = (dom + (1.0 - ctrl)) / 2.0
        energy = base_energy
        if anger > 0.4:
            energy += (anger - 0.4) * 1.5
        if fear > 0.6:
            if dom > 0.5:
                energy += fear * 0.5 
                metadata["primary_causes"].append("Dominant + Fear = frantic energy")
            else:
                energy -= fear * 0.8 
                metadata["primary_causes"].append("Submissive + Fear = withdrawn energy")
                
        if action in ["withdraw", "remain_silent", "evade"]:
            energy -= 0.3
            metadata["primary_causes"].append("Withdrawing action lowers energy")
            
        verbal_energy = max(0.0, min(1.0, energy))

        # --- Hesitation Tendency ---
        hesitation = (1.0 - dom) * 0.3 + fear * 0.4 + (1.0 - ctrl) * 0.2
        if hesitation_flag:
            hesitation += 0.3
            metadata["primary_causes"].append("Behavioral ambivalence boosts hesitation")
        if action in ["demand", "threaten", "refuse"]:
            hesitation -= 0.3
            
        hesitation_tendency = max(0.0, min(1.0, hesitation))

        # --- Directness ---
        direct = dom * 0.5 + trust * 0.3 + (1.0 - fear) * 0.2
        if action in ["fully_disclose", "demand", "accuse", "threaten"]:
            direct += 0.4
            metadata["primary_causes"].append("Direct action type boosts directness")
        if action in ["evade", "lie", "withdraw", "conceal"]:
            direct -= 0.4
            metadata["primary_causes"].append("Evasive action type lowers directness")
            
        directness = max(0.0, min(1.0, direct))

        # --- Emotional Leakage ---
        leakage = pressure * (1.0 - speech_control)
        if leakage > 0.5:
            metadata["primary_causes"].append("High pressure vs low control causes emotional leakage")
        emotional_leakage = max(0.0, min(1.0, leakage))

        # --- Self-correction ---
        self_corr = stress * 0.4 + (1.0 - ctrl) * 0.3 + hesitation_tendency * 0.3
        if action == "lie":
            self_corr += (1.0 - ctrl) * 0.4
            metadata["primary_causes"].append("Lying with low control boosts self-correction")
            
        self_correction_tendency = max(0.0, min(1.0, self_corr))

        # --- Concealed vs Leaked States ---
        concealed = []
        leaked = []
        if fear > 0.5:
            if speech_control > 0.5: concealed.append("fear")
            if emotional_leakage > 0.3: leaked.append("fear")
        if anger > 0.5:
            if speech_control > 0.5: concealed.append("anger")
            if emotional_leakage > 0.3: leaked.append("anger")

        # --- Momentum (History) ---
        metadata["deltas"] = {}
        if history.recent_expressions:
            last_expr = history.recent_expressions[-1]
            mw = self.momentum_weight
            
            sc_raw = speech_control
            speech_control = speech_control * (1 - mw) + last_expr.speech_control * mw
            metadata["deltas"]["speech_control"] = speech_control - last_expr.speech_control
            
            ht_raw = hesitation_tendency
            hesitation_tendency = hesitation_tendency * (1 - mw) + last_expr.hesitation_tendency * mw
            metadata["deltas"]["hesitation_tendency"] = hesitation_tendency - last_expr.hesitation_tendency
            
            ve_raw = verbal_energy
            verbal_energy = verbal_energy * (1 - mw) + last_expr.verbal_energy * mw
            metadata["deltas"]["verbal_energy"] = verbal_energy - last_expr.verbal_energy
            
            el_raw = emotional_leakage
            emotional_leakage = emotional_leakage * (1 - mw) + last_expr.emotional_leakage * mw
            metadata["deltas"]["emotional_leakage"] = emotional_leakage - last_expr.emotional_leakage
            
            dir_raw = directness
            directness = directness * (1 - mw) + last_expr.directness * mw
            metadata["deltas"]["directness"] = directness - last_expr.directness
            
            sct_raw = self_correction_tendency
            self_correction_tendency = self_correction_tendency * (1 - mw) + last_expr.self_correction_tendency * mw
            metadata["deltas"]["self_correction_tendency"] = self_correction_tendency - last_expr.self_correction_tendency

        # --- Controlled Stochasticity ---
        def jitter(val):
            return max(0.0, min(1.0, val + random.uniform(-0.05, 0.05)))
            
        expr = Expression(
            speech_control=jitter(speech_control),
            hesitation_tendency=jitter(hesitation_tendency),
            verbal_energy=jitter(verbal_energy),
            emotional_leakage=jitter(emotional_leakage),
            directness=jitter(directness),
            self_correction_tendency=jitter(self_correction_tendency),
            concealed_states=concealed,
            leaked_states=leaked,
            hesitation=hesitation_flag
        )
        
        metadata["derived_pacing"] = expr.derived_pacing
        metadata["derived_verbal_style"] = expr.derived_verbal_style
        
        history.recent_expressions.append(expr)
        if len(history.recent_expressions) > 5:
            history.recent_expressions.pop(0)

        return ExpressionResult(expression=expr, metadata=metadata)
