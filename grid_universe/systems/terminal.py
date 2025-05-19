from dataclasses import replace
from grid_universe.state import State
from grid_universe.types import EntityID


def win_system(state: State, agent_id: EntityID) -> State:
    if agent_id in state.dead or len(state.agent) == 0:
        return state

    agent_pos = state.position.get(agent_id)
    if agent_pos is None or state.win:
        return state

    if state.objective_fn(state, agent_id):
        return replace(state, win=True)
    return state


def lose_system(state: State, agent_id: EntityID) -> State:
    """
    Sets state.lose = True if the agent is dead.
    """
    if agent_id in state.dead and not state.lose:
        return replace(state, lose=True)
    return state
