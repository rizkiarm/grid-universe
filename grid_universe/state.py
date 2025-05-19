from dataclasses import dataclass
from typing import Optional
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
from grid_universe.types import EntityID, MoveFn


@dataclass(frozen=True)
class State:
    # Level
    width: int
    height: int
    move_fn: "MoveFn"

    # Entity
    entity: PMap[EntityID, Entity]

    # Components
    ## Effects
    immunity: PMap[EntityID, Immunity]
    phasing: PMap[EntityID, Phasing]
    speed: PMap[EntityID, Speed]
    time_limit: PMap[EntityID, TimeLimit]
    usage_limit: PMap[EntityID, UsageLimit]
    ## Properties
    agent: PMap[EntityID, Agent]
    appearance: PMap[EntityID, Appearance]
    blocking: PMap[EntityID, Blocking]
    collectible: PMap[EntityID, Collectible]
    collidable: PMap[EntityID, Collidable]
    cost: PMap[EntityID, Cost]
    damage: PMap[EntityID, Damage]
    dead: PMap[EntityID, Dead]
    exit: PMap[EntityID, Exit]
    health: PMap[EntityID, Health]
    inventory: PMap[EntityID, Inventory]
    key: PMap[EntityID, Key]
    lethal_damage: PMap[EntityID, LethalDamage]
    locked: PMap[EntityID, Locked]
    moving: PMap[EntityID, Moving]
    portal: PMap[EntityID, Portal]
    position: PMap[EntityID, Position]
    pushable: PMap[EntityID, Pushable]
    required: PMap[EntityID, Required]
    rewardable: PMap[EntityID, Rewardable]
    status: PMap[EntityID, Status]
    ## Extra
    prev_position: PMap[EntityID, Position] = pmap()

    # Status
    turn: int = 0
    score: int = 0
    win: bool = False
    lose: bool = False
    message: Optional[str] = None


def create_empty_state(width: int, height: int, move_fn: MoveFn) -> State:
    return State(
        # Level
        width=width,
        height=height,
        move_fn=move_fn,
        # Entity
        entity=pmap(),
        # Components
        ## Effects
        immunity=pmap(),
        phasing=pmap(),
        speed=pmap(),
        time_limit=pmap(),
        usage_limit=pmap(),
        ## Properties
        agent=pmap(),
        appearance=pmap(),
        blocking=pmap(),
        collectible=pmap(),
        collidable=pmap(),
        cost=pmap(),
        damage=pmap(),
        dead=pmap(),
        exit=pmap(),
        health=pmap(),
        inventory=pmap(),
        key=pmap(),
        lethal_damage=pmap(),
        locked=pmap(),
        moving=pmap(),
        portal=pmap(),
        position=pmap(),
        pushable=pmap(),
        required=pmap(),
        rewardable=pmap(),
        status=pmap(),
        ## Extra
        prev_position=pmap(),
        # Status
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
