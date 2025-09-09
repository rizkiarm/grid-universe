from collections.abc import Mapping

from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID


def entities_at(state: State, pos: Position) -> set[EntityID]:
    """Returns all entity IDs whose position matches `pos`."""
    return {eid for eid, p in state.position.items() if p == pos}


def entities_with_components_at(
    state: State, pos: Position, *component_stores: Mapping[EntityID, object],
) -> list[EntityID]:
    """Returns all entity IDs at position `pos` that have ALL given components."""
    ids_at_pos: set[EntityID] = {eid for eid, p in state.position.items() if p == pos}
    for store in component_stores:
        ids_at_pos &= set(store.keys())
    return list(ids_at_pos)
