from __future__ import annotations

from enum import StrEnum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Set

import random

from grid_universe.state import State
from grid_universe.types import (
    EffectLimit,
    EffectLimitAmount,
    EffectType,
    MoveFn,
    ObjectiveFn,
)
from grid_universe.moves import default_move_fn
from grid_universe.objectives import default_objective_fn
from grid_universe.components.properties import (
    AppearanceName,
    Moving,
    MovingAxis,
    PathfindingType,
)
from grid_universe.levels.grid import Level, Position
from grid_universe.levels.convert import to_state
from grid_universe.levels.entity_spec import EntitySpec
from grid_universe.levels.factories import (
    create_agent,
    create_floor,
    create_wall,
    create_exit,
    create_coin,
    create_core,
    create_key,
    create_door,
    create_portal,
    create_box,
    create_monster,
    create_hazard,
    create_speed_effect,
    create_immunity_effect,
    create_phasing_effect,
)
from grid_universe.utils.maze import (
    generate_perfect_maze,
    adjust_maze_wall_percentage,
    all_required_path_positions,
)


# -------------------------
# Specs and defaults
# -------------------------

EffectOption = Dict[str, Any]
PowerupSpec = Tuple[
    EffectType, Optional[EffectLimit], Optional[EffectLimitAmount], EffectOption
]
DamageAmount = int
IsLethal = bool
HazardSpec = Tuple[AppearanceName, DamageAmount, IsLethal]

DEFAULT_POWERUPS: List[PowerupSpec] = [
    (EffectType.SPEED, EffectLimit.TIME, 10, {"multiplier": 2}),
    (EffectType.PHASING, EffectLimit.TIME, 10, {}),
    (EffectType.IMMUNITY, EffectLimit.USAGE, 5, {}),
]

DEFAULT_HAZARDS: List[HazardSpec] = [
    (AppearanceName.LAVA, 5, True),
    (AppearanceName.SPIKE, 3, False),
]


class MovementType(StrEnum):
    STATIC = auto()
    DIRECTIONAL = auto()
    PATHFINDING_LINE = auto()
    PATHFINDING_PATH = auto()


EnemySpec = Tuple[DamageAmount, IsLethal, MovementType, int]
BoxSpec = Tuple[bool, int]

DEFAULT_ENEMIES: List[EnemySpec] = [
    (5, True, MovementType.DIRECTIONAL, 2),
    (3, False, MovementType.PATHFINDING_LINE, 1),
]

DEFAULT_BOXES: List[BoxSpec] = [
    (True, 0),
    (False, 1),
    (False, 2),
]


# -------------------------
# Internal helpers
# -------------------------


def _random_axis_and_dir(rng: random.Random) -> Tuple[MovingAxis, int]:
    axis: MovingAxis = rng.choice([MovingAxis.HORIZONTAL, MovingAxis.VERTICAL])
    direction: int = rng.choice([-1, 1])
    return axis, direction


def _pop_or_fallback(positions: List[Position], fallback: Position) -> Position:
    return positions.pop() if positions else fallback


# -------------------------
# Main generator
# -------------------------


