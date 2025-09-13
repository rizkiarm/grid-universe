from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Optional

from grid_universe.types import EntityID


class PathfindingType(StrEnum):
    STRAIGHT_LINE = auto()
    PATH = auto()


@dataclass(frozen=True)
class Pathfinding:
    """AI movement directive for automated entities.

    Specifies how an entity should compute movement objectives each step.

    Attributes:
        target:
            Optional entity ID to follow/approach. If ``None`` and ``type`` is
            ``PATH`` the system may skip pathfinding or use a default goal.
        type:
            Strategy: ``PATH`` requests full pathfinding (e.g., A*), whereas
            ``STRAIGHT_LINE`` attempts direct movement along axis-aligned shortest
            displacement without obstacle search.
    """

    target: Optional[EntityID] = None
    type: PathfindingType = PathfindingType.PATH
