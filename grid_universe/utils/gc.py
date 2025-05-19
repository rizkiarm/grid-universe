from pyrsistent import pmap
from grid_universe.types import EntityID
from grid_universe.state import State
from typing import Set, Any, Dict, cast
from pyrsistent.typing import PMap


def compute_alive_entities(state: State) -> Set[EntityID]:
    alive: Set[EntityID] = set(state.entity.keys())
    for stats in state.status.values():
        alive |= set(stats.effect_ids)
    for inv in state.inventory.values():
        alive |= set(inv.item_ids)
    return alive


def run_garbage_collector(state: State) -> State:
    alive = compute_alive_entities(state)
    new_fields: Dict[str, Any] = {}
    for field in state.__dataclass_fields__:
        value = getattr(state, field)
        if isinstance(value, type(pmap())):
            value_map = cast(PMap[EntityID, Any], value)
            filtered = pmap({k: v for k, v in value_map.items() if k in alive})
            new_fields[field] = filtered
    from dataclasses import replace

    return replace(state, **new_fields)
