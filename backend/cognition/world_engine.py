from typing import Tuple, Dict, Any
from cognition.schemas import WorldState, WorldUpdateSignal

def update_world(state: WorldState, signal: WorldUpdateSignal) -> Tuple[WorldState, Dict[str, Any]]:
    """
    Authoritatively updates the world state based on proposed signals.
    Validates against reality constraints.
    """
    # Clone state for determinism
    resources = {k: v.model_copy() for k, v in state.resources.items()}
    capabilities = {k: v.model_copy() for k, v in state.capabilities.items()}
    constraints = dict(state.constraints)
    
    metadata = {"status": "rejected", "reason": "unknown"}

    if signal.action == "transfer":
        if signal.object_id in resources:
            res = resources[signal.object_id]
            # Verify the actor actually holds it
            if res.holder == signal.actor and res.available:
                res.holder = signal.target
                metadata = {"status": "accepted", "reason": "resource transferred"}
                
                # Check capability unlocks
                if signal.object_id == "walkie_talkie" and signal.target == "subject":
                    if "subject_can_use_walkie_talkie" in capabilities:
                        capabilities["subject_can_use_walkie_talkie"].enabled = True
            else:
                metadata = {"status": "rejected", "reason": f"actor {signal.actor} does not hold resource"}
        else:
            metadata = {"status": "rejected", "reason": f"resource {signal.object_id} does not exist in authoritative world"}

    elif signal.action == "consume":
        if signal.object_id in resources:
            res = resources[signal.object_id]
            if res.holder == signal.actor and res.available:
                res.available = False
                metadata = {"status": "accepted", "reason": "resource consumed"}
            else:
                metadata = {"status": "rejected", "reason": "cannot consume"}
        else:
            metadata = {"status": "rejected", "reason": "does not exist"}

    elif signal.action == "claim":
        # Negotiator merely claims something exists. We do NOT create it in authoritative reality.
        # This belongs in Beliefs, not here. We actively reject it from reality mutation.
        metadata = {"status": "rejected", "reason": "claim does not mutate reality"}

    new_state = WorldState(
        resources=resources,
        capabilities=capabilities,
        constraints=constraints
    )
    
    return new_state, metadata
