from typing import Dict
from grid_universe.state import State
from grid_universe.types import EntityID, ObjectiveFn
from grid_universe.utils.ecs import entities_with_components_at


def default_objective_fn(state: State, agent_id: EntityID) -> bool:
    return collect_required_objective_fn(state, agent_id) and exit_objective_fn(
        state, agent_id
    )


def exit_objective_fn(state: State, agent_id: EntityID) -> bool:
    if agent_id not in state.position:
        return False
    return (
        len(entities_with_components_at(state, state.position[agent_id], state.exit))
        > 0
    )


def collect_required_objective_fn(state: State, agent_id: EntityID) -> bool:
    return all((eid not in state.collectible) for eid in state.required)


def all_unlocked_objective_fn(state: State, agent_id: EntityID) -> bool:
    return len(state.locked) == 0


def all_pushable_at_exit_objective_fn(state: State, agent_id: EntityID) -> bool:
    for pushable_id in state.pushable:
        if pushable_id not in state.position:
            return False
        if (
            len(
                entities_with_components_at(
                    state, state.position[pushable_id], state.exit
                )
            )
            == 0
        ):
            return False
    return True


OBJECTIVE_FN_REGISTRY: Dict[str, ObjectiveFn] = {
    "default": default_objective_fn,
    "exit": exit_objective_fn,
    "collect": collect_required_objective_fn,
    "unlock": all_unlocked_objective_fn,
    "push": all_pushable_at_exit_objective_fn,
}
