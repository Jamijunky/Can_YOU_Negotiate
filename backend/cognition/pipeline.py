import time
import uuid
import traceback
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field

from cognition.schemas import (
    HumanModel, PsychologicalState, RelationshipState, SituationModel, Belief, GoalState, WorldState,
    StrategyHistory
)
from cognition.appraisal_engine import AppraisalEngine, CognitiveAppraisal
from cognition.state_engine import apply_state_transition
from cognition.belief_engine import update_belief, update_situation, handle_commitment
from cognition.relationship_engine import update_relationship
from cognition.behavioral_policy import BehavioralPolicyEngine, BehavioralDecision
from cognition.world_engine import update_world
from cognition.expression_engine import ExpressionEngine, ExpressionHistory, ExpressionResult
from cognition.speech_generator import SpeechGenerator, SpeechGenerationResult

class TurnTrace(BaseModel):
    turn_id: str
    timestamp: float
    input_transcript: str
    latencies_ms: Dict[str, float] = Field(default_factory=dict)
    
    appraisal: Optional[CognitiveAppraisal] = None
    state_delta: Dict[str, float] = Field(default_factory=dict)
    
    behavioral_decision: Optional[BehavioralDecision] = None
    expression: Optional[Dict[str, float]] = None
    
    generated_speech: Optional[str] = None
    confidence: float = 0.0
    
    # Authoritative World State Observability
    world_state: Optional[Dict[str, Any]] = None
    world_updates: list[dict] = Field(default_factory=list)
    
    error: Optional[str] = None
    fallback_used: bool = False

class CognitivePipeline:
    def __init__(
        self,
        appraisal_engine: AppraisalEngine,
        policy_engine: BehavioralPolicyEngine,
        expression_engine: ExpressionEngine,
        speech_generator: SpeechGenerator
    ):
        self.appraisal_engine = appraisal_engine
        self.policy_engine = policy_engine
        self.expression_engine = expression_engine
        self.speech_generator = speech_generator

    def process_turn(
        self,
        input_transcript: str,
        human: HumanModel,
        state: PsychologicalState,
        rel: RelationshipState,
        situation: SituationModel,
        beliefs: list[Belief],
        goals: GoalState,
        strategy_history: StrategyHistory,
        expression_history: ExpressionHistory,
        recent_context: list[str],
        world: Optional[WorldState] = None
    ) -> Tuple[SpeechGenerationResult, TurnTrace]:
        
        world = world or WorldState()
        trace = TurnTrace(
            turn_id=str(uuid.uuid4()),
            timestamp=time.time(),
            input_transcript=input_transcript,
            world_state=world.model_dump()
        )
        total_start = time.perf_counter()
        
        try:
            # 1. Appraisal
            start = time.perf_counter()
            appraisal = self.appraisal_engine.appraise(
                event=input_transcript,
                human=human,
                state=state,
                relationship=rel,
                beliefs=beliefs,
                situation=situation,
                recent_context=recent_context
            )
            trace.latencies_ms["appraisal"] = (time.perf_counter() - start) * 1000
            trace.appraisal = appraisal
            
            # Record state before
            s_fear_before = state.fear
            s_anger_before = state.anger
            
            # 1.5 World Update
            start = time.perf_counter()
            world_meta_log = []
            for w_sig in getattr(appraisal, 'world_updates', []):
                world, w_meta = update_world(world, w_sig)
                world_meta_log.append(w_meta)
            trace.world_updates = world_meta_log
            trace.world_state = world.model_dump()
            trace.latencies_ms["world_update"] = (time.perf_counter() - start) * 1000
            
            # 2. State Update
            start = time.perf_counter()
            state, _ = apply_state_transition(state, human.personality, appraisal.state_updates)
            trace.latencies_ms["state_update"] = (time.perf_counter() - start) * 1000
            
            trace.state_delta = {
                "fear": state.fear - s_fear_before,
                "anger": state.anger - s_anger_before
            }
            
            # 3. Belief Update
            start = time.perf_counter()
            beliefs_dict = {b.id: b for b in beliefs}
            for b_sig in appraisal.belief_updates:
                b = beliefs_dict.get(b_sig.belief_id)
                if b:
                    updated_b, _ = update_belief(b, b_sig, beliefs_dict)
                    beliefs_dict[b.id] = updated_b
                    # also replace in beliefs list
                    for i, old_b in enumerate(beliefs):
                        if old_b.id == b.id:
                            beliefs[i] = updated_b
            for s_sig in appraisal.situation_updates:
                situation, _ = update_situation(situation, s_sig)
            trace.latencies_ms["belief_update"] = (time.perf_counter() - start) * 1000
            
            # 4. Relationship Update
            start = time.perf_counter()
            rel, _ = update_relationship(rel, appraisal.relationship_updates)
            trace.latencies_ms["relationship_update"] = (time.perf_counter() - start) * 1000
            
            # 5. Behavioral Policy
            start = time.perf_counter()
            decision = self.policy_engine.select_action(
                human=human, state=state, relationship=rel, situation=situation,
                beliefs=beliefs, history=strategy_history, world=world
            )
            trace.latencies_ms["behavioral_policy"] = (time.perf_counter() - start) * 1000
            trace.behavioral_decision = decision
            
            # 6. Expression
            start = time.perf_counter()
            expr_result = self.expression_engine.generate_expression(human, state, rel, decision, expression_history)
            trace.latencies_ms["expression"] = (time.perf_counter() - start) * 1000
            trace.expression = expr_result.expression.model_dump()
            
            # 7. Speech Generation
            start = time.perf_counter()
            speech_result = self.speech_generator.generate(
                human, state, rel, decision, expr_result.expression, beliefs, situation, world, recent_context
            )
            trace.latencies_ms["speech_generation"] = (time.perf_counter() - start) * 1000
            
            trace.generated_speech = speech_result.spoken_text
            trace.confidence = speech_result.confidence
            
            if speech_result.confidence == 0.0:
                trace.fallback_used = True
                
        except Exception as e:
            trace.error = str(e) + "\n" + traceback.format_exc()
            trace.fallback_used = True
            speech_result = SpeechGenerationResult(spoken_text="...", confidence=0.0, behavioral_fidelity=0.0)
            trace.generated_speech = speech_result.spoken_text
            
        trace.latencies_ms["total_turn"] = (time.perf_counter() - total_start) * 1000
        return speech_result, trace
