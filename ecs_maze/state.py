from dataclasses import dataclass
from typing import Optional
from pyrsistent import PMap, pmap

from ecs_maze.components import (
    Position,
    Agent,
    Enemy,
    Box,
    Collectible,
    Portal,
    Key,
    Door,
    Inventory,
    Moving,
    PowerUp,
    Hazard,
    Wall,
    Floor,
    Blocking,
    Dead,
    Rewardable,
    Pushable,
    Locked,
    Exit,
    Health,
    Required,
    Collidable,
    Item,
    PowerUpType,
    Damage,
    LethalDamage,
    Cost,
)
from ecs_maze.types import EntityID, MoveFn


@dataclass(frozen=True)
class State:
    width: int
    height: int
    move_fn: "MoveFn"
    position: PMap[EntityID, Position]
    agent: PMap[EntityID, Agent]
    enemy: PMap[EntityID, Enemy]
    box: PMap[EntityID, Box]
    collectible: PMap[EntityID, Collectible]
    item: PMap[EntityID, Item]
    required: PMap[EntityID, Required]
    portal: PMap[EntityID, Portal]
    key: PMap[EntityID, Key]
    door: PMap[EntityID, Door]
    locked: PMap[EntityID, Locked]
    inventory: PMap[EntityID, Inventory]
    moving: PMap[EntityID, Moving]
    powerup: PMap[EntityID, PowerUp]
    powerup_status: PMap[EntityID, PMap[PowerUpType, PowerUp]]
    hazard: PMap[EntityID, Hazard]
    wall: PMap[EntityID, Wall]
    floor: PMap[EntityID, Floor]
    blocking: PMap[EntityID, Blocking]
    dead: PMap[EntityID, Dead]
    rewardable: PMap[EntityID, Rewardable]
    cost: PMap[EntityID, Cost]
    pushable: PMap[EntityID, Pushable]
    exit: PMap[EntityID, Exit]
    health: PMap[EntityID, Health]
    collidable: PMap[EntityID, Collidable]
    damage: PMap[EntityID, Damage]
    lethal_damage: PMap[EntityID, LethalDamage]
    prev_position: PMap[EntityID, Position] = pmap()

    turn: int = 0
    score: int = 0
    win: bool = False
    lose: bool = False
    message: Optional[str] = None
