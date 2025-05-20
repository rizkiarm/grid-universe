from dataclasses import dataclass
from typing import Any, Optional
from pyrsistent import PMap, pmap

from grid_universe.entity import Entity
from grid_universe.components.effects import (
    Immunity,
    Phasing,
    Speed,
    TimeLimit,
    UsageLimit,
)
from grid_universe.components.properties import (
    Agent,
    Appearance,
    Blocking,
    Collectible,
    Collidable,
    Cost,
    Damage,
    Dead,
    Exit,
    Health,
    Inventory,
    Key,
    LethalDamage,
    Locked,
    Moving,
    Portal,
    Position,
    Pushable,
    Required,
    Rewardable,
    Status,
)
from grid_universe.types import EntityID, MoveFn, ObjectiveFn


@dataclass(frozen=True)
class State:
    # Level
    width: int
    height: int
    move_fn: "MoveFn"
    objective_fn: "ObjectiveFn"

    # Entity
    entity: PMap[EntityID, Entity] = pmap()

    # Components
    ## Effects
    immunity: PMap[EntityID, Immunity] = pmap()
    phasing: PMap[EntityID, Phasing] = pmap()
    speed: PMap[EntityID, Speed] = pmap()
    time_limit: PMap[EntityID, TimeLimit] = pmap()
    usage_limit: PMap[EntityID, UsageLimit] = pmap()
    ## Properties
    agent: PMap[EntityID, Agent] = pmap()
    appearance: PMap[EntityID, Appearance] = pmap()
    blocking: PMap[EntityID, Blocking] = pmap()
    collectible: PMap[EntityID, Collectible] = pmap()
    collidable: PMap[EntityID, Collidable] = pmap()
    cost: PMap[EntityID, Cost] = pmap()
    damage: PMap[EntityID, Damage] = pmap()
    dead: PMap[EntityID, Dead] = pmap()
    exit: PMap[EntityID, Exit] = pmap()
    health: PMap[EntityID, Health] = pmap()
    inventory: PMap[EntityID, Inventory] = pmap()
    key: PMap[EntityID, Key] = pmap()
    lethal_damage: PMap[EntityID, LethalDamage] = pmap()
    locked: PMap[EntityID, Locked] = pmap()
    moving: PMap[EntityID, Moving] = pmap()
    portal: PMap[EntityID, Portal] = pmap()
    position: PMap[EntityID, Position] = pmap()
    pushable: PMap[EntityID, Pushable] = pmap()
    required: PMap[EntityID, Required] = pmap()
    rewardable: PMap[EntityID, Rewardable] = pmap()
    status: PMap[EntityID, Status] = pmap()
    ## Extra
    prev_position: PMap[EntityID, Position] = pmap()

    # Status
    turn: int = 0
    score: int = 0
    win: bool = False
    lose: bool = False
    message: Optional[str] = None

    @property
    def description(self) -> PMap[str, Any]:
        description: PMap[str, Any] = pmap()
        for field in self.__dataclass_fields__:
            value = getattr(self, field)
            if isinstance(value, type(pmap())) and len(value) == 0:
                continue
            description = description.set(field, value)
        return pmap(description)
