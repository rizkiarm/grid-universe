from dataclasses import replace

from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.ecs import entities_with_components_at
from grid_universe.utils.grid import compute_destination, is_blocked_at


def push_system(state: State, eid: EntityID, next_pos: Position) -> State:
    """Handles an entity trying to push a pushable object located at next_pos (adjacent cell).
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
    push_to = compute_destination(state, current_pos, next_pos)
    if push_to is None:
        return state

    if is_blocked_at(state, push_to, check_collidable=True):
        return state  # Push not possible

    new_position = state.position.set(pushable_id, push_to).set(eid, next_pos)
    return replace(state, position=new_position)
