from __future__ import annotations
from typing import List

from grid_universe.levels.grid import Level
from grid_universe.levels.convert import to_state
from grid_universe.moves import default_move_fn
from grid_universe.objectives import default_objective_fn, exit_objective_fn
from grid_universe.state import State
from grid_universe.components.properties import AppearanceName, Moving, MovingAxis
from grid_universe.levels.factories import (
    create_floor,
    create_wall,
    create_agent,
    create_exit,
    create_coin,
    create_core,
    create_key,
    create_door,
    create_portal,
    create_box,
    create_monster,
    create_hazard,
    create_speed_effect,  # Boots
    create_immunity_effect,  # Shield
    create_phasing_effect,  # Ghost
)

# -------------------------
# Cost policy constants (env scoring)
# -------------------------
# Base per-tile step cost (applied once per logical action by tile_cost_system).
# Must be > 1 so that a coin can be a strictly cheaper step (reward into cost reduction).
TILE_COST = 3

# Coin reward acts as per-step cost reduction when stepping on it (non-collectible reward tile).
# Must satisfy: 0 < COIN_REWARD < TILE_COST.
COIN_REWARD = 2

# Required core reward must be 0 (objective only, no scoring bonus).
CORE_REWARD = 0


# -------------------------
# Helpers
# -------------------------


def _floors(level: Level, cost: int = TILE_COST) -> None:
    """Fill the grid with floor tiles carrying uniform Cost=cost per step."""
    for y in range(level.height):
        for x in range(level.width):
            level.add((x, y), create_floor(cost_amount=cost))


def _border(level: Level) -> None:
    """Draw wall border (background walls)."""
    for x in range(level.width):
        level.add((x, 0), create_wall())
        level.add((x, level.height - 1), create_wall())
    for y in range(level.height):
        level.add((0, y), create_wall())
        level.add((level.width - 1, y), create_wall())


def _place_coin_tile(
    level: Level, pos: tuple[int, int], reward: int = COIN_REWARD
) -> None:
    """Add a non-collectible coin tile that grants a step reward.

    Converts a normally collectible coin entity into a stationary reward tile so
    that the net step cost becomes ``TILE_COST - reward`` (still positive) when
    the agent moves onto it.

    Args:
        level (Level): Level being authored.
        pos (tuple[int, int]): Tile coordinate.
        reward (int): Reward amount (must satisfy ``0 < reward < TILE_COST``).
    """
    coin = create_coin(reward=reward)  # factory sets Collectible + Rewardable
    coin.collectible = (
        None  # make it non-collectible so reward triggers as tile reward, not pickup
    )
    level.add(pos, coin)


# -------------------------
# Levels L0..L9 (mechanic ramp-up)
# -------------------------


