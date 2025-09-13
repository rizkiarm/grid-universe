from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import streamlit as st

from grid_universe.gym_env import GridUniverseEnv, ObsType
from grid_universe.examples.maze import (
    DEFAULT_BOXES,
    DEFAULT_ENEMIES,
    DEFAULT_HAZARDS,
    DEFAULT_POWERUPS,
    BoxSpec,
    EnemySpec,
    HazardSpec,
    MovementType,
    PowerupSpec,
)
from grid_universe.moves import MOVE_FN_REGISTRY, default_move_fn
from grid_universe.objectives import OBJECTIVE_FN_REGISTRY, default_objective_fn
from grid_universe.renderer.texture import (
    DEFAULT_TEXTURE_MAP,
    TEXTURE_MAP_REGISTRY,
    TextureMap,
)
from grid_universe.types import EffectLimit, EffectType, MoveFn, ObjectiveFn


@dataclass(frozen=True)
class Config:
    width: int
    height: int
    num_required_items: int
    num_rewardable_items: int
    num_portals: int
    num_doors: int
    health: int
    movement_cost: int
    required_item_reward: int
    rewardable_item_reward: int
    boxes: List[BoxSpec]  # (pushable: bool, speed: int)
    powerups: List[
        PowerupSpec
    ]  # ([EffectType], Optional[EffectLimit], Optional[int], Dict[str, Any])
    hazards: List[HazardSpec]  # (AppearanceName, damage: int, lethal: bool)
    enemies: List[EnemySpec]  # (damage: int, lethal: bool, MovementType, speed: int)
    wall_percentage: float
    move_fn: MoveFn
    objective_fn: ObjectiveFn
    seed: Optional[int]
    render_texture_map: TextureMap


def set_default_config() -> None:
    if "config" not in st.session_state:
        st.session_state["config"] = Config(
            width=10,
            height=10,
            num_required_items=3,
            num_rewardable_items=3,
            num_portals=1,
            num_doors=1,
            health=5,
            movement_cost=1,
            required_item_reward=10,
            rewardable_item_reward=10,
            boxes=list(DEFAULT_BOXES),
            powerups=list(DEFAULT_POWERUPS),
            hazards=list(DEFAULT_HAZARDS),
            enemies=list(DEFAULT_ENEMIES),
            wall_percentage=0.8,
            move_fn=default_move_fn,
            objective_fn=default_objective_fn,
            seed=None,
            render_texture_map=DEFAULT_TEXTURE_MAP,
        )
        st.session_state["maze_seed_counter"] = 0


def maze_size_section(config: Config) -> Tuple[int, int, float, int]:
    st.subheader("Maze Size & Structure")
    width: int = st.slider("Maze width", 6, 30, config.width, key="width")
    height: int = st.slider("Maze height", 6, 30, config.height, key="height")
    wall_percentage: float = st.slider(
        "Wall percentage (0=open, 1=perfect maze)",
        0.0,
        1.0,
        config.wall_percentage,
        step=0.01,
        key="wall_percentage",
    )
    movement_cost: int = st.slider(
        "Floor cost", 0, 10, config.movement_cost, key="movement_cost"
    )
    return width, height, wall_percentage, movement_cost


def items_section(config: Config) -> Tuple[int, int, int, int]:
    st.subheader("Items & Rewards")
    num_required_items: int = st.slider(
        "Required Items",
        0,
        10,
        config.num_required_items,
        key="num_required_items",
    )
    num_rewardable_items: int = st.slider(
        "Rewardable Items",
        0,
        10,
        config.num_rewardable_items,
        key="num_rewardable_items",
    )
    required_item_reward: int = st.number_input(
        "Reward per required item",
        min_value=0,
        value=config.required_item_reward,
        key="required_item_reward",
    )
    rewardable_item_reward: int = st.number_input(
        "Reward per rewardable item",
        min_value=0,
        value=config.rewardable_item_reward,
        key="rewardable_item_reward",
    )
    return (
        num_required_items,
        num_rewardable_items,
        required_item_reward,
        rewardable_item_reward,
    )


def agent_section(config: Config) -> int:
    st.subheader("Agent")
    health: int = st.slider("Agent Health", 1, 30, config.health, key="health")
    return health


def doors_portals_section(config: Config) -> Tuple[int, int]:
    st.subheader("Doors, Portals")
    num_portals: int = st.slider(
        "Portals (pairs)", 0, 5, config.num_portals, key="num_portals"
    )
    num_doors: int = st.slider("Doors", 0, 4, config.num_doors, key="num_doors")
    return num_portals, num_doors


