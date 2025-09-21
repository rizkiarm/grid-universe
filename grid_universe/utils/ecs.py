"""ECS convenience queries.

Helper functions for querying entity/component relationships without
introducing iteration logic into systems. All functions are pure and operate
on the immutable :class:`grid_universe.state.State` snapshot.

Performance: ``entities_at`` uses a cached reverse index of the immutable
``State.position`` PMap to provide O(1) lookups per state snapshot.
"""

from functools import lru_cache
from typing import Dict, FrozenSet, Mapping, List, Set

from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID


@lru_cache(maxsize=4096)
def _position_index(
    position_store: Mapping[EntityID, Position],
) -> Mapping[Position, FrozenSet[EntityID]]:
    """Build a reverse index from position to entity IDs.

    The argument is a persistent/immutable PMap, which is hashable and thus
    safe to use with ``lru_cache``. Any new ``State`` (or updated position
    store) produces a distinct key, ensuring correctness across turns.
    """
    index: Dict[Position, Set[EntityID]] = {}
    for eid, pos in position_store.items():
        index.setdefault(pos, set()).add(eid)
    # Freeze sets for cacheability
    return {pos: frozenset(eids) for pos, eids in index.items()}


def entities_at(state: State, pos: Position) -> Set[EntityID]:
    """Return entity IDs whose position equals ``pos``."""
    idx = _position_index(state.position)
    return set(idx.get(pos, ()))


def entities_with_components_at(
    state: State, pos: Position, *component_stores: Mapping[EntityID, object]
) -> List[EntityID]:
    """Return IDs at ``pos`` possessing all provided component stores."""
    ids_at_pos: Set[EntityID] = entities_at(state, pos)
    for store in component_stores:
        ids_at_pos &= set(store.keys())
    return list(ids_at_pos)
