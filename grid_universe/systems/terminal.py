from dataclasses import replace

from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.terminal import is_terminal_state, is_valid_state


def win_system(state: State, agent_id: EntityID) -> State:
    """Sets state.win = True if the agent satisfies the objective function.
    Does nothing if the state is already terminal or the agent is missing/dead.
    """
    if not is_valid_state(state, agent_id) or is_terminal_state(state, agent_id):
        return state

    if state.objective_fn(state, agent_id):
        return replace(state, win=True)
    return state


def lose_system(state: State, agent_id: EntityID) -> State:
    """Sets state.lose = True if the agent is dead."""
    if agent_id in state.dead and not state.lose:
        return replace(state, lose=True)
    return state
