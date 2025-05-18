from dataclasses import replace
from grid_universe.state import State
from grid_universe.types import EntityID


def win_system(state: State, agent_id: EntityID) -> State:
    if agent_id in state.dead or len(state.agent) == 0:
        return state

    agent_pos = state.position.get(agent_id)
    if agent_pos is None or state.win:
        return state

    # Agent must be at an exit
    at_exit = any(
        pos == agent_pos for eid, pos in state.position.items() if eid in state.exit
    )
    # All required items collected? (i.e., no RequiredItem entities left on the map)
    all_required_collected = all(
        (eid not in state.collectible) for eid in state.required
    )

    if at_exit and all_required_collected:
        return replace(state, win=True)
    return state


def lose_system(state: State, agent_id: EntityID) -> State:
    """
    Sets state.lose = True if the agent is dead.
    """
    if agent_id in state.dead and not state.lose:
        return replace(state, lose=True)
    return state
