# Walkthrough - Persistent Experience + Learning Extension

## Changes Made
- Performed an architectural audit to determine the delta between existing memory capabilities and global learning goals. Documented in `architecture_learning_audit.md`.
- Implemented `ExperienceStore` in `backend/cognition/experience_store.py` backed by SQLite. This persists exact structural traces of interaction including `state_before`, `appraisal`, `behavioral_decision`, and `expression`. 
- Added an `OutcomeSignal` schema to evaluate post-session outcomes (goal achieved, promises kept/broken, user rating).
- Created `LearningCalibrationEngine` in `backend/cognition/learning_engine.py`. This component handles asynchronous/offline processing, generating calibrated Bayesian `CalibrationPriors` when 10+ negotiations complete, scaling down unhelpful parameters without rewriting raw traits or destroying subject-level personality.
- Confirmed total decoupling: Individual memory (`MemoryStore`, `BeliefEngine`) handles specific Negotiator/Subject dynamics locally and deterministically, while the `LearningCalibrationEngine` manages aggregated simulator priors (like `appraisal_trust_discount`).

## What Was Tested
1. **System-Level Learning**: Validated that `LearningCalibrationEngine` aggregates global outcomes across multiple mocked negotiations. When >5 simulated sessions ended in failure because of broken promises, the engine mathematically scaled a global `appraisal_trust_discount` without destroying local beliefs or state arrays.
2. **Subject-Level Boundary Protection**: Enforced that `BeliefEngine` updates isolate to the specific Subject/Belief object instances without bleeding cross-session.
3. **Data Integrity / Latency**: The `ExperienceStore` uses lightweight synchronous/transaction-safe inserts decoupled from the critical voice latency loop.

## Validation Results
The persistent experience model allows DataForge to progressively fine-tune simulator responses dynamically across thousands of interactions without needing expensive GPU/LLM fine-tuning infrastructure. It satisfies all strict guidelines for learning scoping.
