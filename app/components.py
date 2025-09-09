
import numpy as np
import streamlit as st
from keyup import keyup

from grid_universe.actions import GymAction
from grid_universe.components import AppearanceName, Inventory, Status
from grid_universe.gym_env import GridUniverseEnv
from grid_universe.state import State
from grid_universe.types import EffectLimit, EffectLimitAmount, EffectType, EntityID

ITEM_ICONS: dict[AppearanceName, str] = {
    AppearanceName.KEY: "🔑",
    AppearanceName.COIN: "🪙",
    AppearanceName.CORE: "🌟",
}

POWERUP_ICONS: dict[AppearanceName, str] = {
    AppearanceName.GHOST: "👻",
    AppearanceName.SHIELD: "🛡️",
    AppearanceName.BOOTS: "⚡",
}


def get_effect_types(state: State, effect_id: EntityID) -> list[EffectType]:
    effect_types: list[EffectType] = []
    for effect_type, effect_ids in [
        (EffectType.IMMUNITY, state.immunity),
        (EffectType.PHASING, state.phasing),
        (EffectType.SPEED, state.speed),
    ]:
        if effect_id in effect_ids:
            effect_types.append(effect_type)
    return effect_types


def get_effect_limits(
    state: State, effect_id: EntityID,
) -> list[tuple[EffectLimit, EffectLimitAmount]]:
    effect_limits: list[tuple[EffectLimit, EffectLimitAmount]] = []
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


def get_keyboard_action() -> GymAction | None:
    key_map = {
        "ArrowUp": GymAction.UP,
        "ArrowDown": GymAction.DOWN,
        "ArrowLeft": GymAction.LEFT,
        "ArrowRight": GymAction.RIGHT,
        "w": GymAction.UP,
        "s": GymAction.DOWN,
        "a": GymAction.LEFT,
        "d": GymAction.RIGHT,
        "f": GymAction.USE_KEY,
        "e": GymAction.PICK_UP,
        "q": GymAction.WAIT,
    }
    value = keyup(
        default_text="Click here to use keyboard",
        focused_text="W,A,S,D to move, E to collect, F to use key, and Q to wait",
    )
    return key_map.get(value)


def do_action(env: GridUniverseEnv, action: GymAction) -> None:
    obs, reward, terminated, truncated, info = env.step(np.uint(action.value))
    st.session_state["obs"] = obs
    st.session_state["info"] = info
    st.session_state["total_reward"] = float(st.session_state["total_reward"]) + reward
    st.session_state["game_over"] = terminated or truncated
