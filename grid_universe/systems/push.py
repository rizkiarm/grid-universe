from dataclasses import replace
from grid_universe.moves import wrap_around_move_fn
from grid_universe.state import State
from grid_universe.components import Position
from grid_universe.types import EntityID
from grid_universe.utils.ecs import entities_with_components_at


def wrap_position(x: int, y: int, width: int, height: int) -> Position:
    return Position(x % width, y % height)


def push_system(state: State, eid: EntityID, next_pos: Position) -> State:
    """
    Handles an entity trying to push a pushable object located at next_pos (adjacent cell).
    Computes push direction vector automatically.
    """
    current_pos = state.position.get(eid)
    if current_pos is None:
        return state

    # Is there a pushable object at next_pos?
    pushable_ids = entities_with_components_at(state, next_pos, state.pushable)
    if not pushable_ids:
        return state  # Nothing to push

    pushable_id = pushable_ids[0]

    # Compute push vector and target position for the pushed object
    dx = next_pos.x - current_pos.x
    dy = next_pos.y - current_pos.y
    push_to = Position(next_pos.x + dx, next_pos.y + dy)
    push_to = Position(next_pos.x + dx, next_pos.y + dy)

    # Only wrap if using wrap_around_move_fn
    if state.move_fn is wrap_around_move_fn:
        push_to = wrap_position(
            next_pos.x + dx, next_pos.y + dy, state.width, state.height
        )
    else:
        push_to = Position(next_pos.x + dx, next_pos.y + dy)
        # Out-of-bounds check for default and non-wrap
        if not (0 <= push_to.x < state.width and 0 <= push_to.y < state.height):
            return state

    # Check for blocking at destination
    blocked = False
    for other_id, other_pos in state.position.items():
        if other_pos == push_to and (
            other_id in state.blocking
            or other_id in state.pushable
            or other_id in state.collidable
        ):
            blocked = True
            break

    if blocked:
        return state  # Push not possible

    # Update both the pusher's and the pushable's positions using PMap
    new_position = state.position.set(pushable_id, push_to).set(eid, next_pos)
    return replace(state, position=new_position)
