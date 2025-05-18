from dataclasses import replace
from pyrsistent import PMap
from grid_universe.components import Collectible, Position
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.collectible import (
    grant_powerups_on_collect,
    add_collected_to_inventory,
)
from grid_universe.utils.ecs import entities_with_components_at


def collectible_system(state: State, eid: EntityID) -> State:
    entity_pos = state.position.get(eid)
    if entity_pos is None:
        return state

    collected_ids = entities_with_components_at(state, entity_pos, state.collectible)
    if not collected_ids:
        return state

    inv = state.inventory.get(eid)
    if inv is None:
        return state

    # Inventory update
    new_inv = add_collected_to_inventory(inv, collected_ids)

    # Grant powerups with stacking
    new_inv, new_powerup, new_powerup_status = grant_powerups_on_collect(
        collected_ids, eid, new_inv, state.powerup, state.powerup_status
    )

    # Update score if collected is rewardable
    score = state.score
    for cid in collected_ids:
        if cid in state.rewardable:
            score += state.rewardable[cid].reward

    # Update inventory
    new_inventory = state.inventory.set(eid, new_inv)

    # Remove collectible entities from the world
    new_position: PMap[EntityID, Position] = state.position
    new_collectible: PMap[EntityID, Collectible] = state.collectible
    for cid in collected_ids:
        new_position = new_position.remove(cid)
        new_collectible = new_collectible.remove(cid)

    return replace(
        state,
        inventory=new_inventory,
        collectible=new_collectible,
        position=new_position,
        score=score,
        powerup=new_powerup,
        powerup_status=new_powerup_status,
    )
