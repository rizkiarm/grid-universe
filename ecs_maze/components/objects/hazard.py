from dataclasses import dataclass
from enum import Enum


class HazardType(Enum):
    LAVA = "lava"
    SPIKE = "spike"


@dataclass(frozen=True)
class Hazard:
    type: HazardType