def boxes_section(config: Config) -> List[BoxSpec]:
    """
    Edit boxes for BoxSpec := (pushable: bool, speed: int)
    """
    st.subheader("Boxes")
    boxes: List[BoxSpec] = list(config.boxes) if config.boxes else list(DEFAULT_BOXES)
    box_count: int = st.number_input(
        "Number of boxes", min_value=0, value=len(boxes), key="box_count"
    )
    edited: List[BoxSpec] = []
    for idx in range(box_count):
        pushable_default: bool = boxes[idx][0] if idx < len(boxes) else True
        speed_default: int = boxes[idx][1] if idx < len(boxes) else 0

        st.markdown(f"**Box #{idx + 1}**")
        cols = st.columns([1, 1])
        with cols[0]:
            pushable = st.checkbox(
                "Pushable?", value=pushable_default, key=f"box_pushable_{idx}"
            )
        with cols[1]:
            speed = st.number_input(
                "Speed", min_value=0, value=speed_default, key=f"box_speed_{idx}"
            )
        edited.append((bool(pushable), int(speed)))
    return edited


def hazards_section() -> List[HazardSpec]:
    st.subheader("Hazards")
    hazards: List[HazardSpec] = []
    for hazard_type, hazard_damage, hazard_lethal in DEFAULT_HAZARDS:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            count: int = st.number_input(
                f"{hazard_type.value.title()} count",
                min_value=0,
                value=1,
                key=f"hazard_count_{hazard_type.value}",
            )
        with col2:
            lethal: bool = st.checkbox(
                "Lethal?", value=hazard_lethal, key=f"hazard_lethal_{hazard_type.value}"
            )
        with col3:
            if not lethal:
                damage: int = st.number_input(
                    "Damage",
                    min_value=1,
                    value=hazard_damage,
                    key=f"hazard_damage_{hazard_type.value}",
                )
            else:
                st.markdown("Lethal")
                damage = 0
        hazards.extend([(hazard_type, int(damage), bool(lethal))] * count)
    return hazards


def powerups_section() -> List[PowerupSpec]:
    """
    Edit powerups:
      ([EffectType], Optional[EffectLimit], Optional[int], Dict[str, Any])
    For SPEED, expose 'multiplier' option.
    """
    st.subheader("Powerups")
    powerups: List[PowerupSpec] = []
    for idx, (
        effect_type,
        limit_type_default,
        limit_amount_default,
        option_default,
    ) in enumerate(DEFAULT_POWERUPS):
        label = effect_type.name.title()
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            count: int = st.number_input(
                f"{label} count", min_value=0, value=1, key=f"powerup_count_{idx}"
            )
        with col2:
            limit_choice = st.selectbox(
                "Limit Type",
                ["unlimited", "time", "usage"],
                index=0
                if limit_type_default is None
                else (1 if limit_type_default == EffectLimit.TIME else 2),
                key=f"powerup_limit_type_{idx}",
            )
            updated_limit_type: Optional[EffectLimit] = None
            if limit_choice == "time":
                updated_limit_type = EffectLimit.TIME
            elif limit_choice == "usage":
                updated_limit_type = EffectLimit.USAGE
            else:
                updated_limit_type = None
        with col3:
            if updated_limit_type is None:
                st.markdown("Unlimited")
                updated_limit_amount: Optional[int] = None
            else:
                default_amt = (
                    limit_amount_default if limit_amount_default is not None else 10
                )
                updated_limit_amount = int(
                    st.number_input(
                        "Limit Amount",
                        min_value=1,
                        value=default_amt,
                        key=f"powerup_limit_amount_{idx}",
                    )
                )
        with col4:
            updated_option = dict(option_default)
            if effect_type == EffectType.SPEED:
                multiplier_default = int(option_default.get("multiplier", 2))
                updated_option["multiplier"] = int(
                    st.number_input(
                        "Speed x",
                        min_value=2,
                        value=multiplier_default,
                        key=f"powerup_speed_mult_{idx}",
                    )
                )
            else:
                st.markdown("No extra option")
        if count > 0:
            powerups.extend(
                [
                    (
                        effect_type,
                        updated_limit_type,
                        updated_limit_amount,
                        updated_option,
                    )
                ]
                * count
            )
    return powerups


def enemies_section(config: Config) -> List[EnemySpec]:
    """
    Edit enemies:
      (damage: int, lethal: bool, movement_type: MovementType, speed: int)
    """
    st.subheader("Enemies")
    enemies: List[EnemySpec] = (
        list(config.enemies) if config.enemies else list(DEFAULT_ENEMIES)
    )
    enemy_count: int = st.number_input(
        "Number of enemies", min_value=0, value=len(enemies), key="enemy_count"
    )
    edited: List[EnemySpec] = []
    for idx in range(enemy_count):
        damage_default: int = enemies[idx][0] if idx < len(enemies) else 3
        lethal_default: bool = enemies[idx][1] if idx < len(enemies) else False
        movement_type_default: MovementType = (
            enemies[idx][2] if idx < len(enemies) else MovementType.STATIC
        )
        speed_default: int = enemies[idx][3] if idx < len(enemies) else 1

        st.markdown(f"**Enemy #{idx + 1}**")
        cols = st.columns([1, 1, 1, 1])
        with cols[0]:
            lethal = st.checkbox(
                "Lethal?", value=lethal_default, key=f"enemy_lethal_{idx}"
            )
        with cols[1]:
            damage = (
                0
                if lethal
                else int(
                    st.number_input(
                        "Damage",
                        min_value=1,
                        value=damage_default,
                        key=f"enemy_damage_{idx}",
                    )
                )
            )
        with cols[2]:
            movement_type = st.selectbox(
                "Movement Type",
                list(MovementType),
                index=list(MovementType).index(movement_type_default),
                key=f"enemy_movement_type_{idx}",
            )
        with cols[3]:
            if movement_type == MovementType.STATIC:
                st.markdown("Static")
                speed = 0
            else:
                speed = int(
                    st.number_input(
                        "Movement Speed",
                        min_value=1,
                        value=max(1, speed_default),
                        key=f"enemy_movement_speed_{idx}",
                    )
                )
        edited.append((int(damage), bool(lethal), movement_type, int(speed)))
    return edited


