from dataclasses import replace
from typing import Any, Optional, List, Dict, Tuple, Set, Union
import random

from pyrsistent import pset

from grid_universe.objectives import default_objective_fn
from grid_universe.state import State, create_empty_state
from grid_universe.entity import Entity, new_entity_id
from grid_universe.moves import default_move_fn
from grid_universe.types import (
    EffectLimit,
    EffectLimitAmount,
    EffectType,
    EntityID,
    MoveFn,
    ObjectiveFn,
)
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
    AppearanceName,
    Blocking,
    Collectible,
    Collidable,
    Cost,
    Damage,
    # Dead,
    Exit,
    Health,
    Inventory,
    Key,
    LethalDamage,
    Locked,
    Moving,
    MovingAxis,
    Portal,
    Position,
    Pushable,
    Required,
    Rewardable,
    Status,
)

from grid_universe.utils.maze import (
    generate_perfect_maze,
    all_required_path_positions,
    adjust_maze_wall_percentage,
)


EffectOption = Dict[str, Any]

PowerupSpec = Tuple[
    AppearanceName,
    List[EffectType],
    Optional[EffectLimit],
    Optional[EffectLimitAmount],
    EffectOption,
]

DEFAULT_POWERUPS: List[PowerupSpec] = [
    (AppearanceName.BOOTS, [EffectType.SPEED], EffectLimit.TIME, 10, {"multiplier": 2}),
    (
        AppearanceName.GHOST,
        [EffectType.PHASING, EffectType.IMMUNITY],
        EffectLimit.TIME,
        10,
        {},
    ),
    (AppearanceName.SHIELD, [EffectType.IMMUNITY], EffectLimit.USAGE, 5, {}),
]

DamageLethal = bool
DamageAmount = int

HazardSpec = Tuple[AppearanceName, DamageAmount, DamageLethal]

DEFAULT_HAZARDS: List[HazardSpec] = [
    (AppearanceName.LAVA, 5, True),
    (AppearanceName.SPIKE, 3, False),
]

IsMoving = bool

EnemySpec = Tuple[AppearanceName, DamageAmount, DamageLethal, IsMoving]

DEFAULT_ENEMIES: List[EnemySpec] = [
    (AppearanceName.MONSTER, 5, True, True),
    (AppearanceName.MONSTER, 3, False, False),
]


def place_floors(
    state: State,
    empty_positions: List[Tuple[int, int]],
    cost: int = 1,
) -> State:
    state_entity = state.entity
    state_appearance = state.appearance
    state_cost = state.cost
    state_position = state.position
    for pos in empty_positions:
        eid: EntityID = new_entity_id()
        state_entity = state_entity.set(eid, Entity())
        state_appearance = state_appearance.set(
            eid, Appearance(name=AppearanceName.FLOOR, background=True, priority=10)
        )
        state_cost = state_cost.set(eid, Cost(amount=cost))
        state_position = state_position.set(eid, Position(*pos))
    return replace(
        state,
        entity=state_entity,
        appearance=state_appearance,
        cost=state_cost,
        position=state_position,
    )


def place_agent(
    state: State,
    position: Tuple[int, int],
    health: int,
) -> State:
    agent_id: EntityID = new_entity_id()
    state_entity = state.entity.set(agent_id, Entity())
    state_agent = state.agent.set(agent_id, Agent())
    state_position = state.position.set(agent_id, Position(*position))
    state_appearance = state.appearance.set(
        agent_id, Appearance(name=AppearanceName.HUMAN, priority=0)
    )
    state_inventory = state.inventory.set(agent_id, Inventory(pset()))
    state_status = state.status.set(agent_id, Status(pset()))
    state_health = state.health.set(agent_id, Health(health=health, max_health=health))
    state_collidable = state.collidable.set(agent_id, Collidable())
    return replace(
        state,
        entity=state_entity,
        agent=state_agent,
        position=state_position,
        appearance=state_appearance,
        inventory=state_inventory,
        status=state_status,
        health=state_health,
        collidable=state_collidable,
    )


def place_exit(
    state: State,
    position: Tuple[int, int],
) -> State:
    exit_id: EntityID = new_entity_id()
    state_entity = state.entity.set(exit_id, Entity())
    state_exit = state.exit.set(exit_id, Exit())
    state_position = state.position.set(exit_id, Position(*position))
    state_appearance = state.appearance.set(
        exit_id, Appearance(name=AppearanceName.EXIT, priority=9)
    )
    return replace(
        state,
        entity=state_entity,
        exit=state_exit,
        position=state_position,
        appearance=state_appearance,
    )


