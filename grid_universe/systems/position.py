"""Position snapshot system.

Maintains ``prev_position`` as an immutable snapshot of all entity positions
at the start (or end) of a step. Other systems (e.g. portal teleportation,
trail generation, damage-on-crossing) rely on this historical information to
detect transitions or movement paths.
"""

from dataclasses import replace
from typing import Dict

from pyrsistent import pmap
from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID


def position_system(state: State) -> State:
    """Snapshot current entity positions.

    Args:
        state (State): Current immutable simulation state.

    Returns:
        State: New state with ``prev_position`` replaced by a pmap copy of the
            current ``position`` mapping.
    """
    prev_position: Dict[EntityID, Position] = {}
    for eid, pos in state.position.items():
        prev_position[eid] = pos
    return replace(state, prev_position=pmap(prev_position))
