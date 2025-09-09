import random
from collections.abc import Sequence

from grid_universe.actions import Action
from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID, MoveFn


def default_move_fn(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    pos = state.position[eid]
    dx, dy = {
        Action.UP: (0, -1),
        Action.DOWN: (0, 1),
        Action.LEFT: (-1, 0),
        Action.RIGHT: (1, 0),
    }[action]
    return [Position(pos.x + dx, pos.y + dy)]


def wrap_around_move_fn(
    state: State, eid: EntityID, action: Action,
) -> Sequence[Position]:
    pos = state.position[eid]
    dx, dy = {
        Action.UP: (0, -1),
        Action.DOWN: (0, 1),
        Action.LEFT: (-1, 0),
        Action.RIGHT: (1, 0),
    }[action]
    width = getattr(state, "width", None)
    height = getattr(state, "height", None)
    if width is None or height is None:
        msg = "State must have width and height for wrap_around_move_fn."
        raise ValueError(msg)
    new_x = (pos.x + dx) % width
    new_y = (pos.y + dy) % height
    return [Position(new_x, new_y)]


def mirror_move_fn(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    mirror_map: dict[Action, Action] = {
        Action.LEFT: Action.RIGHT,
        Action.RIGHT: Action.LEFT,
        Action.UP: Action.UP,
        Action.DOWN: Action.DOWN,
    }
    mirrored = mirror_map[action]
    return default_move_fn(state, eid, mirrored)


def slippery_move_fn(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    pos = state.position[eid]
    dx, dy = {
        Action.UP: (0, -1),
        Action.DOWN: (0, 1),
        Action.LEFT: (-1, 0),
        Action.RIGHT: (1, 0),
    }[action]
    width, height = state.width, state.height
    nx, ny = pos.x + dx, pos.y + dy
    path: list[Position] = []
    while 0 <= nx < width and 0 <= ny < height:  # Prevents infinite loop at grid edge
        test_pos = Position(nx, ny)
        blocked = False
        for oid, o_pos in state.position.items():
            if o_pos == test_pos and oid in state.blocking:
                blocked = True
                break
        if blocked:
            break
        path.append(test_pos)
        nx += dx
        ny += dy
    return path if path else [pos]


def windy_move_fn(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    pos = state.position[eid]
    dx, dy = {
        Action.UP: (0, -1),
        Action.DOWN: (0, 1),
        Action.LEFT: (-1, 0),
        Action.RIGHT: (1, 0),
    }[action]
    width, height = state.width, state.height
    path: list[Position] = []
    # First move
    nx1, ny1 = pos.x + dx, pos.y + dy
    if 0 <= nx1 < width and 0 <= ny1 < height:
        path.append(Position(nx1, ny1))
        # Wind effect
        if random.random() < 0.3:
            wind_dx, wind_dy = random.choice([(0, -1), (0, 1), (-1, 0), (1, 0)])
            nx2, ny2 = nx1 + wind_dx, ny1 + wind_dy
            if 0 <= nx2 < width and 0 <= ny2 < height:
                path.append(Position(nx2, ny2))
    # If the first move is out of bounds, wind does not apply.
    return path if path else [pos]


def gravity_move_fn(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    pos = state.position[eid]
    dx, dy = {
        Action.UP: (0, -1),
        Action.DOWN: (0, 1),
        Action.LEFT: (-1, 0),
        Action.RIGHT: (1, 0),
    }[action]
    width, height = state.width, state.height
    nx, ny = pos.x + dx, pos.y + dy

    def can_move(px: int, py: int) -> bool:
        # Out-of-bounds check
        if not (0 <= px < width and 0 <= py < height):
            return False
        test_pos = Position(px, py)
        for oid, o_pos in state.position.items():
            if o_pos == test_pos and oid in state.blocking:
                return False
        return True

    if not can_move(nx, ny):
        return [pos]

    path: list[Position] = [Position(nx, ny)]
    while True:
        next_x, next_y = nx, path[-1].y + 1
        if not can_move(next_x, next_y):
            break
        path.append(Position(next_x, next_y))
    return path


# Move function registry for per-level assignment
MOVE_FN_REGISTRY: dict[str, MoveFn] = {
    "default": default_move_fn,
    "wrap": wrap_around_move_fn,
    "mirror": mirror_move_fn,
    "slippery": slippery_move_fn,
    "windy": windy_move_fn,
    "gravity": gravity_move_fn,
}
