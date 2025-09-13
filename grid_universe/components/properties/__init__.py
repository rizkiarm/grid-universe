"""Property component aggregates.

This module re-exports *property* components: stable attributes that define an
entity's inherent or persistent qualities (e.g. :class:`Position`,
:class:`Health`, :class:`Blocking`, :class:`Inventory`). Systems read these
dataclasses to determine movement, collisions, rendering, damage application
and objective evaluation.

All properties are immutable dataclasses; creating a new instance (or removing
one from an entity) is how state changes are expressed between steps. For
temporary modifiers, see the sibling :mod:`grid_universe.components.effects`
package.
"""

from .agent import Agent
from .appearance import Appearance, AppearanceName
from .blocking import Blocking
from .collectible import Collectible
from .collidable import Collidable
from .cost import Cost
from .damage import Damage
from .dead import Dead
from .exit import Exit
from .health import Health
from .inventory import Inventory
from .key import Key
from .lethal_damage import LethalDamage
from .locked import Locked
from .moving import Moving, MovingAxis
from .pathfinding import Pathfinding, PathfindingType
from .portal import Portal
from .position import Position
from .pushable import Pushable
from .required import Required
from .rewardable import Rewardable
from .status import Status

__all__ = [
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