def place_collectibles(
    state: State,
    empty_positions: List[Tuple[int, int]],
    num_items: int,
    reward: Optional[int] = None,
    required: bool = False,
) -> Tuple[State, List[Tuple[int, int]]]:
    state_entity = state.entity
    state_position = state.position
    state_appearance = state.appearance
    state_collectible = state.collectible
    state_rewardable = state.rewardable
    state_required = state.required

    used_positions: List[Tuple[int, int]] = []
    for _ in range(num_items):
        if not empty_positions:
            break
        position = empty_positions.pop()
        item_id: EntityID = new_entity_id()

        state_entity = state_entity.set(item_id, Entity())
        state_position = state_position.set(item_id, Position(*position))
        state_appearance = state_appearance.set(
            item_id,
            Appearance(
                name=AppearanceName.CORE if required else AppearanceName.COIN,
                icon=True,
                priority=4,
            ),
        )
        state_collectible = state_collectible.set(item_id, Collectible())
        if reward is not None:
            state_rewardable = state_rewardable.set(item_id, Rewardable(amount=reward))
        if required:
            state_required = state_required.set(item_id, Required())

        used_positions.append(position)

    return replace(
        state,
        entity=state_entity,
        position=state_position,
        appearance=state_appearance,
        collectible=state_collectible,
        rewardable=state_rewardable,
        required=state_required,
    ), used_positions


def place_boxes(
    state: State,
    empty_positions: List[Tuple[int, int]],
    num_boxes: int,
    pushable: bool = False,
    moving: bool = False,
    rng: Optional[random.Random] = None,
) -> State:
    if rng is None:
        rng = random.Random()
    state_entity = state.entity
    state_position = state.position
    state_appearance = state.appearance
    state_blocking = state.blocking
    state_collidable = state.collidable
    state_pushable = state.pushable
    state_moving = state.moving

    for _ in range(num_boxes):
        if not empty_positions:
            break
        position = empty_positions.pop()
        box_id: EntityID = new_entity_id()

        state_entity = state_entity.set(box_id, Entity())
        state_position = state_position.set(box_id, Position(*position))
        state_appearance = state_appearance.set(
            box_id, Appearance(name=AppearanceName.BOX, priority=2)
        )
        state_blocking = state_blocking.set(box_id, Blocking())
        state_collidable = state_collidable.set(box_id, Collidable())
        if pushable:
            state_pushable = state_pushable.set(box_id, Pushable())
        if moving:
            state_moving = state_moving.set(
                box_id,
                Moving(
                    axis=rng.choice([MovingAxis.HORIZONTAL, MovingAxis.VERTICAL]),
                    direction=rng.choice([-1, 1]),
                ),
            )

    return replace(
        state,
        entity=state_entity,
        position=state_position,
        appearance=state_appearance,
        blocking=state_blocking,
        collidable=state_collidable,
        pushable=state_pushable,
        moving=state_moving,
    )


def place_portals(
    state: State,
    empty_positions: List[Tuple[int, int]],
    num_portals: int,
) -> State:
    state_entity = state.entity
    state_position = state.position
    state_appearance = state.appearance
    state_portal = state.portal
    for _ in range(num_portals):
        if len(empty_positions) < 2:
            break
        p1 = empty_positions.pop()
        p2 = empty_positions.pop()
        id1: EntityID = new_entity_id()
        id2: EntityID = new_entity_id()

        state_entity = state_entity.set(id1, Entity())
        state_entity = state_entity.set(id2, Entity())
        state_position = state_position.set(id1, Position(*p1))
        state_position = state_position.set(id2, Position(*p2))
        state_appearance = state_appearance.set(
            id1, Appearance(name=AppearanceName.PORTAL, priority=7)
        )
        state_appearance = state_appearance.set(
            id2, Appearance(name=AppearanceName.PORTAL, priority=7)
        )
        state_portal = state_portal.set(id1, Portal(pair_entity=id2))
        state_portal = state_portal.set(id2, Portal(pair_entity=id1))

    return replace(
        state,
        entity=state_entity,
        position=state_position,
        appearance=state_appearance,
        portal=state_portal,
    )


