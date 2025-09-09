# tests/utils/test_inventory.py

from pyrsistent import pset

from grid_universe.components import Inventory, Key
from grid_universe.types import EntityID
from grid_universe.utils.inventory import (
    add_item,
    all_keys_with_id,
    has_key_with_id,
    remove_item,
)


def test_add_and_remove_item() -> None:
    inv = Inventory(item_ids=pset())
    key_id: EntityID = 101
    # Add item
    inv2 = add_item(inv, key_id)
    assert key_id in inv2.item_ids
    # Remove item
    inv3 = remove_item(inv2, key_id)
    assert key_id not in inv3.item_ids


def test_has_key_with_id() -> None:
    k1: EntityID = 1
    k2: EntityID = 2
    k3: EntityID = 3
    key_store = {
        k1: Key(key_id="red"),
        k2: Key(key_id="blue"),
        k3: Key(key_id="red"),
    }
    inv = Inventory(item_ids=pset([k1, k2]))
    assert has_key_with_id(inv, key_store, "red") == k1
    assert has_key_with_id(inv, key_store, "blue") == k2
    assert has_key_with_id(inv, key_store, "green") is None


def test_all_keys_with_id() -> None:
    k1: EntityID = 1
    k2: EntityID = 2
    k3: EntityID = 3
    key_store = {
        k1: Key(key_id="red"),
        k2: Key(key_id="red"),
        k3: Key(key_id="blue"),
    }
    inv = Inventory(item_ids=pset([k1, k2, k3]))
    red_keys = all_keys_with_id(inv, key_store, "red")
    blue_keys = all_keys_with_id(inv, key_store, "blue")
    assert red_keys == pset([k1, k2])
    assert blue_keys == pset([k3])
    assert all_keys_with_id(inv, key_store, "green") == pset()
