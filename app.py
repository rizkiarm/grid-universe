from dataclasses import dataclass, replace
import dataclasses
from pyrsistent import thaw
import streamlit as st
import numpy as np
from typing import List, Tuple, Dict, Optional
from st_keyup import st_keyup  # type: ignore
from grid_universe.components import Inventory
from grid_universe.components.properties.appearance import AppearanceName
from grid_universe.components.properties.status import Status
from grid_universe.gym_env import GridUniverseEnv, MazeEnvAction, ObsType
from grid_universe.levels.maze import (
    DEFAULT_BOXES,
    DEFAULT_HAZARDS,
    DEFAULT_POWERUPS,
    DEFAULT_ENEMIES,
    BoxSpec,
    EnemySpec,
    HazardSpec,
    MovementType,
    PowerupSpec,
)
from grid_universe.moves import MOVE_FN_REGISTRY, default_move_fn
from grid_universe.objectives import OBJECTIVE_FN_REGISTRY, default_objective_fn
from grid_universe.state import State
from grid_universe.types import (
    EffectType,
    EffectLimit,
    EffectLimitAmount,
    EntityID,
    MoveFn,
    ObjectiveFn,
)

ITEM_ICONS: Dict[AppearanceName, str] = {
    AppearanceName.KEY: "🔑",
    AppearanceName.COIN: "🪙",
    AppearanceName.CORE: "🌟",
}

POWERUP_ICONS: Dict[AppearanceName, str] = {
    AppearanceName.GHOST: "👻",
    AppearanceName.SHIELD: "🛡️",
    AppearanceName.BOOTS: "⚡",
}

st.set_page_config(layout="wide", page_title="Grid Universe")
st.markdown(
    """
    <style>
        header, footer, #MainMenu { visibility: hidden; }
        .stMainBlockContainer {
            padding-top: 0;
            padding-bottom: 0;
        }
        .stToastContainer {
            align-items: center;
        }
    </style>
""",
    unsafe_allow_html=True,
)


@dataclass(frozen=True)
class MazeConfig:
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


def set_default_config() -> None:
    if "maze_config" not in st.session_state:
        st.session_state["maze_config"] = MazeConfig(
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
        )
        st.session_state["maze_seed_counter"] = 0


def get_config_from_widgets() -> MazeConfig:
    maze_config: MazeConfig = st.session_state["maze_config"]

    st.subheader("Maze Size & Structure")
    width: int = st.slider("Maze width", 6, 30, maze_config.width, key="width")
    height: int = st.slider("Maze height", 6, 30, maze_config.height, key="height")
    wall_percentage: float = st.slider(
        "Wall percentage (0=open, 1=perfect maze)",
        0.0,
        1.0,
        maze_config.wall_percentage,
        step=0.01,
        key="wall_percentage",
    )
    movement_cost: int = st.slider(
        "Floor cost", 0, 10, maze_config.movement_cost, key="movement_cost"
    )

    st.subheader("Items & Rewards")
    num_required_items: int = st.slider(
        "Required Items",
        0,
        10,
        maze_config.num_required_items,
        key="num_required_items",
    )
    num_rewardable_items: int = st.slider(
        "Rewardable Items",
        0,
        10,
        maze_config.num_rewardable_items,
        key="num_rewardable_items",
    )
    required_item_reward: int = st.number_input(
        "Reward per required item",
        min_value=0,
        value=maze_config.required_item_reward,
        key="required_item_reward",
    )
    rewardable_item_reward: int = st.number_input(
        "Reward per rewardable item",
        min_value=0,
        value=maze_config.rewardable_item_reward,
        key="rewardable_item_reward",
    )

    st.subheader("Agent")
    health: int = st.slider("Agent Health", 1, 30, maze_config.health, key="health")

    st.subheader("Doors, Portals")
    num_portals: int = st.slider(
        "Portals (pairs)", 0, 5, maze_config.num_portals, key="num_portals"
    )
    num_doors: int = st.slider("Doors", 0, 4, maze_config.num_doors, key="num_doors")

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

    st.subheader("Gameplay Movement")
    move_fn_names: List[str] = list(MOVE_FN_REGISTRY.keys())
    move_fn_label: str = st.selectbox(
        "Movement rule",
        move_fn_names,
        index=move_fn_names.index(
            next(k for k, v in MOVE_FN_REGISTRY.items() if v is maze_config.move_fn)
        ),
        key="move_fn",
    )
    move_fn: MoveFn = MOVE_FN_REGISTRY[move_fn_label]

    st.subheader("Gameplay Objective")
    objective_fn_names: List[str] = list(OBJECTIVE_FN_REGISTRY.keys())
    objective_fn_label: str = st.selectbox(
        "Objective",
        objective_fn_names,
        index=objective_fn_names.index(
            next(
                k
                for k, v in OBJECTIVE_FN_REGISTRY.items()
                if v is maze_config.objective_fn
            )
        ),
        key="objective_fn",
    )
    objective_fn: ObjectiveFn = OBJECTIVE_FN_REGISTRY[objective_fn_label]

    st.subheader("Random seed")
    seed: int = st.number_input("Random seed", min_value=0, key="maze_seed")

    return MazeConfig(
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
    )


