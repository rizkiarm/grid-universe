from dataclasses import replace
from pyrsistent import PMap
from ecs_maze.state import State
from ecs_maze.components import PowerUpType, Health, Dead
from ecs_maze.types import EntityID
from ecs_maze.utils.ecs import entities_with_components_at
from ecs_maze.utils.health import apply_damage_and_check_death
from ecs_maze.utils.powerup import is_powerup_active, use_powerup_if_present


def enemy_collision_system(state: State, eid: EntityID) -> State:
    entity_pos = state.position.get(eid)
    if entity_pos is None or eid in state.dead:
        return state

    # Find all enemies at entity's position
    enemy_ids = entities_with_components_at(state, entity_pos, state.enemy)
    if not enemy_ids:
        return state

    powerup_status = state.powerup_status
    health_dict: PMap[EntityID, Health] = state.health
    dead_dict: PMap[EntityID, Dead] = state.dead

    # 1. Immunity powerup
    if is_powerup_active(state, eid, PowerUpType.GHOST):
        return state

    for oid in enemy_ids:
        # 2. Shield check (uses-based)
        shielded, powerup_status = use_powerup_if_present(
            powerup_status, eid, PowerUpType.SHIELD
        )
        if shielded:
            continue

        # 3. Apply damage or lethal effect
        damage_amount = state.damage[oid].amount if oid in state.damage else 0
        if damage_amount < 0:
            raise ValueError(f"Enemy {oid} has negative damage: {damage_amount}")

        health_dict, dead_dict = apply_damage_and_check_death(
            health_dict, dead_dict, eid, damage_amount, oid in state.lethal_damage
        )

    return replace(
        state,
        dead=dead_dict,
        health=health_dict,
        powerup_status=powerup_status,
    )
