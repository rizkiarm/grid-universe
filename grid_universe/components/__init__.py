"""grid_universe.components
=================================

Aggregate import surface for all ECS component dataclasses used by the engine.

This package separates immutable, purely data-focused *properties* (state that
describes an entity such as position, health, blocking, inventory, etc.) from
runtime *effects* (temporary modifiers like immunity, phasing, speed changes or
constraints such as usage and time limits).

The symbols re-exported here are intentionally curated so downstream code can
conveniently import components from a single place, e.g.::

    from grid_universe.components import Position, Health, Damage

All component classes are simple ``@dataclass`` value objects; they carry no
behavior beyond their fields and are manipulated by systems during the step
pipeline. See the ``systems`` package documentation for transformation logic.

"""

# Effects
from .effects import Effect
from .effects import Immunity
from .effects import Phasing
from .effects import TimeLimit
from .effects import UsageLimit
from .effects import Speed

# Properties
from .properties import Agent
from .properties import Appearance, AppearanceName
from .properties import Blocking
from .properties import Collectible
from .properties import Collidable
from .properties import Cost
from .properties import Damage
from .properties import Dead
from .properties import Exit
from .properties import Health
from .properties import Inventory
from .properties import Key
from .properties import LethalDamage
from .properties import Locked
from .properties import Moving, MovingAxis
from .properties import Pathfinding, PathfindingType
from .properties import Portal
from .properties import Position
from .properties import Pushable
from .properties import Required
from .properties import Rewardable
from .properties import Status

__all__ = [
    # Effects
    "Effect",
    "Immunity",
    "Phasing",
    "Speed",
    "TimeLimit",
    "UsageLimit",
    # Properties
    "Agent",
    "Appearance",
    "AppearanceName",
    "Blocking",
    "Collectible",
    "Collidable",
    "Cost",
    "Damage",
    "Dead",
    "Exit",
    "Health",
    "Inventory",
    "Key",
    "LethalDamage",
    "Locked",
    "Moving",
    "MovingAxis",
    "Pathfinding",
    "PathfindingType",
    "Portal",
    "Position",
    "Pushable",
    "Required",
    "Rewardable",
    "Status",
]
