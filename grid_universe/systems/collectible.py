from dataclasses import replace
from typing import Optional, Set
from pyrsistent import PMap
from grid_universe.components import Collectible, Position, Status
from grid_universe.components.properties.inventory import Inventory
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.ecs import entities_with_components_at
from grid_universe.utils.inventory import add_item
from grid_universe.utils.status import add_status, has_effect, valid_effect


def collectible_system(state: State, eid: EntityID) -> State:
    entity_pos = state.position.get(eid)
    if entity_pos is None:
        return state

    collectable_ids = entities_with_components_at(state, entity_pos, state.collectible)
    if not collectable_ids:
        return state

    collected_ids: Set[EntityID] = set()

    # Update inventory
    state_inventory: PMap[EntityID, Inventory] = state.inventory
    entity_inventory: Optional[Inventory] = state_inventory.get(eid)
    if entity_inventory is not None:
        for collectable_id in collectable_ids:
            if has_effect(state, collectable_id):
                continue
            entity_inventory = add_item(entity_inventory, collectable_id)
            collected_ids.add(collectable_id)
        state_inventory = state_inventory.set(eid, entity_inventory)

    # Update status
    state_status: PMap[EntityID, Status] = state.status
    entity_status: Optional[Status] = state_status.get(eid)
    if entity_status is not None:
        for collectable_id in collectable_ids:
            if not has_effect(state, collectable_id) or not valid_effect(
                state, collectable_id
            ):
                continue
            entity_status = add_status(entity_status, collectable_id)
            collected_ids.add(collectable_id)
        state_status = state_status.set(eid, entity_status)

    # Update score if collected is rewardable
    score = state.score
    for collectable_id in collectable_ids:
        if collectable_id in state.rewardable:
            score += state.rewardable[collectable_id].amount
            collected_ids.add(collectable_id)

    # Remove collected entities from the world
    state_position: PMap[EntityID, Position] = state.position
    state_collectible: PMap[EntityID, Collectible] = state.collectible
    for cid in collected_ids:
        state_position = state_position.remove(cid)
        state_collectible = state_collectible.remove(cid)

    return replace(
        state,
        inventory=state_inventory,
        status=state_status,
        position=state_position,
        collectible=state_collectible,
        score=score,
    )
