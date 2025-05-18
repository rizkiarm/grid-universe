from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PowerUpLimit(Enum):
    USAGE = "usage"
    DURATION = "duration"


class PowerUpType(Enum):
    GHOST = "ghost"
    SHIELD = "shield"
    HAZARD_IMMUNITY = "hazard_immunity"
    DOUBLE_SPEED = "double_speed"


@dataclass(frozen=True)
class PowerUp:
    type: PowerUpType
    limit: Optional[PowerUpLimit] = None
    remaining: Optional[int] = None
