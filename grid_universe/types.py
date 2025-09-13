"""Common type aliases and enumerations.

``MoveFn`` and ``ObjectiveFn`` are central extension points used in the
``State`` to allow pluggable movement / win condition behavior.
"""

from enum import StrEnum, auto
from typing import Callable, Sequence, TYPE_CHECKING


# Forward declaration for MoveFn typing to avoid circular imports:
if TYPE_CHECKING:
    from grid_universe.state import State
    from grid_universe.actions import Action
    from grid_universe.components import Position

EntityID = int

MoveFn = Callable[["State", "EntityID", "Action"], Sequence["Position"]]
ObjectiveFn = Callable[["State", "EntityID"], bool]


class EffectType(StrEnum):
    """Effect component categories (reflected in serialized observations)."""

    IMMUNITY = auto()
    PHASING = auto()
    SPEED = auto()


class EffectLimit(StrEnum):
    """Limit semantics for effects (time or usage based)."""

    TIME = auto()
    USAGE = auto()


EffectLimitAmount = int
