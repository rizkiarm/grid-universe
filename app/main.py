import os
from dataclasses import replace

import streamlit as st
from components import (
    display_inventory,
    display_powerup_status,
    do_action,
    get_keyboard_action,
)
from config import (
    Config,
    get_config_from_widgets,
    make_env_and_reset,
    set_default_config,
)
from pyrsistent import thaw

from grid_universe.actions import GymAction
from grid_universe.gym_env import GridUniverseEnv, ObsType

script_dir: str = os.path.dirname(os.path.realpath(__file__))

st.set_page_config(layout="wide", page_title="Grid Universe")

with open(os.path.join(script_dir, "styles.css")) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# --------- Main App ---------

set_default_config()
tab_game, tab_config, tab_state = st.tabs(["Game", "Config", "State"])

with tab_config:
    config: Config = get_config_from_widgets()
    st.session_state["config"] = config

    if st.button("🔄 Generate Maze", key="save_config_btn", use_container_width=True):
        st.session_state["maze_seed_counter"] = 0  # reset counter
        st.session_state["config"] = replace(
            st.session_state["config"],
            seed=st.session_state["config"].seed
            + st.session_state["maze_seed_counter"],
        )
        make_env_and_reset(st.session_state["config"])
    st.divider()

with tab_game:
    if "env" not in st.session_state or "obs" not in st.session_state:
        make_env_and_reset(st.session_state["config"])

    left_col, middle_col, right_col = st.columns([0.25, 0.5, 0.25])

    with right_col:
        if st.button("🔄 New Maze", key="generate_btn", use_container_width=True):
            st.session_state["maze_seed_counter"] += 1
            st.session_state["config"] = replace(
                st.session_state["config"],
                seed=st.session_state["config"].seed
                + st.session_state["maze_seed_counter"],
            )
            make_env_and_reset(st.session_state["config"])

        # Need to put after generate maze
        env: GridUniverseEnv = st.session_state["env"]
        obs: ObsType = st.session_state["obs"]
        info: dict[str, object] = st.session_state["info"]

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

        _, up_col, _ = st.columns([1, 1, 1])
        with up_col:
            if st.button("⬆️", key="up_btn", use_container_width=True):
                do_action(env, GymAction.UP)
        left_btn, down_btn, right_btn = st.columns([1, 1, 1])
        with left_btn:
            if st.button("⬅️", key="left_btn", use_container_width=True):
                do_action(env, GymAction.LEFT)
        with down_btn:
            if st.button("⬇️", key="down_btn", use_container_width=True):
                do_action(env, GymAction.DOWN)
        with right_btn:
            if st.button("➡️", key="right_btn", use_container_width=True):
                do_action(env, GymAction.RIGHT)

        pickup_btn, usekey_btn, wait_btn = st.columns([1, 1, 1])
        with pickup_btn:
            if st.button("🤲 Pickup", key="pickup_btn", use_container_width=True):
                do_action(env, GymAction.PICK_UP)
        with usekey_btn:
            if st.button("🔑 Use", key="usekey_btn", use_container_width=True):
                do_action(env, GymAction.USE_KEY)
        with wait_btn:
            if st.button("⏳ Wait", key="wait_btn", use_container_width=True):
                do_action(env, GymAction.WAIT)

        action: GymAction | None = get_keyboard_action()
        if action is not None:
            do_action(env, action)

    with left_col:
        state = env.state
        if state is not None:
            st.info(f"**Total Reward:** {st.session_state['total_reward']}", icon="🏅")

            agent_id = env.agent_id

            if agent_id is not None:
                health = state.health[agent_id]
                st.info(
                    f"**Health Point:** {health.health} / {health.max_health}", icon="❤️",
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
            img_compressed = img.convert("P")  # Converts to 8-bit palette mode
            st.image(img_compressed, use_container_width=True)

with tab_state:
    if env.state:
        st.json(thaw(env.state.description), expanded=1)
