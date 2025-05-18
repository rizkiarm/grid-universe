from dataclasses import dataclass
from typing import Optional

from grid_universe.components.properties.position import Position


@dataclass(frozen=True)
class Moving:
    axis: str  # "horizontal" or "vertical"
    direction: int  # 1 or -1
    prev_position: Optional[Position] = None
