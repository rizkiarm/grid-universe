"""Rendering appearance component.

``Appearance`` controls layering and icon/background behavior when composing
tiles. Priority ordering rules:

* For background tiles (``background=True``) the highest priority value wins.
* For main foreground selection the lowest priority value wins (allows
    important items to sit on top even if visually small).

``icon=True`` marks entities that render as small corner overlays (e.g.
powerups) in addition to the main occupant.
"""

from dataclasses import dataclass
from enum import StrEnum, auto


class AppearanceName(StrEnum):
    """Enumeration of built‑in appearance categories."""

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
    """Visual rendering metadata.

    Attributes:
        name: Symbolic appearance identifier.
        priority: Integer priority used for layering selection.
        icon: If True this entity may render as a small corner icon.
        background: If True counts as a background layer candidate.
    """

    name: AppearanceName
    priority: int = 0
    icon: bool = False
    background: bool = False
