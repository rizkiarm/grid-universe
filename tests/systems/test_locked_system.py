from dataclasses import replace
from grid_universe.systems.locked import unlock_system
from grid_universe.types import EntityID
from grid_universe.state import State
from grid_universe.components import Position, Blocking, Key, Locked, Door, Inventory
from pyrsistent import PSet, pset
from tests.test_utils import make_minimal_key_door_state


def add_key_to_inventory(state: State, agent_id: EntityID, key_id: EntityID) -> State:
    inv: Inventory = state.inventory[agent_id]
    new_inv: Inventory = Inventory(item_ids=inv.item_ids.add(key_id))
    return replace(state, inventory=state.inventory.set(agent_id, new_inv))


def remove_inventory(state: State, agent_id: EntityID) -> State:
    return replace(state, inventory=state.inventory.remove(agent_id))


def set_inventory(state: State, agent_id: EntityID, item_ids: PSet[EntityID]) -> State:
    return replace(
        state, inventory=state.inventory.set(agent_id, Inventory(item_ids=item_ids))
    )


def add_door_with_lock(
    state: State, door_id: EntityID, pos: Position, key_id_str: str
) -> State:
    new_state: State = replace(
        state,
        door=state.door.set(door_id, Door()),
        locked=state.locked.set(door_id, Locked(key_id=key_id_str)),
        blocking=state.blocking.set(door_id, Blocking()),
        position=state.position.set(door_id, pos),
    )
    return new_state


def add_key_entity(state: State, key_id: EntityID, key_id_str: str) -> State:
    return replace(state, key=state.key.set(key_id, Key(key_id=key_id_str)))


def test_unlock_system_no_inventory_does_nothing() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    door_id: EntityID = entities["door_id"]
    state_no_inv: State = remove_inventory(state, agent_id)
    new_state: State = unlock_system(state_no_inv, agent_id, Position(0, 2))
    assert door_id in new_state.locked
    assert door_id in new_state.blocking


def test_unlock_system_inventory_empty_does_nothing() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    door_id: EntityID = entities["door_id"]
    state_empty_inv: State = set_inventory(state, agent_id, pset())
    new_state: State = unlock_system(state_empty_inv, agent_id, Position(0, 2))
    assert door_id in new_state.locked
    assert door_id in new_state.blocking


def test_unlock_system_multiple_locks_with_enough_keys() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    door_id: EntityID = entities["door_id"]
    door2_id: EntityID = door_id + 100
    key2_id: EntityID = key_id + 100
    keyid_str: str = state.locked[door_id].key_id
    pos: Position = Position(0, 2)
    # Add new key and second door
    state2: State = add_key_entity(state, key2_id, keyid_str)
    state2 = add_door_with_lock(state2, door2_id, pos, keyid_str)
    # Add both keys to inventory
    prev_ids: PSet[EntityID] = state2.inventory[agent_id].item_ids
    state2 = set_inventory(state2, agent_id, prev_ids.add(key_id).add(key2_id))
    new_state: State = unlock_system(state2, agent_id, pos)
    assert door_id not in new_state.locked
    assert door2_id not in new_state.locked
    assert key_id not in new_state.inventory[agent_id].item_ids
    assert key2_id not in new_state.inventory[agent_id].item_ids


def test_unlock_system_multiple_locks_only_one_key() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    door_id: EntityID = entities["door_id"]
    door2_id: EntityID = door_id + 200
    keyid_str: str = state.locked[door_id].key_id
    pos: Position = Position(0, 2)
    state2: State = add_door_with_lock(state, door2_id, pos, keyid_str)
    # Only one matching key in inventory
    prev_ids: PSet[EntityID] = state2.inventory[agent_id].item_ids
    state2 = set_inventory(state2, agent_id, prev_ids.add(key_id))
    new_state: State = unlock_system(state2, agent_id, pos)
    unlocked_count: int = int(door_id not in new_state.locked) + int(
        door2_id not in new_state.locked
    )
    assert unlocked_count == 1
    assert key_id not in new_state.inventory[agent_id].item_ids


