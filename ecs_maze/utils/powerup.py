from typing import Optional, Tuple
from dataclasses import replace
from pyrsistent import PMap, pmap
from ecs_maze.components import PowerUp, PowerUpLimit, PowerUpType
from ecs_maze.state import State
from ecs_maze.types import EntityID


def use_powerup_if_present(
    pu_status: PMap[EntityID, PMap[PowerUpType, PowerUp]],
    eid: EntityID,
    powerup_type: PowerUpType,
) -> Tuple[bool, PMap[EntityID, PMap[PowerUpType, PowerUp]]]:
    empty_pu_map: PMap[PowerUpType, PowerUp] = pmap()
    pu_map: PMap[PowerUpType, PowerUp] = pu_status.get(eid, empty_pu_map)
    powerup: Optional[PowerUp] = pu_map.get(powerup_type)
    if powerup is None or powerup.limit != PowerUpLimit.USAGE:
        return False, pu_status
    if powerup.remaining is None:
        return True, pu_status
    new_remaining = powerup.remaining - 1
    if new_remaining > 0:
        pu_map = pu_map.set(powerup_type, replace(powerup, remaining=new_remaining))
    else:
        pu_map = pu_map.remove(powerup_type)
    pu_status = pu_status.set(eid, pu_map)
    return powerup.remaining > 0, pu_status


def is_powerup_active(
    state: State,
    eid: EntityID,
    powerup_type: PowerUpType,
) -> bool:
    pu_map = state.powerup_status.get(eid)
    if not pu_map:
        return False
    powerup = pu_map.get(powerup_type)
    if not powerup:
        return False
    return powerup.remaining is None or powerup.remaining > 0
