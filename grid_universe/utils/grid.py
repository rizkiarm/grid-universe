"""Grid math / collision helpers.

Utility predicates used by movement & push systems. Functions here are pure
and intentionally lightweight to keep inner loops fast.
"""

from typing import Set
from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.ecs import entities_at


def is_in_bounds(state: State, pos: Position) -> bool:
    """Return True if ``pos`` lies within the level rectangle."""
    return 0 <= pos.x < state.width and 0 <= pos.y < state.height


def wrap_position(x: int, y: int, width: int, height: int) -> Position:
    """Toroidal wrap for coordinates (used by wrap movement)."""
    return Position(x % width, y % height)


def is_blocked_at(
    state: State,
    pos: Position,
    check_collidable: bool = True,
    check_pushable: bool = True,
) -> bool:
    """Return True if any blocking entity occupies ``pos``.

    Args:
        state (State): World state.
        pos (Position): Candidate destination.
        check_collidable (bool): If True, treat ``Collidable`` as blocking (for agent movement);
            pushing may disable this to allow pushing into collidable tiles.
    """
    ids_at_pos: Set[EntityID] = entities_at(state, pos)
    for other_id in ids_at_pos:
        if (
            other_id in state.blocking
            or (check_pushable and other_id in state.pushable)
            or (check_collidable and other_id in state.collidable)
        ):
            return True
    return False
