from collections.abc import Callable, Sequence
from enum import StrEnum, auto
from typing import TYPE_CHECKING

# Forward declaration for MoveFn typing to avoid circular imports:
if TYPE_CHECKING:
    from grid_universe.actions import Action
    from grid_universe.components import Position
    from grid_universe.state import State

EntityID = int

MoveFn = Callable[["State", "EntityID", "Action"], Sequence["Position"]]
ObjectiveFn = Callable[["State", "EntityID"], bool]


class EffectType(StrEnum):
    IMMUNITY = auto()
    PHASING = auto()
    SPEED = auto()


class EffectLimit(StrEnum):
    TIME = auto()
    USAGE = auto()


EffectLimitAmount = int
