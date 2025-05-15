from enum import Enum, auto
from typing import Callable, Optional, Sequence, Tuple
from typing import TYPE_CHECKING

from ecs_maze.components import HazardType, Position, PowerUpLimit, PowerUpType


# --- ECS tags for high-level entity/component marking ---
class Tag(Enum):
    AGENT = auto()
    ENEMY = auto()
    BOX = auto()
    PUSHABLE = auto()
    MOVING = auto()
    COLLECTIBLE = auto()
    ITEM = auto()
    REQUIRED = auto()
    REWARDABLE = auto()
    KEY = auto()
    LOCKED = auto()
    DOOR = auto()
    PORTAL = auto()
    EXIT = auto()
    POWERUP_GHOST = auto()
    POWERUP_SHIELD = auto()
    POWERUP_HAZARD_IMMUNITY = auto()
    POWERUP_DOUBLE_SPEED = auto()
    WALL = auto()
    HAZARD_LAVA = auto()
    HAZARD_SPIKE = auto()
    DEAD = auto()
    FLOOR = auto()


# --- Render types for actual icon/texture/sprite selection ---
class RenderType(Enum):
    AGENT = "agent"
    DEAD = "dead"
    ENEMY = "enemy"
    MOVING_ENEMY = "moving_enemy"
    BOX = "box"
    MOVING_BOX = "moving_box"
    PORTAL = "portal"
    LOCKED = "locked"
    DOOR = "door"
    KEY = "key"
    ITEM = "item"
    REQUIRED_ITEM = "required_item"
    REWARDABLE_ITEM = "rewardable_item"
    POWERUP_GHOST = "powerup:ghost"
    POWERUP_SHIELD = "powerup:shield"
    POWERUP_HAZARD_IMMUNITY = "powerup:hazard_immunity"
    POWERUP_DOUBLE_SPEED = "powerup:double_speed"
    HAZARD_LAVA = "hazard:lava"
    HAZARD_SPIKE = "hazard:spike"
    EXIT = "exit"
    WALL = "wall"
    FLOOR = "floor"


# Forward declaration for MoveFn typing to avoid circular imports:
if TYPE_CHECKING:
    from ecs_maze.state import State
    from ecs_maze.actions import Direction

EntityID = int

MoveFn = Callable[["State", int, "Direction"], Sequence["Position"]]

HazardSpec = Tuple[HazardType, int, bool]  # (HazardType, cost:int, lethal:bool)
PowerupSpec = Tuple[
    PowerUpType, Optional[PowerUpLimit], Optional[int]
]  # (PowerUpType, PowerUpLimit, remaining:int)
EnemySpec = Tuple[int, bool, bool]  # (damage:int, lethal:bool, moving:bool)
