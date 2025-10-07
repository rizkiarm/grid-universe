from __future__ import annotations

from typing import Any, List, Tuple, Optional
from dataclasses import dataclass
import streamlit as st

from grid_universe.gym_env import GridUniverseEnv
from grid_universe.examples import cipher_objective_levels
from grid_universe.renderer.texture import DEFAULT_TEXTURE_MAP, TextureMap
from .base import LevelSource, register_level_source
from ..shared_ui import seed_section, texture_map_section


# -----------------------------
# Config Dataclass
# -----------------------------
@dataclass(frozen=True)
class CipherConfig:
    width: int
    height: int
    num_required_items: int
    seed: Optional[int]
    render_texture_map: TextureMap
    cipher_objective_pairs: List[Tuple[str, str]]


# -----------------------------
# UI Builder
# -----------------------------
def build_cipher_config(current: object) -> CipherConfig:
    st.info("Cipher generator (random micro-level).", icon="🔐")
    base = (
        current
        if isinstance(current, CipherConfig)
        else CipherConfig(9, 7, 1, None, DEFAULT_TEXTURE_MAP, [])
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        width = st.slider("Width", 5, 15, base.width, key="cipher_width")
    with c2:
        height = st.slider("Height", 5, 15, base.height, key="cipher_height")
    with c3:
        num_required_items = st.slider(
            "Required Cores",
            0,
            4,
            base.num_required_items,
            key="cipher_required_items",
            help=">0 switches objective to collect+exit unless overridden by a pair objective.",
        )
    st.caption(
        "Optional (cipher,objective) lines: TOKEN,OBJECTIVE_NAME (objective must exist in registry)."
    )
    existing_pairs = base.cipher_objective_pairs or [
        ("cipher1", "default"),
        ("cipher2", "exit"),
    ]
    default_text = "\n".join([f"{c},{o}" for c, o in existing_pairs])
    raw = st.text_area(
        "Cipher/Objective Pairs",
        value=default_text,
        key="cipher_pairs_text",
        height=140,
        help="Each line 'token,objective'. Empty or invalid lines skipped.",
    )
    parsed: List[Tuple[str, str]] = []
    for ln in raw.splitlines():
        line = ln.strip()
        if not line or line.startswith("#") or "," not in line:
            continue
        tok, obj = line.split(",", 1)
        tok, obj = tok.strip(), obj.strip()
        if tok and obj:
            parsed.append((tok, obj))
    st.markdown(f"Valid lines: **{len(parsed)}**")
    seed = seed_section(key="cipher_seed")
    texture = texture_map_section(base)  # type: ignore[arg-type]
    return CipherConfig(
        width=width,
        height=height,
        num_required_items=num_required_items,
        seed=seed,
        render_texture_map=texture,
        cipher_objective_pairs=parsed,
    )


def _make_env(cfg: CipherConfig) -> GridUniverseEnv:
    """Construct cipher micro-level environment using procedural generator."""
    pairs_arg = cfg.cipher_objective_pairs

    def _initial_state_fn(**_ignored: Any):
        return cipher_objective_levels.generate(
            width=cfg.width,
            height=cfg.height,
            num_required_items=cfg.num_required_items,
            seed=cfg.seed,
            cipher_objective_pairs=pairs_arg,
        )

    sample = _initial_state_fn()
    st.session_state["cipher_last_selection"] = {
        "cipher": sample.message or "",
        "objective_fn": getattr(
            sample.objective_fn, "__name__", str(sample.objective_fn)
        ),
    }
    env = GridUniverseEnv(
        render_mode="texture",
        initial_state_fn=_initial_state_fn,
        width=sample.width,
        height=sample.height,
        render_texture_map=cfg.render_texture_map,
    )

    cipher_objective_levels.patch_env_redact_objective_fn(env)

    return env


def _default_cipher_config() -> CipherConfig:
    return CipherConfig(9, 7, 1, None, DEFAULT_TEXTURE_MAP, [])


register_level_source(
    LevelSource(
        name="Cipher Example",
        config_type=CipherConfig,
        initial_config=_default_cipher_config,
        build_config=build_cipher_config,
        make_env=_make_env,
    )
)
