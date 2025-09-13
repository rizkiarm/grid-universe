from dataclasses import replace
from typing import List, Optional, Sequence, Tuple, Union, cast

from pyrsistent.typing import PMap, PSet
from grid_universe.components import Status
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.components.effects import (
    Immunity,
    Phasing,
    Speed,
    UsageLimit,
    TimeLimit,
)


EffectMap = Union[
    PMap[EntityID, Immunity],
    PMap[EntityID, Phasing],
    PMap[EntityID, Speed],
]


def _normalize_effects(
    effects: Union[EffectMap, Sequence[EffectMap]],
) -> List[EffectMap]:
    if isinstance(effects, (list, tuple)):
        return list(cast(Sequence[EffectMap], effects))
    else:
        return [cast(EffectMap, effects)]


def has_effect(state: State, effect_id: EntityID) -> bool:
    for effect in [state.immunity, state.phasing, state.speed]:
        if effect_id in effect:  # type: ignore
            return True
    return False


def valid_effect(state: State, effect_id: EntityID) -> bool:
    # Only add effect if its time or usage limit is positive or unlimited
    if effect_id in state.time_limit and state.time_limit[effect_id].amount <= 0:
        return False
    if effect_id in state.usage_limit and state.usage_limit[effect_id].amount <= 0:
        return False
    return True


def add_status(status: Status, effect_id: EntityID) -> Status:
    """Returns a new status with status_id added."""
    return Status(effect_ids=status.effect_ids.add(effect_id))


def remove_status(status: Status, effect_id: EntityID) -> Status:
    """Returns a new status with status_id removed."""
    return Status(effect_ids=status.effect_ids.remove(effect_id))


def get_status_effect(
    effect_ids: PSet[EntityID],
    effects: Union[EffectMap, Sequence[EffectMap]],
    time_limit: PMap[EntityID, TimeLimit],
    usage_limit: PMap[EntityID, UsageLimit],
) -> Optional[EntityID]:
    """
    Choose one active effect entity ID from effect_ids that matches any of the provided effect maps.

    - effects can be a single effect map (e.g., state.phasing) or a sequence of maps
      (e.g., [state.phasing, state.immunity, state.speed]).
    - Filters out expired effects (time_limit <= 0 or usage_limit <= 0).
    - Preference:
        1) Effects without a usage limit (infinite or time-limited only)
        2) Otherwise, any remaining valid effect (deterministically pick the lowest EID)
    """
    effect_maps: List[EffectMap] = _normalize_effects(effects)

    # Effects present in any of the requested effect stores
    relevant = [
        eid for eid in effect_ids if any(eid in eff_map for eff_map in effect_maps)
    ]
    if not relevant:
        return None

    # Filter out expired effects
    valid: list[EntityID] = []
    for eid in relevant:
        # Expired by time
        if eid in time_limit and time_limit[eid].amount <= 0:
            continue
        # Expired by usage
        if eid in usage_limit and usage_limit[eid].amount <= 0:
            continue
        valid.append(eid)

    if not valid:
        return None

    # Deterministic order
    valid.sort()

    # Prefer effects without usage limits (infinite or time-limited)
    for eid in valid:
        if eid not in usage_limit:
            return eid

    # Otherwise, return the first remaining usage-limited effect
    return valid[0]


def use_status_effect(
    effect_id: EntityID, usage_limit: PMap[EntityID, UsageLimit]
) -> PMap[EntityID, UsageLimit]:
    if effect_id not in usage_limit:
        return usage_limit
    usage_limit = usage_limit.set(
        effect_id,
        replace(usage_limit[effect_id], amount=usage_limit[effect_id].amount - 1),
    )
    return usage_limit


def use_status_effect_if_present(
    effect_ids: PSet[EntityID],
    effects: Union[EffectMap, Sequence[EffectMap]],
    time_limit: PMap[EntityID, TimeLimit],
    usage_limit: PMap[EntityID, UsageLimit],
) -> Tuple[PMap[EntityID, UsageLimit], Optional[EntityID]]:
    effect_maps: List[EffectMap] = _normalize_effects(effects)
    effect_id = get_status_effect(effect_ids, effect_maps, time_limit, usage_limit)
    if effect_id is not None:
        usage_limit = use_status_effect(effect_id, usage_limit)
    return usage_limit, effect_id
