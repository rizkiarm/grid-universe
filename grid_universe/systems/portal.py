"""Portal teleportation system.

Moves entering collidable entities from a portal to its paired portal's
position. An entity is considered *entering* if its previous position differs
from the current one and it is present in the augmented trail for the portal's
tile this step.
"""

from dataclasses import replace
from pyrsistent import pset
from pyrsistent.typing import PMap, PSet
from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.trail import get_augmented_trail


def portal_system_entity(
    state: State, augmented_trail: PMap[Position, PSet[EntityID]], portal_id: EntityID
) -> State:
    """Teleport entities entering the specified portal to its pair."""
    portal = state.portal.get(portal_id)
    portal_position = state.position.get(portal_id)
    if portal_position is None or portal is None:
        return state

    pair_position = state.position.get(portal.pair_entity)
    if pair_position is None:
        return state

    entity_ids = set(augmented_trail.get(portal_position, pset())) & set(
        state.collidable
    )
    entering_entity_ids = {
        eid
        for eid in entity_ids
        if state.prev_position.get(eid) != state.position.get(eid)
    }

    state_position = state.position
    for eid in entering_entity_ids:
        state_position = state_position.set(eid, pair_position)
    return replace(state, position=state_position)


def portal_system(state: State) -> State:
    """Apply portal teleportation for all portals in the state."""
    augmented_trail: PMap[Position, PSet[EntityID]] = get_augmented_trail(
        state, pset(state.collidable)
    )
    for portal_id in state.portal:
        state = portal_system_entity(state, augmented_trail, portal_id)
    return state
