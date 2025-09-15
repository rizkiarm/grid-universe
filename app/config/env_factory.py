from __future__ import annotations

import streamlit as st


from .types import AppConfig
from .sources.base import find_level_source_by_config


def make_env_and_reset(
    config: AppConfig,
):
    """Create & reset an environment for a given config via its registered source.

    Centralizes session_state bookkeeping (env, obs, info, reward, prev_health)
    so individual plugins only focus on building their un‑reset environment.
    """
    source = find_level_source_by_config(config)
    if source is None:
        raise ValueError(
            f"No registered level source for config type: {type(config).__name__}"
        )
    try:
        env = source.make_env(config)
    except ValueError as e:
        # Provide a user‑visible error (common case: missing agent in editor level)
        st.error(f"Environment creation failed: {e}")
        return
    obs, info = env.reset(seed=getattr(config, "seed", None))
    st.session_state["env"] = env
    st.session_state["obs"] = obs
    st.session_state["info"] = info
    st.session_state["total_reward"] = 0.0
    if env.state is not None and env.agent_id is not None:
        agent_id = env.agent_id
        if agent_id in env.state.health:
            st.session_state["prev_health"] = env.state.health[agent_id].health
        else:
            st.session_state["prev_health"] = 0
