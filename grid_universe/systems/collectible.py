from dataclasses import replace
from typing import TYPE_CHECKING

from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.ecs import entities_with_components_at
from grid_universe.utils.inventory import add_item
from grid_universe.utils.status import add_status, has_effect, valid_effect

if TYPE_CHECKING:
    from grid_universe.components import Status
    from grid_universe.components.properties.inventory import Inventory


def collectible_system(state: State, entity_id: EntityID) -> State:
    entity_pos = state.position.get(entity_id)
    if entity_pos is None:
        return state

    collectable_ids = entities_with_components_at(state, entity_pos, state.collectible)
    if not collectable_ids:
        return state

    entity_inventory: Inventory | None = state.inventory.get(entity_id)
    entity_status: Status | None = state.status.get(entity_id)
    state_score = state.score
    collected_ids: set[EntityID] = set()

    for collectable_id in collectable_ids:
        # Collectible is a powerup/effect
        if (
            entity_status is not None
            and has_effect(state, collectable_id)
            and valid_effect(state, collectable_id)
        ):
            entity_status = add_status(entity_status, collectable_id)
            collected_ids.add(collectable_id)
        # Collectible is a normal item (e.g., key, coin, core)
        elif entity_inventory is not None and not has_effect(state, collectable_id):
            entity_inventory = add_item(entity_inventory, collectable_id)
            collected_ids.add(collectable_id)
        # Collectible is rewardable
        if collectable_id in state.rewardable:
            state_score += state.rewardable[collectable_id].amount
            collected_ids.add(collectable_id)

    # Remove collected entities from world
    state_position = state.position
    state_collectible = state.collectible
    for collected_id in collected_ids:
        if collected_id in state_position:
            state_position = state_position.remove(collected_id)
        if collected_id in state_collectible:
            state_collectible = state_collectible.remove(collected_id)

    # Patch inventory/status in state
    state_inventory = state.inventory
    if entity_inventory is not None:
        state_inventory = state_inventory.set(entity_id, entity_inventory)
    state_status = state.status
    if entity_status is not None:
        state_status = state_status.set(entity_id, entity_status)

    return replace(
        state,
        inventory=state_inventory,
        status=state_status,
        position=state_position,
        collectible=state_collectible,
        score=state_score,
    )
