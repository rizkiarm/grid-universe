from grid_universe.state import State
from grid_universe.types import EntityID


def is_valid_state(state: State, agent_id: EntityID) -> bool:
    return len(state.agent) > 0 and state.position.get(agent_id) is not None


def is_terminal_state(state: State, agent_id: EntityID) -> bool:
    return state.win or state.lose or agent_id in state.dead