def place_doors_and_keys(
    state: State,
    empty_positions: List[Tuple[int, int]],
    n: int,
) -> State:
    state_entity = state.entity
    state_position = state.position
    state_appearance = state.appearance
    state_collectible = state.collectible
    state_blocking = state.blocking
    state_key = state.key
    state_locked = state.locked

    for i in range(n):
        if len(empty_positions) < 2:
            break
        key_pos = empty_positions.pop()
        lock_pos = empty_positions.pop()
        key_id: EntityID = new_entity_id()
        lock_id: EntityID = new_entity_id()
        internal_key_id: str = f"key{i}"

        state_entity = state_entity.set(key_id, Entity())
        state_entity = state_entity.set(lock_id, Entity())
        state_position = state_position.set(key_id, Position(*key_pos))
        state_position = state_position.set(lock_id, Position(*lock_pos))
        state_appearance = state_appearance.set(
            key_id, Appearance(name=AppearanceName.KEY, priority=4, icon=True)
        )
        state_appearance = state_appearance.set(
            lock_id, Appearance(name=AppearanceName.DOOR, priority=6)
        )
        state_collectible = state_collectible.set(key_id, Collectible())
        state_blocking = state_blocking.set(lock_id, Blocking())
        state_key = state_key.set(key_id, Key(key_id=internal_key_id))
        state_locked = state_locked.set(lock_id, Locked(key_id=internal_key_id))

    return replace(
        state,
        entity=state_entity,
        position=state_position,
        appearance=state_appearance,
        collectible=state_collectible,
        blocking=state_blocking,
        key=state_key,
        locked=state_locked,
    )


def place_threats(
    state: State,
    empty_positions: List[Tuple[int, int]],
    threats: Union[List[EnemySpec], List[HazardSpec]],
    priority: int = 1,
    rng: Optional[random.Random] = None,
) -> State:
    if rng is None:
        rng = random.Random()

    state_entity = state.entity
    state_position = state.position
    state_appearance = state.appearance
    state_collidable = state.collidable
    state_damage = state.damage
    state_lethal_damage = state.lethal_damage
    state_moving = state.moving

    for threat_detail in threats:
        if not empty_positions:
            break
        position = empty_positions.pop()
        entity_id: EntityID = new_entity_id()
        appearance_name, damage, lethal = threat_detail[:3]
        moving = threat_detail[3] if len(threat_detail) == 4 else False

        state_entity = state_entity.set(entity_id, Entity())
        state_position = state_position.set(entity_id, Position(*position))
        state_appearance = state_appearance.set(
            entity_id, Appearance(name=appearance_name, priority=priority)
        )
        state_collidable = state_collidable.set(entity_id, Collidable())
        state_damage = state_damage.set(entity_id, Damage(amount=damage))
        if lethal:
            state_lethal_damage = state_lethal_damage.set(entity_id, LethalDamage())
        if moving:
            state_moving = state_moving.set(
                entity_id,
                Moving(
                    axis=rng.choice([MovingAxis.HORIZONTAL, MovingAxis.VERTICAL]),
                    direction=rng.choice([-1, 1]),
                ),
            )

    return replace(
        state,
        entity=state_entity,
        position=state_position,
        appearance=state_appearance,
        collidable=state_collidable,
        damage=state_damage,
        lethal_damage=state_lethal_damage,
        moving=state_moving,
    )


def place_powerups(
    state: State,
    empty_positions: List[Tuple[int, int]],
    powerups: List[PowerupSpec],
) -> State:
    state_entity = state.entity
    state_position = state.position
    state_appearance = state.appearance
    state_collectible = state.collectible
    state_immunity = state.immunity
    state_phasing = state.phasing
    state_speed = state.speed
    state_time_limit = state.time_limit
    state_usage_limit = state.usage_limit
    for appearance_name, effects, limit_type, limit_amount, effect_option in powerups:
        if not empty_positions:
            break
        position = empty_positions.pop()
        powerup_id: EntityID = new_entity_id()

        state_entity = state_entity.set(powerup_id, Entity())
        state_position = state_position.set(powerup_id, Position(*position))
        state_appearance = state_appearance.set(
            powerup_id, Appearance(appearance_name, icon=True, priority=4)
        )
        state_collectible = state_collectible.set(powerup_id, Collectible())
        for effect in effects:
            if effect == EffectType.IMMUNITY:
                state_immunity = state_immunity.set(powerup_id, Immunity())
            if effect == EffectType.PHASING:
                state_phasing = state_phasing.set(powerup_id, Phasing())
            if effect == EffectType.SPEED:
                state_speed = state_speed.set(
                    powerup_id, Speed(effect_option["multiplier"])
                )
        if limit_type is None or limit_amount is None:
            continue
        if limit_type == EffectLimit.TIME:
            state_time_limit = state_time_limit.set(
                powerup_id, TimeLimit(amount=limit_amount)
            )
        if limit_type == EffectLimit.USAGE:
            state_usage_limit = state_usage_limit.set(
                powerup_id, UsageLimit(amount=limit_amount)
            )

    return replace(
        state,
        entity=state_entity,
        position=state_position,
        appearance=state_appearance,
        collectible=state_collectible,
        immunity=state_immunity,
        phasing=state_phasing,
        speed=state_speed,
        time_limit=state_time_limit,
        usage_limit=state_usage_limit,
    )


