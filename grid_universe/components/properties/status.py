from dataclasses import dataclass

from pyrsistent import PSet

from grid_universe.types import EntityID


@dataclass(frozen=True)
class Status:
    effect_ids: PSet[EntityID]
