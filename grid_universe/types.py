from enum import StrEnum, auto
from typing import Callable, Sequence, TYPE_CHECKING


# Forward declaration for MoveFn typing to avoid circular imports:
if TYPE_CHECKING:
    from grid_universe.state import State
    from grid_universe.actions import Direction
    from grid_universe.components import Position

EntityID = int

MoveFn = Callable[["State", "EntityID", "Direction"], Sequence["Position"]]
ObjectiveFn = Callable[["State", "EntityID"], bool]


class EffectType(StrEnum):
    IMMUNITY = auto()
    PHASING = auto()
    SPEED = auto()


class EffectLimit(StrEnum):
    TIME = auto()
    USAGE = auto()


EffectLimitAmount = int
