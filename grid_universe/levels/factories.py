# grid_universe/levels/factories.py

from __future__ import annotations

from typing import Optional
from pyrsistent import pset

from grid_universe.components.properties import (
    Agent,
    Appearance,
    AppearanceName,
    Blocking,
    Collectible,
    Collidable,
    Cost,
    Damage,
    Exit,
    Health,
    Inventory,
    Key,
    LethalDamage,
    Locked,
    Portal,
    Pushable,
    Required,
    Rewardable,
    PathfindingType,
    Status,
)
from grid_universe.components.effects import (
    Immunity,
    Phasing,
    Speed,
    TimeLimit,
    UsageLimit,
)
from .entity_spec import EntitySpec


def create_agent(health: int = 5) -> EntitySpec:
    return EntitySpec(
        agent=Agent(),
        appearance=Appearance(name=AppearanceName.HUMAN, priority=0),
        health=Health(health=health, max_health=health),
        collidable=Collidable(),
        inventory=Inventory(pset()),
        status=Status(pset()),
    )


def create_floor(cost_amount: int = 1) -> EntitySpec:
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.FLOOR, background=True, priority=10),
        cost=Cost(amount=cost_amount),
    )


def create_wall() -> EntitySpec:
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.WALL, background=True, priority=9),
        blocking=Blocking(),
    )


def create_exit() -> EntitySpec:
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.EXIT, priority=9),
        exit=Exit(),
    )


def create_coin(reward: Optional[int] = None) -> EntitySpec:
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.COIN, icon=True, priority=4),
        collectible=Collectible(),
        rewardable=None if reward is None else Rewardable(amount=reward),
    )


def create_core(reward: Optional[int] = None, required: bool = True) -> EntitySpec:
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.CORE, icon=True, priority=4),
        collectible=Collectible(),
        rewardable=None if reward is None else Rewardable(amount=reward),
        required=Required() if required else None,
    )


def create_key(key_id: str) -> EntitySpec:
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.KEY, icon=True, priority=4),
        collectible=Collectible(),
        key=Key(key_id=key_id),
    )


def create_door(key_id: str) -> EntitySpec:
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.DOOR, priority=6),
        blocking=Blocking(),
        locked=Locked(key_id=key_id),
    )


def create_portal(*, pair: Optional[EntitySpec] = None) -> EntitySpec:
    """
    If 'pair' is provided, this will set reciprocal authoring refs so both ends are paired on conversion.
    """
    obj = EntitySpec(
        appearance=Appearance(name=AppearanceName.PORTAL, priority=7),
        portal=Portal(pair_entity=-1),
    )
    if pair is not None:
        obj.portal_pair_ref = pair
        if pair.portal_pair_ref is None:
            pair.portal_pair_ref = obj
    return obj


def create_box(pushable: bool = True) -> EntitySpec:
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.BOX, priority=2),
        blocking=Blocking(),
        collidable=Collidable(),
        pushable=Pushable() if pushable else None,
    )


def create_monster(
    damage: int = 3,
    lethal: bool = False,
    *,
    pathfind_target: Optional[EntitySpec] = None,
    path_type: PathfindingType = PathfindingType.PATH,
) -> EntitySpec:
    obj = EntitySpec(
        appearance=Appearance(name=AppearanceName.MONSTER, priority=1),
        collidable=Collidable(),
        damage=Damage(amount=damage),
        lethal_damage=LethalDamage() if lethal else None,
    )
    if pathfind_target is not None:
        obj.pathfind_target_ref = pathfind_target
        obj.pathfinding_type = path_type
    return obj


def create_hazard(
    appearance: AppearanceName,
    damage: int,
    lethal: bool = False,
    priority: int = 7,
) -> EntitySpec:
    return EntitySpec(
        appearance=Appearance(name=appearance, priority=priority),
        collidable=Collidable(),
        damage=Damage(amount=damage),
        lethal_damage=LethalDamage() if lethal else None,
    )


def create_speed_effect(
    multiplier: int,
    time: Optional[int] = None,
    usage: Optional[int] = None,
) -> EntitySpec:
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.BOOTS, icon=True, priority=4),
        collectible=Collectible(),
        speed=Speed(multiplier=multiplier),
        time_limit=TimeLimit(amount=time) if time is not None else None,
        usage_limit=UsageLimit(amount=usage) if usage is not None else None,
    )


def create_immunity_effect(
    time: Optional[int] = None,
    usage: Optional[int] = None,
) -> EntitySpec:
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.SHIELD, icon=True, priority=4),
        collectible=Collectible(),
        immunity=Immunity(),
        time_limit=TimeLimit(amount=time) if time is not None else None,
        usage_limit=UsageLimit(amount=usage) if usage is not None else None,
    )


def create_phasing_effect(
    time: Optional[int] = None,
    usage: Optional[int] = None,
) -> EntitySpec:
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.GHOST, icon=True, priority=4),
        collectible=Collectible(),
        phasing=Phasing(),
        time_limit=TimeLimit(amount=time) if time is not None else None,
        usage_limit=UsageLimit(amount=usage) if usage is not None else None,
    )
