from dataclasses import dataclass
from enum import Enum, auto


class Direction(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


@dataclass(frozen=True)
class MoveAction:
    """
    Move the agent in a given direction.
    """

    entity_id: int  # The agent or entity performing the move
    direction: Direction


@dataclass(frozen=True)
class UseKeyAction:
    """
    Attempt to use a key at the current agent location (e.g., to unlock a door).
    """

    entity_id: int


@dataclass(frozen=True)
class PickUpAction:
    """
    Attempt to pick up an item (collectible, key, powerup) at the current location.
    """

    entity_id: int  # Usually the agent


@dataclass(frozen=True)
class WaitAction:
    """
    Take no action this turn (useful for multi-agent or turn-based games).
    """

    entity_id: int


Action = MoveAction | UseKeyAction | PickUpAction | WaitAction
