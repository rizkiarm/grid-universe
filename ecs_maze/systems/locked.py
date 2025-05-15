from dataclasses import replace
from ecs_maze.components import Position
from ecs_maze.state import State
from ecs_maze.types import EntityID
from ecs_maze.utils.ecs import entities_with_components_at
from ecs_maze.utils.inventory import has_key_with_id, remove_item


def unlock_system(state: State, eid: EntityID, next_pos: Position) -> State:
    """
    Handles unlocking logic for ALL locked entities at next_pos.
    Removes the Locked component for each if the correct key is in inventory (single-use).
    """
    locked_ids = entities_with_components_at(state, next_pos, state.locked)
    if not locked_ids:
        return state

    inv = state.inventory.get(eid)
    if inv is None:
        return state  # No inventory, can't unlock

    new_locked = state.locked
    new_blocking = state.blocking
    new_inventory = state.inventory
    new_key = state.key
    current_inv = inv

    for locked_id in locked_ids:
        locked_comp = state.locked[locked_id]
        key_found = has_key_with_id(current_inv, state.key, locked_comp.key_id)
        if key_found is not None:
            # Remove Locked and Blocking component (if any)
            new_locked = new_locked.remove(locked_id)
            if locked_id in new_blocking:
                new_blocking = new_blocking.remove(locked_id)
            # Remove key from inventory and key store
            current_inv = remove_item(current_inv, key_found)
            new_key = new_key.remove(key_found) if key_found in new_key else new_key

    # Update inventory in state if changed
    if current_inv != inv:
        new_inventory = new_inventory.set(eid, current_inv)

    return replace(
        state,
        locked=new_locked,
        blocking=new_blocking,
        inventory=new_inventory,
        key=new_key,
    )