def movement_section(config: Config) -> MoveFn:
    st.subheader("Gameplay Movement")
    move_fn_names: List[str] = list(MOVE_FN_REGISTRY.keys())
    move_fn_label: str = st.selectbox(
        "Movement rule",
        move_fn_names,
        index=move_fn_names.index(
            next(k for k, v in MOVE_FN_REGISTRY.items() if v is config.move_fn)
        ),
        key="move_fn",
    )
    move_fn: MoveFn = MOVE_FN_REGISTRY[move_fn_label]
    return move_fn


def objective_section(config: Config) -> ObjectiveFn:
    st.subheader("Gameplay Objective")
    objective_fn_names: List[str] = list(OBJECTIVE_FN_REGISTRY.keys())
    objective_fn_label: str = st.selectbox(
        "Objective",
        objective_fn_names,
        index=objective_fn_names.index(
            next(
                k for k, v in OBJECTIVE_FN_REGISTRY.items() if v is config.objective_fn
            )
        ),
        key="objective_fn",
    )
    objective_fn: ObjectiveFn = OBJECTIVE_FN_REGISTRY[objective_fn_label]
    return objective_fn


def seed_section() -> int:
    st.subheader("Random seed")
    seed: int = st.number_input("Random seed", min_value=0, value=0, key="maze_seed")
    return seed


def texture_map_section(config: Config) -> TextureMap:
    st.subheader("Texture Map")
    texture_map_names: List[str] = list(TEXTURE_MAP_REGISTRY.keys())
    texture_map_label: str = st.selectbox(
        "Texture Map",
        texture_map_names,
        index=texture_map_names.index(
            next(
                k
                for k, v in TEXTURE_MAP_REGISTRY.items()
                if v is config.render_texture_map
            )
        ),
        key="texture_map",
    )
    texture_map: TextureMap = TEXTURE_MAP_REGISTRY[texture_map_label]
    return texture_map


def get_config_from_widgets() -> Config:
    """
    Collect user inputs from Streamlit widgets and return a Config.
    """
    config: Config = st.session_state["config"]

    width, height, wall_percentage, movement_cost = maze_size_section(config)
    (
        num_required_items,
        num_rewardable_items,
        required_item_reward,
        rewardable_item_reward,
    ) = items_section(config)
    health: int = agent_section(config)
    num_portals, num_doors = doors_portals_section(config)
    boxes: List[BoxSpec] = boxes_section(config)
    hazards: List[HazardSpec] = hazards_section()
    powerups: List[PowerupSpec] = powerups_section()
    enemies: List[EnemySpec] = enemies_section(config)
    move_fn: MoveFn = movement_section(config)
    objective_fn: ObjectiveFn = objective_section(config)
    seed: int = seed_section()
    render_texture_map: TextureMap = texture_map_section(config)

    return Config(
        width=width,
        height=height,
        num_required_items=num_required_items,
        num_rewardable_items=num_rewardable_items,
        num_portals=num_portals,
        num_doors=num_doors,
        health=health,
        movement_cost=movement_cost,
        required_item_reward=required_item_reward,
        rewardable_item_reward=rewardable_item_reward,
        boxes=boxes,
        powerups=powerups,
        hazards=hazards,
        enemies=enemies,
        wall_percentage=wall_percentage,
        move_fn=move_fn,
        objective_fn=objective_fn,
        seed=seed,
        render_texture_map=render_texture_map,
    )


def make_env_and_reset(
    config: Config,
) -> Tuple[GridUniverseEnv, ObsType, Dict[str, object]]:
    """
    Build a GridUniverseEnv from Config, reset it, and store runtime objects in session_state.
    """
    config_dict = dataclasses.asdict(config)
    env = GridUniverseEnv(render_mode="texture", **config_dict)
    obs, info = env.reset(seed=config.seed)
    st.session_state["env"] = env
    st.session_state["obs"] = obs
    st.session_state["info"] = info
    st.session_state["total_reward"] = 0.0
    st.session_state["prev_health"] = config.health
    return env, obs, info
