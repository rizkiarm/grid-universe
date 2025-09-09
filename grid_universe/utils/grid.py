
from grid_universe.components import Position
from grid_universe.moves import wrap_around_move_fn
from grid_universe.state import State


def is_in_bounds(state: State, pos: Position) -> bool:
    return 0 <= pos.x < state.width and 0 <= pos.y < state.height


def wrap_position(x: int, y: int, width: int, height: int) -> Position:
    return Position(x % width, y % height)


def is_blocked_at(state: State, pos: Position, check_collidable: bool = True) -> bool:
    """Returns True if the position is blocked (blocking, pushable, or collidable)."""
    for other_id, other_pos in state.position.items():
        if other_pos == pos and (
            other_id in state.blocking
            or other_id in state.pushable
            or (check_collidable and other_id in state.collidable)
        ):
            return True
    return False


def compute_destination(
    state: State, current_pos: Position, next_pos: Position,
) -> Position | None:
    """Compute where an entity would move from `current_pos` to `next_pos`."""
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
