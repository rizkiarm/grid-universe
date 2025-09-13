"""Status effect utility helpers.

Pure helpers for querying, selecting and consuming effects referenced by a
``Status`` component. Separation from the system module keeps logic reusable
across movement/pathfinding or interaction systems that need to consult or
exhaust limited effects (e.g., usage-limited phasing).
"""

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
    """Return list form for effect map(s) argument."""
    if isinstance(effects, (list, tuple)):
        return list(cast(Sequence[EffectMap], effects))
    else:
        return [cast(EffectMap, effects)]


def has_effect(state: State, effect_id: EntityID) -> bool:
    """Return True if ``effect_id`` exists in any runtime effect store."""
    effect_maps: List[EffectMap] = [state.immunity, state.phasing, state.speed]
    for effect in effect_maps:
        if effect_id in effect:
            return True
    return False


def valid_effect(state: State, effect_id: EntityID) -> bool:
    """Return True if effect has no expired time/usage limit."""
    # Only add effect if its time or usage limit is positive or unlimited
    if effect_id in state.time_limit and state.time_limit[effect_id].amount <= 0:
        return False
    if effect_id in state.usage_limit and state.usage_limit[effect_id].amount <= 0:
        return False
    return True


def add_status(status: Status, effect_id: EntityID) -> Status:
    """Return new ``Status`` with effect ID added."""
    return Status(effect_ids=status.effect_ids.add(effect_id))


def remove_status(status: Status, effect_id: EntityID) -> Status:
    """Return new ``Status`` with effect ID removed."""
    return Status(effect_ids=status.effect_ids.remove(effect_id))


def get_status_effect(
    effect_ids: PSet[EntityID],
    effects: Union[EffectMap, Sequence[EffectMap]],
    time_limit: PMap[EntityID, TimeLimit],
    usage_limit: PMap[EntityID, UsageLimit],
) -> Optional[EntityID]:
    """Select a valid effect from ``effect_ids`` matching any provided store.

    Selection rules:
    1. Filter to effect IDs present in at least one supplied effect map.
    2. Drop expired effects (time or usage limit <= 0).
    3. Prefer effects without usage limits; otherwise lowest EID yields tie.
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
    """Consume one use from a usage-limited effect if present."""
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
    """Select and consume an effect (if any) returning updated usage map."""
    effect_maps: List[EffectMap] = _normalize_effects(effects)
    effect_id = get_status_effect(effect_ids, effect_maps, time_limit, usage_limit)
    if effect_id is not None:
        usage_limit = use_status_effect(effect_id, usage_limit)
    return usage_limit, effect_id
