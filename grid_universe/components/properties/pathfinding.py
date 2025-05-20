from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Optional

from grid_universe.types import EntityID


class PathfindingType(StrEnum):
    STRAIGHT_LINE = auto()
    PATH = auto()


@dataclass(frozen=True)
class Pathfinding:
    target: Optional[EntityID] = None
    type: PathfindingType = PathfindingType.PATH
