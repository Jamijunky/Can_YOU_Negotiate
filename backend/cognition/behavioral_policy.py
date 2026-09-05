import random
import math
from typing import List, Optional
from cognition.schemas import (
    WorldState,
    HumanModel, PsychologicalState, RelationshipState, SituationModel, 
    Belief, BehavioralCandidate, BehavioralDecision, StrategyHistory,
    ConsequencePrediction
)

class BehavioralPolicyEngine:
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        
    def generate_candidates(self) -> List[BehavioralCandidate]:
        actions = [
            "answer", "refuse", "evade", "bargain", "lie", 
            "partially_disclose", "fully_disclose", "question", 
            "challenge", "accuse", "seek_reassurance", "change_topic", 
            "withdraw", "remain_silent", "correct", "test", 
            "threaten", "backtrack", "admit", "deny", "demand", 
            "surrender", "escalate", "plead", "test_boundaries", "use_walkie_talkie"
        ]
        return [BehavioralCandidate(action=a, intensity=0.5) for a in actions]

    def filter_feasible(self, candidates: List[BehavioralCandidate], situation: SituationModel, world: WorldState = None) -> List[BehavioralCandidate]:
        """Filters out actions that are structurally impossible given the situation and world."""
        feasible = []
        for c in candidates:
            if world and c.action == "use_walkie_talkie":
                cap = world.capabilities.get("subject_can_use_walkie_talkie")
                if not cap or not getattr(cap, "enabled", False):
                    continue
            feasible.append(c)
        return feasible

    def _get_dynamic_goal_weights(self, human: HumanModel, state: PsychologicalState) -> dict:
        """Goals become more urgent based on state."""
        weights = {"survival": 1.0, "dignity": 1.0, "control": 1.0, "information": 1.0}
        
        # High fear spikes survival urgency
        weights["survival"] += (state.fear / 50.0) 
        
        # High anger or dominance spikes control/dignity
        weights["control"] += (state.anger / 50.0) + (human.personality.dominance - 0.5)
        weights["dignity"] += (human.personality.pride - 0.5) * 2.0
        
        # Desperation makes survival paramount but sacrifices dignity
        weights["survival"] += (state.desperation / 30.0)
        weights["dignity"] -= (state.desperation / 50.0)
        
        return weights

    def evaluate_candidate(
        self, 
        candidate: BehavioralCandidate,
        human: HumanModel,
        state: PsychologicalState,
        relationship: RelationshipState,
        beliefs: List[Belief],
        history: StrategyHistory,
        goal_weights: dict
    ) -> BehavioralCandidate:
        score = 0.0
        rationale = []
        
        action = candidate.action
        
        # --- 1. GOAL ALIGNMENT ---
        if action in ["surrender", "seek_reassurance", "fully_disclose"]:
            # Sacrifices control for survival (usually)
            val = goal_weights["survival"] * 10.0 - goal_weights["control"] * 5.0
            score += val
            rationale.append(f"Goal alignment: {val:.1f}")
        
        if action in ["threaten", "escalate", "demand", "refuse"]:
            # Asserts control/dignity, risks survival
            val = goal_weights["control"] * 8.0 + goal_weights["dignity"] * 5.0 - goal_weights["survival"] * 5.0
            score += val
            rationale.append(f"Goal alignment: {val:.1f}")
            
        if action in ["question", "test", "use_walkie_talkie"]:
            val = goal_weights["information"] * 10.0
            score += val
            rationale.append(f"Information value: {val:.1f}")
            
        # --- 2. RELATIONSHIP EFFECT ---
        # Trust makes cooperative actions more viable
        trust_factor = (relationship.trust - 50.0) / 10.0  # -5 to +5
        if action in ["fully_disclose", "admit", "surrender", "seek_reassurance", "bargain"]:
            score += trust_factor * 2.0
            rationale.append(f"Trust factor (+coop): {trust_factor*2.0:.1f}")
        if action in ["lie", "evade", "deny", "accuse"]:
            score -= trust_factor * 2.0 # High trust penalizes lies
            rationale.append(f"Trust factor (-coop): {-trust_factor*2.0:.1f}")

        # Threat perception makes defensive/aggressive actions viable
        threat_factor = (relationship.perceived_threat - 50.0) / 10.0
        if action in ["withdraw", "remain_silent", "lie", "deny", "escalate"]:
            score += threat_factor * 1.5
            rationale.append(f"Threat factor: {threat_factor*1.5:.1f}")
        if action in ["surrender", "seek_reassurance", "fully_disclose"]:
            score -= threat_factor * 5.0
            rationale.append(f"Threat factor (-coop): {-threat_factor*5.0:.1f}")
            
        # Surrender requires safety and trust; opening contact without rapport must not immediately surrender
        if action == "surrender":
            if relationship.trust < 40.0:
                penalty = (40.0 - relationship.trust) * 1.5
                score -= penalty
                rationale.append(f"Lack of trust penalty for surrender: {-penalty:.1f}")
            if state.stress > 50.0 and state.anger > 40.0:
                score -= 25.0
                rationale.append("Agitated state blocks surrender: -25.0")
            
        # --- 3. PSYCHOLOGICAL STATE (EMOTIONAL PRESSURE) ---
        if action in ["accuse", "challenge", "threaten", "escalate", "refuse"]:
            val = (state.anger / 10.0)
            score += val
            rationale.append(f"Anger pressure: {val:.1f}")
            
        if action in ["withdraw", "remain_silent", "evade"]:
            val = (state.fear / 10.0)
            score += val
            rationale.append(f"Fear pressure: {val:.1f}")
            
        if action in ["seek_reassurance", "surrender"]:
            val = (state.desperation / 15.0)
            score += val
            rationale.append(f"Desperation pressure: {val:.1f}")
            
        if action in ["bargain", "question"]:
            val = (state.hope / 10.0)
            score += val
            rationale.append(f"Hope pressure: {val:.1f}")
            
        # --- 4. PERSONALITY TENDENCIES ---
        if action in ["threaten", "escalate", "lie", "attack"]:
            risk = 80.0
            val = (human.personality.risk_tolerance - 0.5) * 20.0
            score += val
            rationale.append(f"Risk tolerance: {val:.1f}")
        elif action in ["surrender", "admit", "fully_disclose"]:
            risk = 90.0
            val = (human.personality.risk_tolerance - 0.5) * 20.0
            score += val
            rationale.append(f"Risk tolerance: {val:.1f}")
        else:
            risk = 20.0

        if action in ["surrender", "admit", "withdraw"]:
            val = -(human.personality.pride - 0.5) * 35.0
            score += val
            rationale.append(f"Pride constraint: {val:.1f}")

        # --- 5. BELIEF CONSISTENCY (Ambivalence) ---
        total_tension = sum(b.tension for b in beliefs)
        if total_tension > 50.0 and action in ["remain_silent", "evade", "question"]:
            # High ambivalence -> stalling/information gathering
            val = (total_tension / 20.0)
            score += val
            rationale.append(f"Ambivalence hesitation: {val:.1f}")

        # Check explicit beliefs about the negotiator
        for b in beliefs:
            if "lie" in b.statement.lower() or "trust" in b.statement.lower() or "kill" in b.statement.lower():
                if b.confidence > 50:
                    if action in ["believe", "surrender", "fully_disclose", "seek_reassurance"]:
                        score -= 100.0
                        rationale.append(f"Belief constraint ({b.id}): -100.0")

        # --- 6. ACTION HISTORY (Strategic Learning) ---
        penalty = 0.0
        bonus = 0.0
        for record in history.records:
            if record.action == action:
                if record.perceived_outcome in ["ineffective", "counterproductive"]:
                    penalty += 15.0 
                elif record.perceived_outcome == "effective":
                    bonus += 10.0
        if penalty > 0:
            score -= penalty
            rationale.append(f"History penalty: {-penalty}")
        if bonus > 0:
            score += bonus
            rationale.append(f"History bonus: {bonus}")
            
        # --- 7. EXPECTED RESPONSE PREDICTION ---
        expected_response = "neutral_negotiation"
        reversibility = "reversible"
        
        if action == "surrender":
            expected_response = "arrest_and_custody"
            reversibility = "irreversible"
        elif action in ["threaten", "escalate"]:
            expected_response = "aggression_or_force"
            reversibility = "partially_reversible"
        elif action in ["fully_disclose"]:
            reversibility = "partially_reversible"
            
        candidate.consequence_prediction = ConsequencePrediction(
            expected_negotiator_response=expected_response,
            expected_immediate_goal_effect="aligned" if score > 0 else "conflict",
            expected_longterm_goal_effect="unknown",
            risk=risk,
            relationship_consequence="strain" if action in ["threaten", "lie"] else "build",
            reversibility=reversibility
        )
        
        candidate.score = score
        candidate.rationale = " | ".join(rationale)
        return candidate
        
    def select_action(
        self,
        human: HumanModel,
        state: PsychologicalState,
        relationship: RelationshipState,
        situation: SituationModel,
        beliefs: List[Belief],
        history: StrategyHistory,
        world: Optional[WorldState] = None,
        temperature: float = 0.5
    ) -> BehavioralDecision:
        try:
            candidates = self.generate_candidates()
            feasible = self.filter_feasible(candidates, situation, world)
            
            goal_weights = self._get_dynamic_goal_weights(human, state)
            
            evaluated = []
            for c in feasible:
                evaluated.append(self.evaluate_candidate(c, human, state, relationship, beliefs, history, goal_weights))
                
            # Sort highest score first
            evaluated.sort(key=lambda x: x.score, reverse=True)
            
            if not evaluated:
                raise ValueError("No feasible candidates generated.")
                
            top_score = evaluated[0].score
            
            # Stochastic selection among near-top candidates
            # Temperature defines the score threshold window
            threshold_window = 5.0 * temperature
            threshold = top_score - threshold_window
            
            top_candidates = [c for c in evaluated if c.score >= threshold]
            
            if len(top_candidates) == 1 or temperature == 0.0:
                selected = evaluated[0]
                method = "highest_score"
            else:
                # Weighted random choice among top candidates based on score relative to threshold
                # Shift scores so the lowest in the top bracket is at least 1 for weighting
                weights = [max(1.0, c.score - threshold + 1.0) for c in top_candidates]
                selected = self.rng.choices(top_candidates, weights=weights, k=1)[0]
                method = "stochastic_near_top"
                
            # Detect ambivalence
            hesitation = False
            if len(top_candidates) > 1:
                actions = [c.action for c in top_candidates]
                if ("surrender" in actions and "threaten" in actions) or \
                   ("fully_disclose" in actions and "lie" in actions):
                    hesitation = True
                    
            return BehavioralDecision(
                candidates=evaluated,
                selected=selected,
                selection_method=method,
                hesitation=hesitation
            )
            
        except Exception as e:
            # Fallback behavior - deterministic safe output
            print(f"Behavioral Policy Exception: {e}")
            fallback = BehavioralCandidate(
                action="remain_silent",
                intensity=0.5,
                score=0.0,
                rationale="Fallback due to policy error."
            )
            return BehavioralDecision(
                candidates=[fallback],
                selected=fallback,
                selection_method="fallback",
                hesitation=False
            )
