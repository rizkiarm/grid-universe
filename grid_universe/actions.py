"""Action enumerations.

Defines both the human readable :class:`Action` (string enum) used internally.
``MOVE_ACTIONS`` is the canonical ordered list of movement actions; checks like
``if action in MOVE_ACTIONS`` are preferred over enum name comparisons.
"""

from enum import StrEnum, auto


class Action(StrEnum):
    """String enum of player actions.

    Enum Members:
        UP: Move one tile up.
        DOWN: Move one tile down.
        LEFT: Move one tile left.
        RIGHT: Move one tile right.
        USE_KEY: Attempt to unlock a co‑located locked entity with a matching key.
        PICK_UP: Collect items (powerups / coins / cores / keys) at the current tile.
        WAIT: Advance a turn without moving (effects still tick).
    """

    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    USE_KEY = auto()
    PICK_UP = auto()
    WAIT = auto()


MOVE_ACTIONS = [Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT]
