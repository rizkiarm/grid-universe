from dataclasses import replace
from typing import Tuple
from pyrsistent.typing import PMap, PSet
from grid_universe.components import TimeLimit, UsageLimit, Status
from grid_universe.entity import Entity
from grid_universe.state import State
from grid_universe.types import EntityID, EffectType


def tick_time_limit(
    state: State,
    status: Status,
    time_limit: PMap[EntityID, TimeLimit],
) -> PMap[EntityID, TimeLimit]:
    """
    Decrement the time limit for all effects in `status` that have a time limit.
    """
    for effect_id in status.effect_ids:
        if effect_id in time_limit:
            time_limit = time_limit.set(
                effect_id, TimeLimit(amount=time_limit[effect_id].amount - 1)
            )
    return time_limit


def cleanup_effect(
    effect_id: EntityID,
    effect_ids: PSet[EntityID],
    entity: PMap[EntityID, Entity],
) -> Tuple[PSet[EntityID], PMap[EntityID, Entity]]:
    """
    Remove the given effect_id from the effect_ids set and entity map.
    """
    effect_ids = effect_ids.remove(effect_id)
    if effect_id in entity:
        entity = entity.remove(effect_id)
    return effect_ids, entity


def is_effect_expired(
    effect_id: EntityID,
    time_limit: PMap[EntityID, TimeLimit],
    usage_limit: PMap[EntityID, UsageLimit],
) -> bool:
    """
    Returns True if the effect has a time or usage limit that is zero or below.
    """
    if effect_id in time_limit and time_limit[effect_id].amount <= 0:
        return True
    if effect_id in usage_limit and usage_limit[effect_id].amount <= 0:
        return True
    return False


def garbage_collect(
    state: State,
    time_limit: PMap[EntityID, TimeLimit],
    usage_limit: PMap[EntityID, UsageLimit],
    entity: PMap[EntityID, Entity],
    status: Status,
) -> Tuple[PMap[EntityID, Entity], Status]:
    """
    Removes from Status (and the entity map) any effect_ids that:
      - no longer exist as a component (orphaned effect - component deleted)
      - are expired (time/usage limit <= 0)
    Returns updated (entity, status).
    Now DRY: leverages EffectType for all effect component checks.
    """
    effect_ids: PSet[EntityID] = status.effect_ids

    # Remove invalid effect_ids by checking all effect component maps using EffectType
    for effect_id in list(effect_ids):
        if all(
            effect_id not in getattr(state, effect_type.name.lower())
            for effect_type in EffectType
        ):
            effect_ids, entity = cleanup_effect(effect_id, effect_ids, entity)

    # Remove expired effect_ids
    for effect_id in list(effect_ids):
        if is_effect_expired(effect_id, time_limit, usage_limit):
            effect_ids, entity = cleanup_effect(effect_id, effect_ids, entity)

    return entity, replace(status, effect_ids=effect_ids)


def status_system(state: State) -> State:
    """
    Updates all entity statuses in the ECS:
      - Decrements all time-limited effects.
      - Removes expired or invalid effect_ids from status and entity map.
      - Returns the new game state.
    """
    state_status = state.status
    state_entity = state.entity
    state_time_limit = state.time_limit
    state_usage_limit = state.usage_limit

    for entity_id, entity_status in state_status.items():
        # Tick time limits
        state_time_limit = tick_time_limit(state, entity_status, state_time_limit)
        # Cleanup expired/invalid effects
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
