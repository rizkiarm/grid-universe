from dataclasses import replace
from typing import Tuple
from pyrsistent import PMap
from grid_universe.state import State
from grid_universe.components import Health, Dead, UsageLimit
from grid_universe.types import EntityID
from grid_universe.utils.ecs import entities_with_components_at
from grid_universe.utils.health import apply_damage_and_check_death
from grid_universe.utils.status import use_status_effect_if_present


def apply_damage(
    state: State,
    entity_id: EntityID,
    health: PMap[EntityID, Health],
    dead: PMap[EntityID, Dead],
    usage_limit: PMap[EntityID, UsageLimit],
) -> Tuple[PMap[EntityID, Health], PMap[EntityID, Dead], PMap[EntityID, UsageLimit]]:
    initial = health, dead, usage_limit

    entity_pos = state.position.get(entity_id)
    if entity_pos is None or entity_id in state.dead:
        return initial

    damager_ids = set(
        entities_with_components_at(state, entity_pos, state.damage)
        + entities_with_components_at(state, entity_pos, state.lethal_damage)
    )
    if not damager_ids:
        return initial

    for damager_id in damager_ids:
        if entity_id in state.status:
            usage_limit, effect_id = use_status_effect_if_present(
                state.status[entity_id].effect_ids,
                state.immunity,
                state.time_limit,
                usage_limit,
            )
            if effect_id is not None:
                continue

        damage_amount = (
            state.damage[damager_id].amount if damager_id in state.damage else 0
        )
        if damage_amount < 0:
            raise ValueError(
                f"Damager {damager_id} has negative damage: {damage_amount}"
            )

        health, dead = apply_damage_and_check_death(
            health, dead, entity_id, damage_amount, damager_id in state.lethal_damage
        )

    return health, dead, usage_limit


def damage_system(state: State) -> State:
    health: PMap[EntityID, Health] = state.health
    dead: PMap[EntityID, Dead] = state.dead
    usage_limit: PMap[EntityID, UsageLimit] = state.usage_limit

    for entity_id in state.health:
        health, dead, usage_limit = apply_damage(
            state, entity_id, health, dead, usage_limit
        )

    return replace(
        state,
        health=health,
        dead=dead,
        usage_limit=usage_limit,
    )
