from dataclasses import replace
from typing import List, Tuple
from pyrsistent import PMap, pmap
from ecs_maze.components import PowerUp, PowerUpType, Inventory
from ecs_maze.types import EntityID
from ecs_maze.utils.inventory import add_item, remove_item


def update_existing_powerup(
    pu_map: PMap[PowerUpType, PowerUp], existing: PowerUp, new: PowerUp
) -> PMap[PowerUpType, PowerUp]:
    if existing.remaining is None:
        return pu_map  # keep the unlimited powerup
    elif new.remaining is None:
        return pu_map.set(new.type, new)  # update with new unlimited
    elif existing.limit == new.limit:
        stacked_remaining = existing.remaining + new.remaining
        stacked_pu = replace(new, remaining=stacked_remaining)
        return pu_map.set(new.type, stacked_pu)
    # different limit
    return pu_map.set(new.type, new)  # replace with new. maybe chain in the future


def grant_powerups_on_collect(
    collected_ids: List[EntityID],
    collector_id: EntityID,
    inventory: Inventory,
    powerup_store: PMap[EntityID, PowerUp],
    powerup_status_store: PMap[EntityID, PMap[PowerUpType, PowerUp]],
) -> Tuple[
    Inventory, PMap[EntityID, PowerUp], PMap[EntityID, PMap[PowerUpType, PowerUp]]
]:
    """
    Grants any powerup present on collected_ids to the collector_id (agent), stacking duration/uses as appropriate.
    Removes collected entities from the collectible/world store.
    Returns (updated_powerup_store, updated_powerup_status_store).
    """
    new_inventory = inventory
    new_powerup = powerup_store
    new_powerup_status = powerup_status_store
    empty_powerup_map: PMap[PowerUpType, PowerUp] = pmap()
    agent_pu_map: PMap[PowerUpType, PowerUp] = powerup_status_store.get(
        collector_id, empty_powerup_map
    )

    for cid in collected_ids:
        if cid in powerup_store:
            new = powerup_store[cid]
            existing = agent_pu_map.get(new.type)

            if existing is not None:
                agent_pu_map = update_existing_powerup(agent_pu_map, existing, new)
            else:
                agent_pu_map = agent_pu_map.set(new.type, new)
            new_powerup = new_powerup.remove(cid)  # remove from the world
            new_inventory = remove_item(new_inventory, cid)  # remove from inventory

    new_powerup_status = new_powerup_status.set(collector_id, agent_pu_map)
    return new_inventory, new_powerup, new_powerup_status


def add_collected_to_inventory(
    inv: Inventory,
    collected_ids: List[EntityID],
) -> Inventory:
    """
    Adds all collected_ids to inventory using the given add_item utility.
    """
    new_inv = inv
    for cid in collected_ids:
        new_inv = add_item(new_inv, cid)
    return new_inv
