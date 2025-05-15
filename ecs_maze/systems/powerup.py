from dataclasses import replace

from pyrsistent.typing import PMap
from ecs_maze.state import State
from ecs_maze.components import PowerUp, PowerUpLimit, PowerUpType


def garbage_collect_powerups(
    pu_map: PMap[PowerUpType, PowerUp],
) -> PMap[PowerUpType, PowerUp]:
    for pu_type, powerup in list(pu_map.items()):
        if powerup and powerup.remaining is not None and powerup.remaining <= 0:
            pu_map = pu_map.remove(pu_type)
    return pu_map


def update_duration_type_powerups(
    pu_map: PMap[PowerUpType, PowerUp],
) -> PMap[PowerUpType, PowerUp]:
    for pu_type, powerup in list(pu_map.items()):
        if powerup.limit != PowerUpLimit.DURATION or powerup.remaining is None:
            continue
        if powerup.remaining > 0:
            updated = replace(powerup, remaining=powerup.remaining - 1)
            pu_map = pu_map.set(pu_type, updated)
    return pu_map


def powerup_tick_system(state: State) -> State:
    pu_status = state.powerup_status
    new_status = pu_status
    for eid, pu_map in pu_status.items():
        updated_map = pu_map
        updated_map = update_duration_type_powerups(updated_map)
        updated_map = garbage_collect_powerups(updated_map)
        new_status = new_status.set(eid, updated_map)
    return replace(state, powerup_status=new_status)
