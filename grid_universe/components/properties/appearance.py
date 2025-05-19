from dataclasses import dataclass
from enum import StrEnum, auto


class AppearanceName(StrEnum):
    NONE = auto()
    BOOTS = auto()
    BOX = auto()
    COIN = auto()
    CORE = auto()
    DOOR = auto()
    EXIT = auto()
    FLOOR = auto()
    GEM = auto()
    GHOST = auto()
    HUMAN = auto()
    KEY = auto()
    LAVA = auto()
    LOCK = auto()
    MONSTER = auto()
    PORTAL = auto()
    SHIELD = auto()
    SPIKE = auto()
    WALL = auto()


@dataclass(frozen=True)
class Appearance:
    name: AppearanceName
    priority: int = 0
    icon: bool = False
    background: bool = False
