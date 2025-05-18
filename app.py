from dataclasses import dataclass, replace
import dataclasses
from pyrsistent.typing import PMap
import streamlit as st
import numpy as np
from typing import List, Tuple, Dict, Optional
from st_keyup import st_keyup  # type: ignore
from grid_universe.components import (
    Inventory,
    PowerUp,
    PowerUpType,
    PowerUpLimit,
)
from grid_universe.gym_env import ECSMazeEnv, MazeEnvAction, ObsType
from grid_universe.levels.generator import (
    DEFAULT_HAZARDS,
    DEFAULT_POWERUPS,
    DEFAULT_ENEMIES,
)
from grid_universe.moves import MOVE_FN_REGISTRY, default_move_fn
from grid_universe.state import State
from grid_universe.types import EnemySpec, HazardSpec, MoveFn, PowerupSpec, RenderType
from grid_universe.utils.render import eid_to_render_type

ITEM_ICONS: Dict[RenderType, str] = {
    RenderType.KEY: "🔑",
    RenderType.REWARDABLE_ITEM: "🪙",
    RenderType.REQUIRED_ITEM: "🌟",
    RenderType.ITEM: "🎁",
}

POWERUP_ICONS: Dict[PowerUpType, str] = {
    PowerUpType.GHOST: "👻",
    PowerUpType.SHIELD: "🛡️",
    PowerUpType.HAZARD_IMMUNITY: "🧪",
    PowerUpType.DOUBLE_SPEED: "⚡",
}