def build_level_basic_movement(seed: int = 100) -> State:
    """L0: Movement smoke test (Exit).

    Args:
        seed (int): Deterministic seed stored on resulting ``State`` (used by rendering / RNG subsystems).

    Returns:
        State: Authored immutable state.
    """
    w, h = 7, 5
    lvl = Level(
        w, h, move_fn=default_move_fn, objective_fn=exit_objective_fn, seed=seed
    )
    _floors(lvl)
    lvl.add((1, h // 2), create_agent(health=5))
    lvl.add((w - 2, h // 2), create_exit())
    # corridor wall
    for y in range(h):
        if y != h // 2:
            lvl.add((w // 2, y), create_wall())
    return to_state(lvl)


def build_level_maze_turns(seed: int = 101) -> State:
    """L1: Basic maze turns (Exit).

    Args:
        seed (int): Deterministic seed stored on resulting ``State``.

    Returns:
        State: Authored immutable state.
    """
    w, h = 9, 7
    lvl = Level(
        w, h, move_fn=default_move_fn, objective_fn=exit_objective_fn, seed=seed
    )
    _floors(lvl)
    _border(lvl)
    for x in range(2, w - 2):
        lvl.add((x, 2), create_wall())
    for x in range(2, w - 2):
        if x != w // 2:
            lvl.add((x, h - 3), create_wall())
    lvl.add((1, 1), create_agent(health=5))
    lvl.add((w - 2, h - 2), create_exit())
    return to_state(lvl)


def build_level_optional_coin(seed: int = 102) -> State:
    """L2: Optional coin path (Exit).

    Coin tiles reduce net cost along that route encouraging detour.

    Args:
        seed (int): Deterministic seed stored on resulting ``State``.

    Returns:
        State: Authored immutable state.
    """
    w, h = 9, 7
    lvl = Level(
        w, h, move_fn=default_move_fn, objective_fn=exit_objective_fn, seed=seed
    )
    _floors(lvl)
    _border(lvl)
    for x in range(2, w - 2):
        lvl.add((x, 2), create_wall())
    for x in range(2, w - 2):
        if x != w // 2:
            lvl.add((x, h - 3), create_wall())
    lvl.add((1, 1), create_agent(health=5))
    lvl.add((w - 2, h - 2), create_exit())
    # Cheaper side path using coin tiles (0 < COIN_REWARD < TILE_COST ⇒ A* prefers this path)
    for x in range(2, w - 2, 2):
        _place_coin_tile(lvl, (x, 1))
    return to_state(lvl)


def build_level_required_one(seed: int = 103) -> State:
    """L3: One required core (Collect-then-Exit).

    Args:
        seed (int): Deterministic seed stored on resulting ``State``.

    Returns:
        State: Authored immutable state.
    """
    w, h = 9, 7
    lvl = Level(
        w, h, move_fn=default_move_fn, objective_fn=default_objective_fn, seed=seed
    )
    _floors(lvl)
    _border(lvl)
    for y in range(1, h - 1):
        if y != h // 2:
            lvl.add((w // 2, y), create_wall())
    lvl.add((1, h // 2), create_agent(health=5))
    lvl.add((w - 2, h // 2), create_exit())
    core = create_core(reward=CORE_REWARD, required=True)  # reward=0
    lvl.add((w // 2 - 1, h // 2 - 1), core)
    return to_state(lvl)


def build_level_required_two(seed: int = 104) -> State:
    """L4: Two required cores and backtracking (Collect-then-Exit).

    Args:
        seed (int): Deterministic seed stored on resulting ``State``.

    Returns:
        State: Authored immutable state.
    """
    w, h = 11, 9
    lvl = Level(
        w, h, move_fn=default_move_fn, objective_fn=default_objective_fn, seed=seed
    )
    _floors(lvl)
    _border(lvl)
    midx, midy = w // 2, h // 2
    for x in range(1, w - 1):
        for y in range(1, h - 1):
            if x != midx and y != midy:
                lvl.add((x, y), create_wall())
    # carve openings around center
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        lvl.add((midx + dx, midy + dy), create_floor(cost_amount=TILE_COST))
    lvl.add((1, midy), create_agent(health=6))
    lvl.add((w - 2, midy), create_exit())
    lvl.add((midx, 1), create_core(reward=CORE_REWARD, required=True))  # reward=0
    lvl.add((midx, h - 2), create_core(reward=CORE_REWARD, required=True))  # reward=0
    return to_state(lvl)


def build_level_key_door(seed: int = 105) -> State:
    """L5: Key–Door gating (Exit).

    Args:
        seed (int): Deterministic seed stored on resulting ``State``.

    Returns:
        State: Authored immutable state.
    """
    w, h = 11, 9
    lvl = Level(
        w, h, move_fn=default_move_fn, objective_fn=exit_objective_fn, seed=seed
    )
    _floors(lvl)
    for y in range(h):
        if y != h // 2:
            lvl.add((w // 2, y), create_wall())
    lvl.add((1, h // 2), create_agent(health=5))
    lvl.add((w - 2, h // 2), create_exit())
    lvl.add((2, h // 2 - 1), create_key(key_id="alpha"))
    lvl.add((w // 2, h // 2), create_door(key_id="alpha"))
    return to_state(lvl)


def build_level_hazard_detour(seed: int = 106) -> State:
    """L6: Hazard detour (damage=2) (Exit).

    Hazard imposes only base step cost but reduces health on contact.

    Args:
        seed (int): Deterministic seed stored on resulting ``State``.

    Returns:
        State: Authored immutable state.
    """
    w, h = 11, 9
    lvl = Level(
        w, h, move_fn=default_move_fn, objective_fn=exit_objective_fn, seed=seed
    )
    _floors(lvl)
    lvl.add((1, h // 2), create_agent(health=6))
    lvl.add((w - 2, h // 2), create_exit())
    # Central hazard (2 dmg); side wall encourages detour, but cost remains uniform except coin tiles
    lvl.add(
        (w // 2 - 1, h // 2),
        create_hazard(AppearanceName.SPIKE, damage=2, lethal=False),
    )
    for y in range(1, h - 1):
        if y != h // 2:
            lvl.add((w // 2 - 1, y), create_wall())
    return to_state(lvl)


def build_level_portal_shortcut(seed: int = 107) -> State:
    """L7: Portal pair shortcut (Exit).

    Args:
        seed (int): Deterministic seed stored on resulting ``State``.

    Returns:
        State: Authored immutable state.
    """
    w, h = 11, 9
    lvl = Level(
        w, h, move_fn=default_move_fn, objective_fn=exit_objective_fn, seed=seed
    )
    _floors(lvl)
    lvl.add((1, h // 2), create_agent(health=5))
    lvl.add((w - 2, h // 2), create_exit())
    p1 = create_portal()
    p2 = create_portal(pair=p1)
    lvl.add((2, 1), p1)
    lvl.add((w - 1, h // 2), p2)
    for x in range(3, w - 3):
        lvl.add((x, h // 2 - 1), create_wall())
    return to_state(lvl)


def build_level_pushable_box(seed: int = 108) -> State:
    """L8: Pushable box in narrow corridor (Exit).

    Args:
        seed (int): Deterministic seed stored on resulting ``State``.

    Returns:
        State: Authored immutable state.
    """
    w, h = 11, 9
    lvl = Level(
        w, h, move_fn=default_move_fn, objective_fn=exit_objective_fn, seed=seed
    )
    _floors(lvl)
    for y in range(h):
        if y != h // 2:
            lvl.add((w // 2, y), create_wall())
    lvl.add((1, h // 2), create_agent(health=5))
    lvl.add((w - 2, h // 2), create_exit())
    lvl.add((w // 2 - 1, h // 2), create_box(pushable=True))
    return to_state(lvl)


def build_level_enemy_patrol(seed: int = 109) -> State:
    """L9: Enemy patrol (damage=1) with safe avoidance (Exit).

    Args:
        seed (int): Deterministic seed stored on resulting ``State``.

    Returns:
        State: Authored immutable state.
    """
    w, h = 13, 9
    lvl = Level(
        w, h, move_fn=default_move_fn, objective_fn=exit_objective_fn, seed=seed
    )
    _floors(lvl)
    lvl.add((2, h // 2), create_agent(health=1))
    lvl.add((w - 2, h // 2), create_exit())
    for y in range(h):
        if y not in [h // 2, h // 2 + 1]:
            lvl.add((w // 2, y), create_wall())
            lvl.add((w // 2 + 1, y), create_wall())
    enemy1 = create_monster(damage=1, lethal=False, moving_axis=MovingAxis.VERTICAL, moving_direction=1, moving_bounce=True, moving_speed=1)
    enemy2 = create_monster(damage=1, lethal=False, moving_axis=MovingAxis.VERTICAL, moving_direction=1, moving_bounce=True, moving_speed=1)
    lvl.add((w // 2, h // 2), enemy1)
    lvl.add((w // 2 + 1, h // 2), enemy2)
    return to_state(lvl)


# -------------------------
# Power-ups introduced one-by-one (useful)
# -------------------------


def build_level_power_shield(seed: int = 110) -> State:
    """L10: Shield (Immunity 5 uses) — necessary at a choke.

    Unavoidable hazard (2 dmg) in a 1-wide corridor; agent has 2 HP. Without the
    shield effect the hazard would be lethal.

    Args:
        seed (int): Deterministic seed stored on resulting ``State``.

    Returns:
        State: Authored immutable state.
    """
    w, h = 11, 9
    lvl = Level(
        w, h, move_fn=default_move_fn, objective_fn=exit_objective_fn, seed=seed
    )
    _floors(lvl)
    lvl.add((1, h // 2), create_agent(health=2))
    lvl.add((w - 2, h // 2), create_exit())
    for y in range(h):
        if y != h // 2:
            lvl.add((w // 2, y), create_wall())
    lvl.add((2, h // 2 - 3), create_immunity_effect(usage=5))  # Shield
    lvl.add(
        (w // 2, h // 2),
        create_hazard(AppearanceName.SPIKE, damage=2, lethal=False),
    )
    return to_state(lvl)


def build_level_power_ghost(seed: int = 111) -> State:
    """L11: Ghost (Phasing 5 turns) — necessary to pass a door; no key provided.

    Single corridor blocked by a locked door; phasing allows bypassing blocking.

    Args:
        seed (int): Deterministic seed stored on resulting ``State``.

    Returns:
        State: Authored immutable state.
    """
    w, h = 13, 9
    lvl = Level(
        w, h, move_fn=default_move_fn, objective_fn=exit_objective_fn, seed=seed
    )
    _floors(lvl)
    lvl.add((1, h // 2), create_agent(health=5))
    lvl.add((w - 2, h // 2), create_exit())
    for y in range(h):
        if y != h // 2:
            lvl.add((w // 2, y), create_wall())
    lvl.add((2, h // 2 - 3), create_phasing_effect(time=5))  # Ghost
    lvl.add((w // 2, h // 2), create_door(key_id="alpha"))  # no key anywhere
    return to_state(lvl)


def build_level_power_boots(seed: int = 112) -> State:
    """L12: Boots (Speed ×2, 5 turns) — useful to cross a 2-tile patrol window safely.

    With 2× speed the agent traverses both tiles of a patrol gap in one action.

    Args:
        seed (int): Deterministic seed stored on resulting ``State``.

    Returns:
        State: Authored immutable state.
    """
    w, h = 13, 9
    lvl = Level(
        w, h, move_fn=default_move_fn, objective_fn=exit_objective_fn, seed=seed
    )
    _floors(lvl)
    lvl.add((1, h // 2), create_agent(health=1))
    lvl.add((w - 2, h // 2), create_exit())
    for y in range(h):
        if y not in [h // 2, h // 2 + 1]:
            lvl.add((w // 2, y), create_wall())
            lvl.add((w // 2 + 1, y), create_wall())
            lvl.add((w // 2 + 2, y), create_wall())
    lvl.add(
        (w // 2 - 1, h // 2 + 1), create_speed_effect(multiplier=2, time=5)
    )  # Boots
    enemy1 = create_monster(damage=1, lethal=False, moving_axis=MovingAxis.VERTICAL, moving_direction=1, moving_bounce=True, moving_speed=1)
    enemy2 = create_monster(damage=1, lethal=False, moving_axis=MovingAxis.VERTICAL, moving_direction=1, moving_bounce=True, moving_speed=1)
    enemy3 = create_monster(damage=1, lethal=False, moving_axis=MovingAxis.VERTICAL, moving_direction=1, moving_bounce=True, moving_speed=1)
    lvl.add((w // 2, h // 2), enemy1)
    lvl.add((w // 2 + 1, h // 2), enemy2)
    lvl.add((w // 2 + 2, h // 2), enemy3)
    return to_state(lvl)


# -------------------------
# L13: Capstone — integrated deterministic puzzle (Collect-then-Exit)
# One of each capped mechanic: key–door, portal pair, hazard, enemy patrol, pushable box,
# plus one power-up (Shield). Required cores have reward=0 (objective only).
# -------------------------


def build_level_capstone(seed: int = 113) -> State:
    """L13 (Capstone): Integrated puzzle (Collect-then-Exit).

    Components:
        * 2 required cores (reward=0)
        * Key–Door pair (gating)
        * Portal pair (shortcut)
        * Hazard (2 dmg) encouraging careful routing (no extra step cost)
        * Patrolling enemy (1 dmg, bounce)
        * Pushable box
        * Shield power-up (5 uses)

    All tiles use base cost ``TILE_COST``; coins omitted so routing is mechanical.

    Returns:
        State: Authored immutable state.
    """
    w, h = 13, 11
    lvl = Level(
        w, h, move_fn=default_move_fn, objective_fn=default_objective_fn, seed=seed
    )
    _floors(lvl)
    _border(lvl)

    # Agent and Exit
    lvl.add((1, h // 2), create_agent(health=6))
    lvl.add((w - 2, h // 2), create_exit())

    # Two required cores (reward=0) on different wings
    lvl.add(
        (w // 2 - 2, 2), create_core(reward=CORE_REWARD, required=True)
    )  # top-left wing
    lvl.add(
        (w // 2 + 2, h - 3), create_core(reward=CORE_REWARD, required=True)
    )  # bottom-right wing

    # Portal pair (non-local transition that helps cut a detour)
    p1 = create_portal()
    p2 = create_portal(pair=p1)
    lvl.add((3, 1), p1)
    lvl.add((w - 4, h - 2), p2)

    # Key–Door gating on the main spine
    lvl.add(
        (w // 2, h // 2), create_door(key_id="alpha")
    )  # door blocks a straight line
    lvl.add(
        (w // 2 - 3, h // 2 - 1), create_key(key_id="alpha")
    )  # key on a side alcove

    # One hazard (no cost, 2 damage) placed near a tempting shortcut
    lvl.add(
        (w // 2 + 1, h // 2 + 1),
        create_hazard(AppearanceName.SPIKE, damage=2, lethal=False),
    )

    # One pushable box blocking a narrow passage (simple push out of the way)
    lvl.add((w // 2 - 1, h // 2), create_box(pushable=True))

    # One patrolling enemy (bounce) guarding part of the route
    enemy = create_monster(damage=1, lethal=False)
    enemy.moving = Moving(axis=MovingAxis.VERTICAL, direction=1, speed=1, bounce=True)
    lvl.add((w // 2 + 3, h // 2), enemy)

    # One Shield power-up to mitigate an otherwise likely contact
    lvl.add((2, h // 2 + 2), create_immunity_effect(usage=5))

    return to_state(lvl)


# -------------------------
# Suite builder
# -------------------------


def generate_task_suite(
    base_seed: int | None = None,
    *,
    seed_list: List[int] | None = None,
) -> List[State]:
    """Return ordered suite of authored levels (L0..L13) with configurable seeds.

    Seeding strategy precedence:
        1. ``seed_list`` if provided (must have length 14)
        2. ``base_seed`` (seeds become ``base_seed + index``)
        3. Each builder's default seed constant (backwards compatible)

    Args:
        base_seed (int | None): Optional base; offsets determine per-level seeds.
        seed_list (list[int] | None): Explicit seeds for each level (length must be 14).

    Returns:
        list[State]: Immutable states for each level.
    """
    builders = [
        build_level_basic_movement,  # L0
        build_level_maze_turns,  # L1
        build_level_optional_coin,  # L2 (coin tiles reduce net step cost)
        build_level_required_one,  # L3
        build_level_required_two,  # L4
        build_level_key_door,  # L5
        build_level_hazard_detour,  # L6
        build_level_portal_shortcut,  # L7
        build_level_pushable_box,  # L8
        build_level_enemy_patrol,  # L9
        build_level_power_shield,  # L10 (Shield useful/necessary)
        build_level_power_ghost,  # L11 (Ghost necessary)
        build_level_power_boots,  # L12 (Boots strongly useful)
        build_level_capstone,  # L13 (capstone integration)
    ]

    if seed_list is not None:
        if len(seed_list) != len(builders):  # defensive check
            raise ValueError(
                f"seed_list must have length {len(builders)}; got {len(seed_list)}"
            )
        return [builder(seed) for builder, seed in zip(builders, seed_list)]

    if base_seed is not None:
        return [builder(base_seed + idx) for idx, builder in enumerate(builders)]

    # Default behavior keeps historical fixed seeds
    return [builder() for builder in builders]
