from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Optional

from grid_universe.components.properties.position import Position


class MovingAxis(StrEnum):
    HORIZONTAL = auto()
    VERTICAL = auto()


@dataclass(frozen=True)
class Moving:
    axis: MovingAxis
    direction: int  # 1 or -1
    prev_position: Optional[Position] = None