st.set_page_config(layout="wide", page_title="Grid Universe")
st.markdown(
    """
    <style>
        header, footer, #MainMenu { visibility: hidden; }
        .stMainBlockContainer {
            padding-top:0;
            padding-bottom:0;
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
    num_boxes: int
    num_moving_boxes: int
    num_portals: int
    num_doors: int
    agent_health: int
    floor_cost: int
    required_item_reward: int
    rewardable_item_reward: int
    powerups: List[PowerupSpec]
    hazards: List[HazardSpec]
    enemies: List[EnemySpec]
    wall_percentage: float
    move_fn: MoveFn
    seed: Optional[int]


def set_default_config() -> None:
    if "maze_config" not in st.session_state:
        st.session_state["maze_config"] = MazeConfig(
            width=10,
            height=10,
            num_required_items=3,
            num_rewardable_items=3,
            num_boxes=2,
            num_moving_boxes=1,
            num_portals=1,
            num_doors=1,
            agent_health=5,
            floor_cost=1,
            required_item_reward=10,
            rewardable_item_reward=10,
            powerups=list(DEFAULT_POWERUPS),
            hazards=list(DEFAULT_HAZARDS),
            enemies=list(DEFAULT_ENEMIES),
            wall_percentage=0.8,
            move_fn=default_move_fn,
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
    floor_cost: int = st.slider(
        "Floor cost", 1, 10, maze_config.floor_cost, key="floor_cost"
    )

    st.subheader("Items & Rewards")
    num_required_items: int = st.slider(
        "Required Items",
        1,
        10,
        maze_config.num_required_items,
        key="num_required_items",
    )
    num_rewardable_items: int = st.slider(
        "Rewardable Items",
        1,
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
    agent_health: int = st.slider(
        "Agent Health", 1, 30, maze_config.agent_health, key="agent_health"
    )

    st.subheader("Boxes, Doors, Portals")
    num_boxes: int = st.slider("Boxes", 0, 8, maze_config.num_boxes, key="num_boxes")
    num_moving_boxes: int = st.slider(
        "Moving Boxes", 0, 4, maze_config.num_moving_boxes, key="num_moving_boxes"
    )
    num_portals: int = st.slider(
        "Portals (pairs)", 0, 5, maze_config.num_portals, key="num_portals"
    )
    num_doors: int = st.slider("Doors", 0, 4, maze_config.num_doors, key="num_doors")

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
    for powerup_type, powerup_ltype, powerup_remaining in DEFAULT_POWERUPS:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            count: int = st.number_input(
                f"{powerup_type.value.replace('_', ' ').capitalize()} count",
                min_value=0,
                value=1,
                key=f"powerup_count_{powerup_type.value}",
            )
        with col2:
            limit_option: str = st.selectbox(
                "Limit",
                ["duration", "usage", "unlimited"],
                index=[PowerUpLimit.DURATION, PowerUpLimit.USAGE, None].index(
                    powerup_ltype
                ),
                key=f"powerup_limit_{powerup_type.value}",
            )
            limit_type: Optional[PowerUpLimit] = None
            if limit_option == "duration":
                limit_type = PowerUpLimit.DURATION
            elif limit_option == "usage":
                limit_type = PowerUpLimit.USAGE
            else:
                limit_type = None  # Irrelevant for unlimited
        with col3:
            if limit_option != "unlimited":
                remaining: Optional[int] = st.number_input(
                    "Remaining",
                    min_value=1,
                    value=powerup_remaining,
                    key=f"powerup_remaining_{powerup_type.value}",
                )
            else:
                st.markdown("Unlimited")
                remaining = None
        if count > 0:
            powerups.extend([(powerup_type, limit_type, remaining)] * count)

    st.subheader("Enemies")
    enemy_count: int = st.number_input(
        "Number of enemies", min_value=0, value=1, key="enemy_count"
    )
    enemies: List[EnemySpec] = []
    if enemy_count > 0:
        for idx in range(enemy_count):
            st.markdown(f"**Enemy #{idx + 1}**")
            cols = st.columns([1, 1, 1])
            with cols[0]:
                lethal = st.checkbox("Lethal?", value=False, key=f"enemy_lethal_{idx}")
            with cols[1]:
                if not lethal:
                    damage = st.number_input(
                        "Damage", min_value=1, value=5, key=f"enemy_damage_{idx}"
                    )
                else:
                    st.markdown("Lethal")
                    damage = 0
            with cols[2]:
                moving = st.checkbox("Moving?", value=False, key=f"enemy_moving_{idx}")
            enemies.append((damage, lethal, moving))

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

    st.subheader("Random seed")
    seed: int = st.number_input("Random seed", min_value=0, key="maze_seed")

    return MazeConfig(
        width=width,
        height=height,
        num_required_items=num_required_items,
        num_rewardable_items=num_rewardable_items,
        num_boxes=num_boxes,
        num_moving_boxes=num_moving_boxes,
        num_portals=num_portals,
        num_doors=num_doors,
        agent_health=agent_health,
        floor_cost=floor_cost,
        required_item_reward=required_item_reward,
        rewardable_item_reward=rewardable_item_reward,
        powerups=powerups,
        hazards=hazards,
        enemies=enemies,
        wall_percentage=wall_percentage,
        move_fn=move_fn,
        seed=seed,
    )


def make_env_and_reset(
    config: MazeConfig,
) -> Tuple[ECSMazeEnv, ObsType, Dict[str, object]]:
    config_dict = dataclasses.asdict(config)
    env = ECSMazeEnv(render_mode="texture", **config_dict)
    obs, info = env.reset(seed=config.seed)
    st.session_state["env"] = env
    st.session_state["obs"] = obs
    st.session_state["info"] = info
    st.session_state["total_reward"] = 0.0
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


def do_action(env: ECSMazeEnv, action_idx: MazeEnvAction) -> None:
    obs, reward, terminated, truncated, info = env.step(np.uint(action_idx))
    st.session_state["obs"] = obs
    st.session_state["info"] = info
    st.session_state["total_reward"] = float(st.session_state["total_reward"]) + reward
    st.session_state["game_over"] = terminated or truncated


def display_powerup_status(powerup_status: PMap[PowerUpType, PowerUp]) -> None:
    st.text("PowerUp")
    with st.container(height=200):
        if len(powerup_status) == 0:
            st.error("No active powerups")
        for ptype, powerup in powerup_status.items():
            icon = POWERUP_ICONS.get(ptype, "✨")
            st.success(
                f"{ptype.value.capitalize()}: "
                f"{powerup.limit.name.lower() if powerup.limit is not None else 'No limit'} "
                f"{powerup.remaining}",
                icon=icon,
            )


def display_inventory(inventory: Inventory, state: State) -> None:
    st.text("Inventory")
    with st.container(height=200):
        if len(inventory.item_ids) == 0:
            st.error("No items")
        for item_id in inventory.item_ids:
            render_type: RenderType = eid_to_render_type(state, item_id)
            icon = ITEM_ICONS.get(render_type, "🎲")  # fallback icon
            text = f"{render_type.name.replace('_', ' ').capitalize()} #{item_id}"
            if item_id in state.key:
                text += f" ({state.key[item_id].key_id})"
            st.success(text, icon=icon)


# --------- Main App ---------
set_default_config()
tab_game, tab_config = st.tabs(["Game", "Config"])

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
        env: ECSMazeEnv = st.session_state["env"]
        obs: ObsType = st.session_state["obs"]
        info: Dict[str, object] = st.session_state["info"]

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
            move_rule = state.move_fn
            maze_rule = (
                move_rule.__name__.replace("_", " ").replace("fn", "").capitalize()
            )
            st.info(f"{maze_rule}", icon="🚶")

            st.info(f"**Total Reward:** {st.session_state['total_reward']}", icon="🏅")

            agent_id = env.agent_id

            if agent_id is not None:
                health = state.health[agent_id]
                st.info(
                    f"**Health Point:** {health.health} / {health.max_health}", icon="❤️"
                )

                display_powerup_status(state.powerup_status[agent_id])
                display_inventory(state.inventory[agent_id], state)

    with middle_col:
        if env.state and env.state.win:
            st.success("🎉 **Goal reached!** 🎉")
        if env.state and env.state.lose:
            st.error("💀 **You have died!** 💀")
        img = env.render(mode="texture")
        if img is not None:
            st.image(img, use_container_width=True)