def generate(
    width: int,
    height: int,
    num_required_items: int = 1,
    num_rewardable_items: int = 1,
    num_portals: int = 1,
    num_doors: int = 1,
    health: int = 5,
    movement_cost: int = 1,
    required_item_reward: int = 10,
    rewardable_item_reward: int = 10,
    boxes: List[BoxSpec] = DEFAULT_BOXES,
    powerups: List[PowerupSpec] = DEFAULT_POWERUPS,
    hazards: List[HazardSpec] = DEFAULT_HAZARDS,
    enemies: List[EnemySpec] = DEFAULT_ENEMIES,
    wall_percentage: float = 0.8,
    move_fn: MoveFn = default_move_fn,
    objective_fn: ObjectiveFn = default_objective_fn,
    seed: Optional[int] = None,
) -> State:
    """
    Maze level generator using the grid-centric Level API + factories, then converts to State.

    Explicit wiring supported at authoring time:
    - Monsters may specify pathfinding target by referencing the agent EntityObject.
    - Portals may be paired by referencing each other (create_portal(pair=other)).
      These references are resolved to proper EIDs in to_state().
    """
    rng = random.Random(seed)

    # 1) Base maze -> adjust walls
    maze_grid = generate_perfect_maze(width, height, rng)
    maze_grid = adjust_maze_wall_percentage(maze_grid, wall_percentage, rng)

    # 2) Level
    level = Level(
        width=width,
        height=height,
        move_fn=move_fn,
        objective_fn=objective_fn,
        seed=seed,
    )

    # 3) Collect positions
    open_positions: List[Position] = [
        pos for pos, is_open in maze_grid.items() if is_open
    ]
    wall_positions: List[Position] = [
        pos for pos, is_open in maze_grid.items() if not is_open
    ]
    rng.shuffle(open_positions)  # randomize for placement variety

    # 4) Floors on all open cells
    for pos in open_positions:
        level.add(pos, create_floor(cost_amount=movement_cost))

    # 5) Agent and exit
    start_pos: Position = _pop_or_fallback(open_positions, (0, 0))
    agent = create_agent(health=health)
    level.add(start_pos, agent)

    goal_pos: Position = _pop_or_fallback(open_positions, (width - 1, height - 1))
    level.add(goal_pos, create_exit())

    # 6) Required cores
    required_positions: List[Position] = []
    for _ in range(num_required_items):
        if not open_positions:
            break
        pos = open_positions.pop()
        level.add(pos, create_core(reward=required_item_reward, required=True))
        required_positions.append(pos)

    # Compute essential path set
    essential_path: Set[Position] = all_required_path_positions(
        maze_grid, start_pos, required_positions, goal_pos
    )

    # 7) Rewardable coins
    for _ in range(num_rewardable_items):
        if not open_positions:
            break
        level.add(open_positions.pop(), create_coin(reward=rewardable_item_reward))

    # 8) Portals (explicit pairing by reference)
    for _ in range(num_portals):
        if len(open_positions) < 2:
            break
        p1 = create_portal()
        p2 = create_portal(pair=p1)  # reciprocal authoring-time reference
        level.add(open_positions.pop(), p1)
        level.add(open_positions.pop(), p2)

    # 9) Doors/keys
    for i in range(num_doors):
        if len(open_positions) < 2:
            break
        key_pos = open_positions.pop()
        door_pos = open_positions.pop()
        key_id_str = f"key{i}"
        level.add(key_pos, create_key(key_id=key_id_str))
        level.add(door_pos, create_door(key_id=key_id_str))

    # 10) Powerups (as pickups)
    create_effect_fn_map: dict[EffectType, Callable[..., EntitySpec]] = {
        EffectType.SPEED: create_speed_effect,
        EffectType.IMMUNITY: create_immunity_effect,
        EffectType.PHASING: create_phasing_effect,
    }
    for type_, lim_type, lim_amount, extra in powerups:
        if not open_positions:
            break
        pos = open_positions.pop()
        create_effect_fn = create_effect_fn_map[type_]
        kwargs = {
            "time": lim_amount if lim_type == EffectLimit.TIME else None,
            "usage": lim_amount if lim_type == EffectLimit.USAGE else None,
        }
        level.add(pos, create_effect_fn(**extra, **kwargs))

    # 11) Non-essential positions (for enemies, hazards, moving boxes)
    open_non_essential: List[Position] = [
        p for p in open_positions if p not in essential_path
    ]
    rng.shuffle(open_non_essential)

    # 12) Boxes
    for pushable, speed in boxes:
        if not open_non_essential:
            break
        pos = open_non_essential.pop()
        box = create_box(pushable=pushable)
        if speed > 0:
            axis, direction = _random_axis_and_dir(rng)
            box.moving = Moving(axis=axis, direction=direction, speed=speed)
        level.add(pos, box)

    # 13) Enemies (wire pathfinding to agent by reference if requested)
    for dmg, lethal, mtype, mspeed in enemies:
        if not open_non_essential:
            break
        pos = open_non_essential.pop()

        # Explicit pathfinding via reference to the agent (authoring-time)
        path_type: Optional[PathfindingType] = None
        if mtype == MovementType.PATHFINDING_LINE:
            path_type = PathfindingType.STRAIGHT_LINE
        elif mtype == MovementType.PATHFINDING_PATH:
            path_type = PathfindingType.PATH

        # If path_type is set, wire target to agent; otherwise directional/static
        if path_type is not None:
            enemy = create_monster(
                damage=dmg, lethal=lethal, pathfind_target=agent, path_type=path_type
            )
        else:
            enemy = create_monster(damage=dmg, lethal=lethal)
            if mtype == MovementType.DIRECTIONAL and mspeed > 0:
                axis, direction = _random_axis_and_dir(rng)
                enemy.moving = Moving(axis=axis, direction=direction, speed=mspeed)

        level.add(pos, enemy)

    # 14) Hazards
    for app_name, dmg, lethal in hazards:
        if not open_non_essential:
            break
        level.add(
            open_non_essential.pop(),
            create_hazard(app_name, damage=dmg, lethal=lethal, priority=7),
        )

    # 15) Walls
    for pos in wall_positions:
        level.add(pos, create_wall())

    # Convert to immutable State (wiring is resolved inside to_state)
    return to_state(level)
