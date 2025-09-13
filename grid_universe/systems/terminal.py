"""Terminal condition systems.

Defines win/lose evaluation utilities that set ``state.win`` or ``state.lose``
flags exactly once when conditions are met (objective success or agent death).
These flags are side-channel indicators—other systems may short-circuit when
the state is already terminal.
"""

from dataclasses import replace
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.terminal import is_terminal_state, is_valid_state


def win_system(state: State, agent_id: EntityID) -> State:
    """Set ``win`` flag if objective function returns True for agent.

    Skips evaluation if state already terminal or agent invalid/dead.
    """
    if not is_valid_state(state, agent_id) or is_terminal_state(state, agent_id):
        return state

    if state.objective_fn(state, agent_id):
        return replace(state, win=True)
    return state


def lose_system(state: State, agent_id: EntityID) -> State:
    """Set ``lose`` flag if agent is dead (idempotent)."""
    if agent_id in state.dead and not state.lose:
        return replace(state, lose=True)
    return state