def make_env_and_reset(
    config: MazeConfig,
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


def get_keyboard_action() -> Optional[MazeEnvAction]:
    value: str = (
        st_keyup(
            "control",
            label_visibility="collapsed",
            key="maze_key_input",
            placeholder="Type: WASD to move, e pickup, f use key, q wait",
        )
        or ""
    )
    prev_value: str = st.session_state.get("maze_key_input_prev", "")
    st.session_state["maze_key_input_prev"] = value
    if value != prev_value:
        from collections import Counter

        new_values: List[str] = list((Counter(value) - Counter(prev_value)).elements())
        if not new_values:
            return None
        key: str = new_values[-1]
        key_map: Dict[str, MazeEnvAction] = {
            "w": MazeEnvAction.UP,
            "s": MazeEnvAction.DOWN,
            "a": MazeEnvAction.LEFT,
            "d": MazeEnvAction.RIGHT,
            "f": MazeEnvAction.USEKEY,
            "e": MazeEnvAction.PICKUP,
            "q": MazeEnvAction.WAIT,
        }
        return key_map.get(key)
    return None


def do_action(env: GridUniverseEnv, action_idx: MazeEnvAction) -> None:
    obs, reward, terminated, truncated, info = env.step(np.uint(action_idx))
    st.session_state["obs"] = obs
    st.session_state["info"] = info
    st.session_state["total_reward"] = float(st.session_state["total_reward"]) + reward
    st.session_state["game_over"] = terminated or truncated


def get_effect_types(state: State, effect_id: EntityID) -> List[EffectType]:
    effect_types: List[EffectType] = []
    for effect_type, effect_ids in [
        (EffectType.IMMUNITY, state.immunity),
        (EffectType.PHASING, state.phasing),
        (EffectType.SPEED, state.speed),
    ]:
        if effect_id in effect_ids:
            effect_types.append(effect_type)
    return effect_types


def get_effect_limits(
    state: State, effect_id: EntityID
) -> List[Tuple[EffectLimit, EffectLimitAmount]]:
    effect_limits: List[Tuple[EffectLimit, EffectLimitAmount]] = []
    for limit_type, limit_map in [
        (EffectLimit.TIME, state.time_limit),
        (EffectLimit.USAGE, state.usage_limit),
    ]:
        if effect_id in limit_map:
            effect_limits.append((limit_type, limit_map[effect_id].amount))
    return effect_limits


def display_powerup_status(state: State, status: Status) -> None:
    st.text("PowerUp")
    with st.container(height=250):
        if len(status.effect_ids) == 0:
            st.error("No active powerups")
        for effect_id in status.effect_ids:
            effect_name = state.appearance[effect_id].name
            effect_types = get_effect_types(state, effect_id)
            effect_limits = get_effect_limits(state, effect_id)
            icon = POWERUP_ICONS.get(state.appearance[effect_id].name, "✨")
            st.success(
                f"{effect_name.capitalize()}"
                f" [{', '.join(effect_types)}]"
                f" {', '.join(['(' + ltype + ' ' + str(lamount) + ')' for ltype, lamount in effect_limits])}",
                icon=icon,
            )


def display_inventory(state: State, inventory: Inventory) -> None:
    st.text("Inventory")
    with st.container(height=250):
        if len(inventory.item_ids) == 0:
            st.error("No items")
        for item_id in inventory.item_ids:
            name = state.appearance[item_id].name
            icon = ITEM_ICONS.get(name, "🎲")  # fallback icon
            text = f"{name.replace('_', ' ').capitalize()} #{item_id}"
            if item_id in state.key:
                text += f" ({state.key[item_id].key_id})"
            st.success(text, icon=icon)


# --------- Main App ---------
set_default_config()
tab_game, tab_config, tab_state = st.tabs(["Game", "Config", "State"])

with tab_config:
    config: MazeConfig = get_config_from_widgets()
    st.session_state["maze_config"] = config

    if st.button("🔄 Generate Maze", key="save_config_btn", use_container_width=True):
        st.session_state["maze_seed_counter"] = 0  # reset counter
        st.session_state["maze_config"] = replace(
            st.session_state["maze_config"],
            seed=st.session_state["maze_config"].seed
            + st.session_state["maze_seed_counter"],
        )
        make_env_and_reset(st.session_state["maze_config"])
    st.divider()

with tab_game:
    if "env" not in st.session_state or "obs" not in st.session_state:
        make_env_and_reset(st.session_state["maze_config"])

    left_col, middle_col, right_col = st.columns([0.25, 0.5, 0.25])

    with right_col:
        if st.button("🔄 New Maze", key="generate_btn", use_container_width=True):
            st.session_state["maze_seed_counter"] += 1
            st.session_state["maze_config"] = replace(
                st.session_state["maze_config"],
                seed=st.session_state["maze_config"].seed
                + st.session_state["maze_seed_counter"],
            )
            make_env_and_reset(st.session_state["maze_config"])

        # Need to put after generate maze
        env: GridUniverseEnv = st.session_state["env"]
        obs: ObsType = st.session_state["obs"]
        info: Dict[str, object] = st.session_state["info"]

        if env.state:
            maze_rule = (
                env.state.move_fn.__name__.replace("_", " ")
                .replace("fn", "")
                .capitalize()
            )
            st.info(f"{maze_rule}", icon="🚶")

            objective = (
                env.state.objective_fn.__name__.replace("_", " ")
                .replace("fn", "")
                .capitalize()
            )
            st.info(f"{objective}", icon="🎯")

        st.divider()

        action_idx: Optional[int] = get_keyboard_action()
        if action_idx is not None:
            do_action(env, action_idx)

        _, up_col, _ = st.columns([1, 1, 1])
        with up_col:
            if st.button("⬆️", key="up_btn", use_container_width=True):
                do_action(env, MazeEnvAction.UP)
        left_btn, down_btn, right_btn = st.columns([1, 1, 1])
        with left_btn:
            if st.button("⬅️", key="left_btn", use_container_width=True):
                do_action(env, MazeEnvAction.LEFT)
        with down_btn:
            if st.button("⬇️", key="down_btn", use_container_width=True):
                do_action(env, MazeEnvAction.DOWN)
        with right_btn:
            if st.button("➡️", key="right_btn", use_container_width=True):
                do_action(env, MazeEnvAction.RIGHT)

        pickup_btn, usekey_btn, wait_btn = st.columns([1, 1, 1])
        with pickup_btn:
            if st.button("🤲 Pickup", key="pickup_btn", use_container_width=True):
                do_action(env, MazeEnvAction.PICKUP)
        with usekey_btn:
            if st.button("🔑 Use", key="usekey_btn", use_container_width=True):
                do_action(env, MazeEnvAction.USEKEY)
        with wait_btn:
            if st.button("⏳ Wait", key="wait_btn", use_container_width=True):
                do_action(env, MazeEnvAction.WAIT)

    with left_col:
        state = env.state
        if state is not None:
            st.info(f"**Total Reward:** {st.session_state['total_reward']}", icon="🏅")

            agent_id = env.agent_id

            if agent_id is not None:
                health = state.health[agent_id]
                st.info(
                    f"**Health Point:** {health.health} / {health.max_health}", icon="❤️"
                )
                prev_health = st.session_state["prev_health"]
                if health.health < prev_health:
                    st.toast(f"Taking {health.health - prev_health} damage!", icon="🔥")
                    st.session_state["prev_health"] = health.health

                display_powerup_status(state, state.status[agent_id])
                display_inventory(state, state.inventory[agent_id])

    with middle_col:
        if env.state and env.state.win:
            st.success("🎉 **Goal reached!** 🎉")
            st.balloons()
        if env.state and env.state.lose:
            st.error("💀 **You have died!** 💀")
        img = env.render(mode="texture")
        if img is not None:
            st.image(img, use_container_width=True)

with tab_state:
    if env.state:
        st.json(thaw(env.state.description), expanded=1)
