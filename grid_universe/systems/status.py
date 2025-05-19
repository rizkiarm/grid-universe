from dataclasses import replace
from typing import Tuple
from pyrsistent.typing import PMap, PSet
from grid_universe.components import TimeLimit, UsageLimit, Status
from grid_universe.entity import Entity
from grid_universe.state import State
from grid_universe.types import EntityID


def tick_time_limit(
    state: State,
    status: Status,
    time_limit: PMap[EntityID, TimeLimit],
) -> PMap[EntityID, TimeLimit]:
    for effect_id in status.effect_ids:
        if effect_id not in time_limit:
            continue
        time_limit = time_limit.set(
            effect_id, TimeLimit(amount=time_limit[effect_id].amount - 1)
        )
    return time_limit


def cleanup_effect(
    effect_id: EntityID,
    effect_ids: PSet[EntityID],
    entity: PMap[EntityID, Entity],
) -> Tuple[PSet[EntityID], PMap[EntityID, Entity]]:
    effect_ids = effect_ids.remove(effect_id)
    if effect_id in entity:
        entity = entity.remove(effect_id)
    return effect_ids, entity


def garbage_collect(
    state: State,
    time_limit: PMap[EntityID, TimeLimit],
    usage_limit: PMap[EntityID, UsageLimit],
    entity: PMap[EntityID, Entity],
    status: Status,
) -> Tuple[PMap[EntityID, Entity], Status]:
    effect_ids: PSet[EntityID] = status.effect_ids

    # Cleanup invalid effect ids
    for effect_id in effect_ids:
        if (
            effect_id not in state.immunity
            and effect_id not in state.phasing
            and effect_id not in state.speed
        ):
            effect_ids, entity = cleanup_effect(effect_id, effect_ids, entity)

    # Cleanup expired effect ids
    for effect_id in effect_ids:
        if effect_id not in time_limit and effect_id not in usage_limit:
            continue
        if effect_id in time_limit and time_limit[effect_id].amount > 0:
            continue
        if effect_id in usage_limit and usage_limit[effect_id].amount > 0:
            continue
        effect_ids, entity = cleanup_effect(effect_id, effect_ids, entity)

    return entity, replace(status, effect_ids=effect_ids)


def status_system(state: State) -> State:
    state_status = state.status
    state_entity = state.entity
    state_time_limit = state.time_limit
    state_usage_limit = state.usage_limit
    for entity_id, entity_status in state_status.items():
        state_time_limit = tick_time_limit(state, entity_status, state_time_limit)
        state_entity, entity_status = garbage_collect(
            state, state_time_limit, state_usage_limit, state_entity, entity_status
        )
        state_status = state_status.set(entity_id, entity_status)
    return replace(
        state,
        status=state_status,
        entity=state_entity,
        time_limit=state_time_limit,
        usage_limit=state_usage_limit,
    )
