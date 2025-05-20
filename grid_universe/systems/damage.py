from dataclasses import replace
from typing import Set, Tuple
from pyrsistent import PMap, pset
from pyrsistent.typing import PSet
from grid_universe.state import State
from grid_universe.components import Health, Dead, UsageLimit, Position
from grid_universe.types import EntityID
from grid_universe.utils.ecs import entities_with_components_at
from grid_universe.utils.health import apply_damage_and_check_death
from grid_universe.utils.status import use_status_effect_if_present
from grid_universe.utils.trail import get_augmented_trail


def get_damager_ids(
    state: State, augmented_trail: PMap[Position, PSet[EntityID]], position: Position
) -> Set[EntityID]:
    damagers = set(state.damage) | set(state.lethal_damage)
    return set(augmented_trail.get(position, pset())) & damagers


def get_cross_damager_ids(
    state: State,
    entity_id: EntityID,
    prev_entity_pos: Position,
    curr_entity_pos: Position,
) -> Set[EntityID]:
    """Find entities at the previous position that moved into the current entity's position."""
    cross_damager_ids = set()
    for eid in entities_with_components_at(
        state, prev_entity_pos, state.damage
    ) + entities_with_components_at(state, prev_entity_pos, state.lethal_damage):
        if state.prev_position.get(eid) == curr_entity_pos:
            cross_damager_ids.add(eid)
    return cross_damager_ids


def apply_damage(
    state: State,
    augmented_trail: PMap[Position, PSet[EntityID]],
    entity_id: EntityID,
    health: PMap[EntityID, Health],
    dead: PMap[EntityID, Dead],
    usage_limit: PMap[EntityID, UsageLimit],
) -> Tuple[PMap[EntityID, Health], PMap[EntityID, Dead], PMap[EntityID, UsageLimit]]:
    initial = health, dead, usage_limit

    entity_pos = state.position.get(entity_id)
    if entity_pos is None or entity_id in state.dead:
        return initial

    damager_ids: Set[EntityID] = get_damager_ids(state, augmented_trail, entity_pos)

    prev_entity_pos = state.prev_position.get(entity_id)
    if prev_entity_pos is not None:
        cross_damager_ids = get_cross_damager_ids(
            state, entity_id, prev_entity_pos, entity_pos
        )
        damager_ids = damager_ids.union(cross_damager_ids)

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
    augmented_trail: PMap[Position, PSet[EntityID]] = get_augmented_trail(
        state, pset(set(state.health) | set(state.damage) | set(state.lethal_damage))
    )

    for entity_id in state.health:
        health, dead, usage_limit = apply_damage(
            state, augmented_trail, entity_id, health, dead, usage_limit
        )

    return replace(
        state,
        health=health,
        dead=dead,
        usage_limit=usage_limit,
    )
