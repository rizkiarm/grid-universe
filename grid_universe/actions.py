"""Action enumerations.

Defines both the human readable :class:`Action` (string enum) used internally
and a stable integer :class:`GymAction` mapping for Gymnasium compatibility.

``MOVE_ACTIONS`` is the canonical ordered list of movement actions; checks like
``if action in MOVE_ACTIONS`` are preferred over enum name comparisons.
"""

from enum import IntEnum, StrEnum, auto


class Action(StrEnum):
    """String enum of player actions.

    Members:
        UP, DOWN, LEFT, RIGHT: Movement directions.
        USE_KEY: Attempt to unlock co‑located locked entity with a matching key.
        PICK_UP: Collect items at the current tile.
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


class GymAction(IntEnum):
    """Stable integer mapping for integration with Gymnasium ``Discrete`` spaces."""

    UP = 0  # start at 0 for explicitness
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    USE_KEY = auto()
    PICK_UP = auto()
    WAIT = auto()
