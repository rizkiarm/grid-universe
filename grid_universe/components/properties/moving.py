"""Autonomous movement component.

``Moving`` entities advance automatically each turn along a specified axis and
direction with optional bouncing at boundaries and configurable tile step
speed (processed before player action). ``prev_position`` stores the last
position for cross / trail interactions when the movement system updates it.
"""

from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Optional

from grid_universe.components.properties.position import Position


class MovingAxis(StrEnum):
    """Axis enumeration for autonomous motion."""

    HORIZONTAL = auto()
    VERTICAL = auto()


@dataclass(frozen=True)
class Moving:
    """Autonomous mover definition.

    Attributes:
        axis: Axis of travel (horizontal or vertical).
        direction: +1 or -1 indicating step direction along the axis.
        bounce: Reverse direction at edge if True; otherwise stop at boundary.
        speed: Tile steps attempted per turn.
        prev_position: Internal bookkeeping of last position (set by system).
    """

    axis: MovingAxis
    direction: int  # 1 or -1
    bounce: bool = True
    speed: int = 1
    prev_position: Optional[Position] = None
