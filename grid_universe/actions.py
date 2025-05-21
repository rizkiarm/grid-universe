from enum import IntEnum, StrEnum, auto


class Action(StrEnum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    USE_KEY = auto()
    PICK_UP = auto()
    WAIT = auto()


MOVE_ACTIONS = [Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT]


class GymAction(IntEnum):
    UP = 0  # start at 0
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    USE_KEY = auto()
    PICK_UP = auto()
    WAIT = auto()
