"""Grid math / collision helpers.

Utility predicates used by movement & push systems. Functions here are pure
and intentionally lightweight to keep inner loops fast.
"""

from typing import Optional
from grid_universe.components import Position
from grid_universe.moves import wrap_around_move_fn
from grid_universe.state import State


def is_in_bounds(state: State, pos: Position) -> bool:
    """Return True if ``pos`` lies within the level rectangle."""
    return 0 <= pos.x < state.width and 0 <= pos.y < state.height


def wrap_position(x: int, y: int, width: int, height: int) -> Position:
    """Toroidal wrap for coordinates (used by wrap movement)."""
    return Position(x % width, y % height)


def is_blocked_at(state: State, pos: Position, check_collidable: bool = True) -> bool:
    """Return True if any blocking entity occupies ``pos``.

    Arguments:
        state: World state.
        pos: Candidate destination.
        check_collidable: If True, treat Collidable as blocking (for agent movement);
            pushing may disable this to allow pushing into collidable tiles.
    """
    for other_id, other_pos in state.position.items():
        if other_pos == pos and (
            other_id in state.blocking
            or other_id in state.pushable
            or (check_collidable and other_id in state.collidable)
        ):
            return True
    return False


def compute_destination(
    state: State, current_pos: Position, next_pos: Position
) -> Optional[Position]:
    """Compute push destination given current and occupant next positions.

    Returns the square beyond ``next_pos`` in the movement direction, applying
    wrap logic if the state's move function is the wrapping one. ``None`` if
    outside bounds and not wrapping.
    """
    dx = next_pos.x - current_pos.x
    dy = next_pos.y - current_pos.y
    dest_x = next_pos.x + dx
    dest_y = next_pos.y + dy

    if state.move_fn is wrap_around_move_fn:
        return wrap_position(dest_x, dest_y, state.width, state.height)

    target_position = Position(dest_x, dest_y)
    if not is_in_bounds(state, target_position):
        return None

    return target_position
