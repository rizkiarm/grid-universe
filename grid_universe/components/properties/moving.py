from dataclasses import dataclass
from enum import StrEnum, auto

from grid_universe.components.properties.position import Position


class MovingAxis(StrEnum):
    HORIZONTAL = auto()
    VERTICAL = auto()


@dataclass(frozen=True)
class Moving:
    axis: MovingAxis
    direction: int  # 1 or -1
    bounce: bool = True
    speed: int = 1
    prev_position: Position | None = None