def test_unlock_system_key_in_inventory_not_in_key_store() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    door_id: EntityID = entities["door_id"]
    phantom_key_id: EntityID = key_id + 999
    # Add phantom key to inventory (not present in state.key)
    prev_ids: PSet[EntityID] = state.inventory[agent_id].item_ids
    state_phantom: State = set_inventory(state, agent_id, prev_ids.add(phantom_key_id))
    new_state: State = unlock_system(state_phantom, agent_id, Position(0, 2))
    assert door_id in new_state.locked
    assert phantom_key_id in new_state.inventory[agent_id].item_ids


def test_unlock_system_lock_with_empty_keyid() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    door_id: EntityID = entities["door_id"]
    empty_key_eid: EntityID = key_id + 500
    # Add empty key entity and update lock to require it
    state2: State = add_key_entity(state, empty_key_eid, "")
    state2 = replace(state2, locked=state2.locked.set(door_id, Locked(key_id="")))
    prev_ids: PSet[EntityID] = state2.inventory[agent_id].item_ids
    state2 = set_inventory(state2, agent_id, prev_ids.add(empty_key_eid))
    new_state: State = unlock_system(state2, agent_id, Position(0, 2))
    # Should unlock if logic allows empty key_id match
    assert door_id not in new_state.locked


def test_unlock_system_lock_missing_blocking() -> None:
    state, entities = make_minimal_key_door_state()
    agent_id: EntityID = entities["agent_id"]
    key_id: EntityID = entities["key_id"]
    door_id: EntityID = entities["door_id"]
    blocking = state.blocking
    if door_id in blocking:
        blocking = blocking.remove(door_id)
    state2: State = replace(state, blocking=blocking)
    state2 = add_key_to_inventory(state2, agent_id, key_id)
    new_state: State = unlock_system(state2, agent_id, Position(0, 2))
    assert door_id not in new_state.locked
    # (blocking missing is fine, should not raise)


def test_unlock_system_multiple_keys_same_keyid():
    state, entities = make_minimal_key_door_state()
    agent_id = entities["agent_id"]
    key_id = entities["key_id"]
    door_id = entities["door_id"]
    keyid_str = state.locked[door_id].key_id
    # Add a second key entity with the same key_id
    key2_id = key_id + 101
    state2 = add_key_entity(state, key2_id, keyid_str)
    prev_ids = state2.inventory[agent_id].item_ids
    state2 = set_inventory(state2, agent_id, prev_ids.add(key_id).add(key2_id))
    # Add two doors at same pos, need same key_id
    door2_id = door_id + 201
    pos = Position(0, 2)
    state2 = add_door_with_lock(state2, door2_id, pos, keyid_str)
    new_state = unlock_system(state2, agent_id, pos)
    # Both locks should be unlocked, both keys consumed
    assert door_id not in new_state.locked
    assert door2_id not in new_state.locked
    assert key_id not in new_state.inventory[agent_id].item_ids
    assert key2_id not in new_state.inventory[agent_id].item_ids


def test_unlock_system_multiple_locks_different_keyids_one_match():
    state, entities = make_minimal_key_door_state()
    agent_id = entities["agent_id"]
    key_id = entities["key_id"]
    door_id = entities["door_id"]
    # Add a second key and door with a different key_id
    key2_id = key_id + 300
    door2_id = door_id + 300
    state2 = add_key_entity(state, key2_id, "different")
    state2 = add_door_with_lock(state2, door2_id, Position(0, 2), "different")
    # Give agent only the base key, not the "different" one
    prev_ids = state2.inventory[agent_id].item_ids
    state2 = set_inventory(state2, agent_id, prev_ids.add(key_id))
    new_state = unlock_system(state2, agent_id, Position(0, 2))
    # Only the matching lock should be unlocked
    assert door_id not in new_state.locked
    assert door2_id in new_state.locked
    assert key_id not in new_state.inventory[agent_id].item_ids
