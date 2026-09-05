# Phase 10: Persistent Experience & Learning Audit

## What is Currently Implemented
1. **Subject-Level State & Memory (Phases 1-3)**
   - `PsychologicalState` (Fear, anger, etc.) changes deterministically.
   - `RelationshipState` (Trust, respect) tracks changes over the negotiation.
   - `BeliefEngine` handles confidence/tension and resistance to contradictory evidence.
   - `MemoryStore` stores episodic and semantic facts.
2. **Subject-Level Strategy Learning (Phase 5)**
   - `StrategyHistory` tracks past `StrategyRecord`s and whether they were "effective/ineffective/counterproductive". 
   - `BehavioralPolicyEngine` uses this to adjust scores (e.g. penalized if a strategy was recently ineffective).
3. **Observability (Phase 8)**
   - `TurnTrace` captures inputs, outputs, states, and latencies across the pipeline.

## What is Missing (The Delta)
1. **ExperienceStore Persistence**: Right now, `TurnTrace` and `StrategyHistory` are in-memory schemas. There is no SQLite/JSON-lines permanent disk persistence capturing cross-session global experience for asynchronous calibration.
2. **System-Level Learning**: There is no mechanism to aggregate 10,000 negotiations, spot that the `AppraisalEngine` constantly overestimates intent, and calibrate it.
3. **Outcome Signalling**: There is no formal `OutcomeSignal` or post-negotiation credit assignment loop.
4. **Subject-Level Cross-Session Memory**: While relationships and beliefs adapt within a session, the long-term "negotiator A is a liar" vs "negotiator B keeps promises" tracking is implicitly handled by generic Beliefs, which is fine, but there is no offline consolidation of this across multiple runs.

## Proposed Minimal Extension
To fulfill the requirements without adding GPU or deep-learning training loops:
1. **`ExperienceStore` (SQLite)**: A local lightweight database capturing `SessionExperience`, `TurnExperience`, and `OutcomeSignal`.
2. **`OutcomeEvaluator`**: A lightweight system that takes a completed session, assigns success/failure, and backpropagates "effectiveness" into the `StrategyHistory` and globally.
3. **`LearningCalibrationEngine`**: An offline/asynchronous statistical component that:
   - Reads the `ExperienceStore`.
   - Aggregates "expected vs actual" negotiator responses.
   - Adjusts Bayesian priors (e.g. modifying default BehavioralPolicy scoring weights) without touching raw LLM weights.
   - Versions these learned parameters (e.g. `calibration_v2.json`).
