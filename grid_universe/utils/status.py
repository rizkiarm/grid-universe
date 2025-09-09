from dataclasses import replace

from pyrsistent.typing import PMap, PSet

from grid_universe.components import Status
from grid_universe.components.effects import (
    Immunity,
    Phasing,
    Speed,
    TimeLimit,
    UsageLimit,
)
from grid_universe.state import State
from grid_universe.types import EntityID


def has_effect(state: State, effect_id: EntityID) -> bool:
    for effect in [state.immunity, state.phasing, state.speed]:
        if effect_id in effect:  # type: ignore
            return True
    return False


def valid_effect(state: State, effect_id: EntityID) -> bool:
    # Only add effect if its time or usage limit is positive or unlimited
    if effect_id in state.time_limit and state.time_limit[effect_id].amount <= 0:
        return False
    return not (effect_id in state.usage_limit and state.usage_limit[effect_id].amount <= 0)


def add_status(status: Status, effect_id: EntityID) -> Status:
    """Returns a new status with status_id added."""
    return Status(effect_ids=status.effect_ids.add(effect_id))


def remove_status(status: Status, effect_id: EntityID) -> Status:
    """Returns a new status with status_id removed."""
    return Status(effect_ids=status.effect_ids.remove(effect_id))


def get_status_effect(
    effect_ids: PSet[EntityID],
    effect: PMap[EntityID, Immunity] | PMap[EntityID, Phasing] | PMap[EntityID, Speed],
    time_limit: PMap[EntityID, TimeLimit],
    usage_limit: PMap[EntityID, UsageLimit],
) -> EntityID | None:
    relevant_effect_ids = [effect_id for effect_id in effect_ids if effect_id in effect]
    if len(relevant_effect_ids) == 0:
        return None
    for effect_id in relevant_effect_ids:
        if (
            effect_id not in usage_limit
        ):  # prioritize either infinite or time-limited effect
            return effect_id
    for effect_id in relevant_effect_ids:
        if effect_id in usage_limit or usage_limit[effect_id].amount > 0:
            return effect_id
    return None


def use_status_effect(
    effect_id: EntityID, usage_limit: PMap[EntityID, UsageLimit],
) -> PMap[EntityID, UsageLimit]:
    if effect_id not in usage_limit:
        return usage_limit
    return usage_limit.set(
        effect_id,
        replace(usage_limit[effect_id], amount=usage_limit[effect_id].amount - 1),
    )


def use_status_effect_if_present(
    effect_ids: PSet[EntityID],
    effect: PMap[EntityID, Immunity] | PMap[EntityID, Phasing] | PMap[EntityID, Speed],
    time_limit: PMap[EntityID, TimeLimit],
    usage_limit: PMap[EntityID, UsageLimit],
) -> tuple[PMap[EntityID, UsageLimit], EntityID | None]:
    effect_id = get_status_effect(effect_ids, effect, time_limit, usage_limit)
    if effect_id is not None:
        usage_limit = use_status_effect(effect_id, usage_limit)
    return usage_limit, effect_id
