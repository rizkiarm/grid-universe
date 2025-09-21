"""Garbage collection utilities.

Removes unreachable entity/component entries from state maps. *Reachable*
entities include:
* All IDs in the master ``entity`` map.
* Effect entity IDs referenced by any ``Status`` component.
* Item IDs referenced by any ``Inventory`` component.

The garbage collector prunes orphaned component entries (e.g., an effect map
entry for an effect whose owning status no longer references it) which keeps
state size bounded and avoids leaking stale objects during long simulations.
"""

from dataclasses import replace
from pyrsistent import pmap
from grid_universe.types import EntityID
from grid_universe.state import State
from typing import Set, Any, Dict, cast
from pyrsistent.typing import PMap


def compute_alive_entities(state: State) -> Set[EntityID]:
    """Return the closure of entity IDs reachable from registries & references."""
    alive: Set[EntityID] = set(state.position.keys())
    for stats in state.status.values():
        alive |= set(stats.effect_ids)
    for inv in state.inventory.values():
        alive |= set(inv.item_ids)
    return alive


def run_garbage_collector(state: State) -> State:
    """Prune component maps to only contain reachable entity IDs."""
    alive = compute_alive_entities(state)
    new_fields: Dict[str, Any] = {}
    for field in state.__dataclass_fields__:
        value = getattr(state, field)
        if isinstance(value, type(pmap())):
            value_map = cast(PMap[EntityID, Any], value)
            filtered = pmap({k: v for k, v in value_map.items() if k in alive})
            new_fields[field] = filtered
    return replace(state, **new_fields)
