from dataclasses import dataclass
from enum import StrEnum, auto

from grid_universe.types import EntityID


class PathfindingType(StrEnum):
    STRAIGHT_LINE = auto()
    PATH = auto()


@dataclass(frozen=True)
class Pathfinding:
    target: EntityID | None = None
    type: PathfindingType = PathfindingType.PATH
