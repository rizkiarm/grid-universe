import dataclasses
import streamlit as st

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from grid_universe.components import AppearanceName
from grid_universe.gym_env import GridUniverseEnv, ObsType
from grid_universe.levels.maze import (
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
    TEXTURE_MAP_REGISTRY,
    DEFAULT_TEXTURE_MAP,
    TextureMap,
)
from grid_universe.types import EffectLimit, MoveFn, ObjectiveFn


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
    boxes: List[BoxSpec]
    powerups: List[PowerupSpec]
    hazards: List[HazardSpec]
    enemies: List[EnemySpec]
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
    st.subheader("Boxes")
    boxes: List[BoxSpec] = list(DEFAULT_BOXES)
    box_count: int = st.number_input(
        "Number of boxes", min_value=0, value=len(boxes), key="box_count"
    )
    if box_count > 0:
        for idx in range(box_count):
            box: BoxSpec = (AppearanceName.BOX, True, 0)
            if idx < len(boxes):
                box = boxes[idx]
            appearance, pushable, speed = box

            st.markdown(f"**Box #{idx + 1}**")
            cols = st.columns([1, 1])
            with cols[0]:
                pushable = st.checkbox(
                    "Pushable?", value=pushable, key=f"box_pushable_{idx}"
                )
            with cols[1]:
                speed = st.number_input(
                    "Speed", min_value=0, value=speed, key=f"box_speed_{idx}"
                )
            if idx < len(boxes):
                boxes[idx] = (appearance, pushable, speed)
            else:
                boxes.append((appearance, pushable, speed))
    return boxes


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
        hazards.extend([(hazard_type, damage, lethal)] * count)
    return hazards


def powerups_section() -> List[PowerupSpec]:
    st.subheader("Powerups")
    powerups: List[PowerupSpec] = []
    for (
        pu_appearance,
        pu_effects,
        pu_limit_type,
        pu_limit_amount,
        pu_option,
    ) in DEFAULT_POWERUPS:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            count: int = st.number_input(
                f"{pu_appearance.value.replace('_', ' ').capitalize()} count",
                min_value=0,
                value=1,
                key=f"powerup_count_{pu_appearance.value}",
            )
        with col2:
            limit_option: str = st.selectbox(
                "Limit Type",
                ["time", "usage", "unlimited"],
                index=[EffectLimit.TIME, EffectLimit.USAGE, None].index(pu_limit_type),
                key=f"powerup_limit_type_{pu_appearance.value}",
            )
            updated_limit_type: Optional[EffectLimit] = None
            if limit_option == "time":
                updated_limit_type = EffectLimit.TIME
            elif limit_option == "usage":
                updated_limit_type = EffectLimit.USAGE
            else:
                updated_limit_type = None  # Irrelevant for unlimited
        with col3:
            if limit_option != "unlimited":
                updated_limit_amount: Optional[int] = st.number_input(
                    "Limit Amount",
                    min_value=1,
                    value=pu_limit_amount,
                    key=f"powerup_limit_amount_{pu_appearance.value}",
                )
            else:
                st.markdown("Unlimited")
                updated_limit_amount = None
        if count > 0:
            powerups.extend(
                [
                    (
                        pu_appearance,
                        pu_effects,
                        updated_limit_type,
                        updated_limit_amount,
                        pu_option,
                    )
                ]
                * count
            )
    return powerups


def enemies_section(config: Config) -> List[EnemySpec]:
    st.subheader("Enemies")
    enemies: List[EnemySpec] = list(DEFAULT_ENEMIES)  # DEFAULT_ENEMIES
    enemy_count: int = st.number_input(
        "Number of enemies", min_value=0, value=len(enemies), key="enemy_count"
    )
    if enemy_count > 0:
        for idx in range(enemy_count):
            enemy: EnemySpec = (
                AppearanceName.MONSTER,
                2,
                False,
                MovementType.STATIC,
                1,
            )
            if idx < len(enemies):
                enemy = enemies[idx]
            appearance, damage, lethal, movement_type, movement_speed = enemy

            st.markdown(f"**Enemy #{idx + 1}**")
            cols = st.columns([1, 1, 1, 1])
            with cols[0]:
                lethal = st.checkbox("Lethal?", value=lethal, key=f"enemy_lethal_{idx}")
            with cols[1]:
                if not lethal:
                    damage = st.number_input(
                        "Damage", min_value=1, value=damage, key=f"enemy_damage_{idx}"
                    )
                else:
                    st.markdown("Lethal")
                    damage = 0
            with cols[2]:
                movement_type: str = st.selectbox(
                    "Movement Type",
                    MovementType,
                    index=[e.value for e in MovementType].index(movement_type),
                    key=f"enemy_movement_type_{idx}",
                )
            with cols[3]:
                if movement_type != MovementType.STATIC:
                    movement_speed = st.number_input(
                        "Movement Speed",
                        min_value=1,
                        value=movement_speed,
                        key=f"enemy_movement_speed_{idx}",
                    )
                else:
                    st.markdown("Static")
                    movement_speed = 0
            if idx < len(enemies):
                enemies[idx] = (
                    appearance,
                    damage,
                    lethal,
                    movement_type,
                    movement_speed,
                )
            else:
                enemies.append(
                    (appearance, damage, lethal, movement_type, movement_speed)
                )
    return enemies


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
    seed: int = st.number_input("Random seed", min_value=0, key="maze_seed")
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
    config_dict = dataclasses.asdict(config)
    env = GridUniverseEnv(render_mode="texture", **config_dict)
    obs, info = env.reset(seed=config.seed)
    st.session_state["env"] = env
    st.session_state["obs"] = obs
    st.session_state["info"] = info
    st.session_state["total_reward"] = 0.0
    st.session_state["prev_health"] = config.health
    return env, obs, info