def place_walls(
    state: State,
    maze_grid: Dict[Tuple[int, int], bool],
) -> State:
    state_entity = state.entity
    state_position = state.position
    state_appearance = state.appearance
    state_blocking = state.blocking
    for position, open_ in maze_grid.items():
        if not open_:
            wall_id: EntityID = new_entity_id()
            state_entity = state_entity.set(wall_id, Entity())
            state_position = state_position.set(wall_id, Position(*position))
            state_appearance = state_appearance.set(
                wall_id,
                Appearance(name=AppearanceName.WALL, background=True, priority=9),
            )
            state_blocking = state_blocking.set(wall_id, Blocking())

    return replace(
        state,
        entity=state_entity,
        position=state_position,
        appearance=state_appearance,
        blocking=state_blocking,
    )


def generate(
    width: int,
    height: int,
    num_required_items: int,
    num_rewardable_items: int,
    num_boxes: int,
    num_moving_boxes: int,
    num_portals: int,
    num_doors: int,
    health: int = 5,
    movement_cost: int = 1,
    required_item_reward: int = 10,
    rewardable_item_reward: int = 10,
    powerups: List[PowerupSpec] = DEFAULT_POWERUPS,
    hazards: List[HazardSpec] = DEFAULT_HAZARDS,
    enemies: List[EnemySpec] = DEFAULT_ENEMIES,
    wall_percentage: float = 0.8,
    move_fn: MoveFn = default_move_fn,
    objective_fn: ObjectiveFn = default_objective_fn,
    seed: Optional[int] = None,
) -> State:
    rng: random.Random = random.Random(seed)
    maze_grid: Dict[Tuple[int, int], bool] = generate_perfect_maze(width, height, rng)
    maze_grid = adjust_maze_wall_percentage(maze_grid, wall_percentage, rng)

    state = create_empty_state(width, height, move_fn, objective_fn)

    # Tiles setup
    empty_positions: List[Tuple[int, int]] = [
        pos for pos, open_ in maze_grid.items() if open_
    ]
    rng.shuffle(empty_positions)

    # Floor
    state = place_floors(state, empty_positions[:], cost=1)

    # Agent/exit
    start_pos: Tuple[int, int] = empty_positions.pop()
    state = place_agent(state, start_pos, health=health)
    goal_pos: Tuple[int, int] = empty_positions.pop()
    state = place_exit(state, goal_pos)

    # Required collectibles
    state, required_positions = place_collectibles(
        state, empty_positions, num_required_items, required_item_reward, required=True
    )

    # Essential path for hazard/enemy placement
    essential_path: Set[Tuple[int, int]] = all_required_path_positions(
        maze_grid, start_pos, required_positions, goal_pos
    )

    # Rewardable collectibles
    state, _ = place_collectibles(
        state, empty_positions, num_rewardable_items, rewardable_item_reward
    )

    # Portals
    state = place_portals(state, empty_positions, num_portals)

    # Doors/keys
    state = place_doors_and_keys(state, empty_positions, num_doors)

    # Powerups
    state = place_powerups(state, empty_positions, powerups)

    # Update empty positions to exclude essential path
    empty_non_essential_positions = list(set(empty_positions) - essential_path)

    # Static boxes
    state = place_boxes(state, empty_non_essential_positions, num_boxes, pushable=True)

    # Moving boxes
    state = place_boxes(
        state, empty_non_essential_positions, num_moving_boxes, moving=True, rng=rng
    )

    # Enemies
    state = place_threats(
        state, empty_non_essential_positions, enemies, priority=1, rng=rng
    )

    # Hazards
    state = place_threats(
        state, empty_non_essential_positions, hazards, priority=7, rng=rng
    )

    # Walls
    state = place_walls(state, maze_grid)

    return state
