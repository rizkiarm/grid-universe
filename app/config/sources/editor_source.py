from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, cast

import streamlit as st

from grid_universe.moves import MOVE_FN_REGISTRY, default_move_fn
from grid_universe.objectives import (
    OBJECTIVE_FN_REGISTRY,
    default_objective_fn,
)
from grid_universe.levels.grid import Level
from grid_universe.levels.factories import (
    create_agent,
    create_box,
    create_coin,
    create_core,
    create_door,
    create_exit,
    create_floor,
    create_hazard,
    create_immunity_effect,
    create_key,
    create_monster,
    create_phasing_effect,
    create_portal,
    create_speed_effect,
    create_wall,
)
from grid_universe.components.properties.appearance import AppearanceName
from grid_universe.components.properties import MovingAxis
from grid_universe.levels.convert import to_state
from grid_universe.gym_env import GridUniverseEnv
from grid_universe.renderer.texture import (
    DEFAULT_TEXTURE_MAP,
    TextureMap,
    TextureRenderer,
)
from grid_universe.types import MoveFn, ObjectiveFn

from .base import LevelSource, register_level_source
from ..shared_ui import texture_map_section


"""Streamlit interactive level editor source.

Provides an authoring UI where the user selects an entity factory + its
parameters, then clicks cells in a grid to place / replace entities.
The current layout is converted to a ``State`` via the existing authoring
API (``levels.Level`` + ``factories`` + ``levels.convert.to_state``) and
rendered live so users get immediate feedback.

Design constraints:
  * Keep config immutable (dataclass frozen) so it fits existing pattern.
  * Maintain a working mutable grid in ``st.session_state`` while editing;
    when ``build_config`` returns it snapshots that grid into an immutable
    tuple structure inside ``EditorConfig``.
  * Palette driven: choose a *tool* (entity type or eraser) then click cells.
  * Each cell stores a list[EntitySpec] (floor + zero/one foreground objects).
  * Always ensure a floor tile exists for rendering consistency.
  * Supports parameterized factories (health for agent, key id, damage, etc.).
  * Portal pairing: user selects Portal tool and clicks two cells in sequence
    to pair them (subsequent even count clicks continue pairing).
"""


# -----------------------------
# Config Dataclass
# -----------------------------
@dataclass(frozen=True)
class EditorConfig:
    width: int
    height: int
    move_fn: MoveFn
    objective_fn: ObjectiveFn
    seed: Optional[int]
    render_texture_map: TextureMap
    # Immutable snapshot of authored grid: grid[y][x] -> list of palette tokens (dict)
    # Each token dict: {"type": str, "params": {..}}. We rebuild EntitySpecs on play.
    grid_tokens: Tuple[Tuple[Tuple[Dict[str, Any], ...], ...], ...]


def _default_editor_config() -> EditorConfig:
    width, height = 9, 7
    # Initial empty grid tokens (floors only)
    base_row: Tuple[Tuple[Dict[str, Any], ...], ...] = tuple(
        tuple(({"type": "floor", "params": {"cost": 1}},)) for _ in range(width)
    )
    grid_tokens = tuple(base_row for _ in range(height))
    return EditorConfig(
        width=width,
        height=height,
        move_fn=default_move_fn,
        objective_fn=default_objective_fn,
        seed=None,
        render_texture_map=DEFAULT_TEXTURE_MAP,
        grid_tokens=grid_tokens,
    )


# -----------------------------
# Palette Definition
# -----------------------------
class ToolSpec:
    def __init__(
        self,
        label: str,
        builder: Optional[Callable[[Dict[str, Any]], Any]],
        param_ui: Optional[Callable[[], Dict[str, Any]]] = None,
        icon: str = "",
        multi_place: bool = False,
        description: str = "",
    ) -> None:
        self.label = label
        self.builder = builder  # returns EntitySpec OR list[EntitySpec]
        self.param_ui = param_ui  # returns params dict
        self.icon = icon
        self.multi_place = multi_place
        self.description = description


def _agent_params() -> Dict[str, Any]:
    health = st.number_input("Health", 1, 99, 5, key="agent_health")
    return {"health": int(health)}


def _coin_params() -> Dict[str, Any]:
    reward = st.number_input("Reward (0 = none)", 0, 999, 0, key="coin_reward")
    return {"reward": int(reward) if reward > 0 else None}


def _core_params() -> Dict[str, Any]:
    reward = st.number_input("Reward (0 = none)", 0, 999, 10, key="core_reward")
    required = st.checkbox("Required?", value=True, key="core_required")
    return {"reward": int(reward) if reward > 0 else None, "required": bool(required)}


def _key_params() -> Dict[str, Any]:
    key_id = st.text_input("Key ID", value="A", key="key_id")
    return {"key_id": key_id or "A"}


def _door_params() -> Dict[str, Any]:
    key_id = st.text_input("Door Key ID", value="A", key="door_key_id")
    return {"key_id": key_id or "A"}


def _movement_params(kind: str) -> Dict[str, Any]:
    """Shared UI for movement (axis, direction, bounce, speed).

    kind: prefix for Streamlit widget keys to avoid collisions.
    Returns dict with moving_* keys expected by factories.
    """
    axis_label = st.selectbox(
        "Axis",
        ["None", "Horizontal", "Vertical"],
        key=f"{kind}_move_axis",
        help="Movement axis (None = static).",
    )
    axis: Optional[MovingAxis]
    if axis_label == "Horizontal":
        axis = MovingAxis.HORIZONTAL
    elif axis_label == "Vertical":
        axis = MovingAxis.VERTICAL
    else:
        axis = None
    direction = st.selectbox(
        "Direction",
        ["+1 (forward/right/down)", "-1 (back/left/up)"],
        index=0,
        key=f"{kind}_move_dir",
    )
    dir_val = 1 if direction.startswith("+1") else -1
    bounce = st.checkbox(
        "Bounce (reverse at ends)", value=True, key=f"{kind}_move_bounce"
    )
    speed = st.number_input(
        "Speed (tiles / step)", 1, 10, 1, key=f"{kind}_move_speed"
    )
    return {
        "moving_axis": axis,
        "moving_direction": dir_val if axis is not None else None,
        "moving_bounce": bool(bounce),
        "moving_speed": int(speed),
    }


def _monster_params() -> Dict[str, Any]:
    damage = st.number_input("Damage", 1, 50, 3, key="monster_dmg")
    lethal = st.checkbox("Lethal?", value=False, key="monster_lethal")
    st.markdown("**Movement**")
    move = _movement_params("monster")
    return {"damage": int(damage), "lethal": bool(lethal), **move}


def _box_params() -> Dict[str, Any]:
    pushable = st.checkbox("Pushable?", value=True, key="box_pushable")
    st.markdown("**Movement**")
    move = _movement_params("box")
    return {"pushable": bool(pushable), **move}


def _hazard_params(kind: str) -> Callable[[], Dict[str, Any]]:
    def _inner() -> Dict[str, Any]:
        damage = st.number_input(
            "Damage", 0, 50, 2, key=f"{kind}_damage", help="Amount of health lost on contact."
        )
        lethal_default = kind == "lava"
        lethal = st.checkbox(
            "Lethal?", value=lethal_default, key=f"{kind}_lethal", help="If checked, instantly defeats agents regardless of damage."
        )
        return {"damage": int(damage), "lethal": bool(lethal)}

    return _inner


def _floor_params() -> Dict[str, Any]:
    cost = st.number_input(
        "Move Cost", 1, 99, 1, key="floor_cost", help="Energy / cost units required to traverse this tile."
    )
    return {"cost": int(cost)}


def _speed_params() -> Dict[str, Any]:
    mult = st.number_input("Multiplier", 2, 10, 2, key="speed_mult")
    time = st.number_input("Time (0=∞)", 0, 999, 0, key="speed_time")
    usage = st.number_input("Usage (0=∞)", 0, 999, 0, key="speed_usage")
    return {
        "multiplier": int(mult),
        "time": int(time) if time > 0 else None,
        "usage": int(usage) if usage > 0 else None,
    }


def _limit_params(effect: str) -> Dict[str, Any]:
    time = st.number_input("Time (0=∞)", 0, 999, 0, key=f"{effect}_time")
    usage = st.number_input("Usage (0=∞)", 0, 999, 0, key=f"{effect}_usage")
    return {
        "time": int(time) if time > 0 else None,
        "usage": int(usage) if usage > 0 else None,
    }


PALETTE: Dict[str, ToolSpec] = {
    "floor": ToolSpec(
        "Floor",
        lambda p: create_floor(cost_amount=p.get("cost", 1)),
        _floor_params,
        icon="⬜",
    ),
    "wall": ToolSpec("Wall", lambda p: create_wall(), icon="🟫"),
    "agent": ToolSpec(
        "Agent", lambda p: create_agent(health=p["health"]), _agent_params, icon="😊"
    ),
    "exit": ToolSpec("Exit", lambda p: create_exit(), icon="🏁"),
    "coin": ToolSpec(
        "Coin", lambda p: create_coin(reward=p["reward"]), _coin_params, icon="🪙"
    ),
    "core": ToolSpec("Core", lambda p: create_core(**p), _core_params, icon="⭐"),
    "key": ToolSpec("Key", lambda p: create_key(p["key_id"]), _key_params, icon="🔑"),
    "door": ToolSpec(
        "Door", lambda p: create_door(p["key_id"]), _door_params, icon="🚪"
    ),
    "portal": ToolSpec(
        "Portal",
        lambda p: create_portal(),
        icon="🔵",
        description="Click two cells sequentially to pair portals.",
    ),
    "box": ToolSpec(
        "Box",
        lambda p: create_box(
            pushable=p["pushable"],
            moving_axis=p.get("moving_axis"),
            moving_direction=p.get("moving_direction"),
            moving_bounce=p.get("moving_bounce", True),
            moving_speed=p.get("moving_speed", 1),
        ),
        _box_params,
        icon="📦",
    ),
    "monster": ToolSpec(
        "Monster",
        lambda p: create_monster(
            damage=p["damage"],
            lethal=p["lethal"],
            moving_axis=p.get("moving_axis"),
            moving_direction=p.get("moving_direction"),
            moving_bounce=p.get("moving_bounce", True),
            moving_speed=p.get("moving_speed", 1),
        ),
        _monster_params,
        icon="👹",
    ),
    "spike": ToolSpec(
        "Spike",
        lambda p: create_hazard(AppearanceName.SPIKE, p["damage"], p["lethal"]),
        _hazard_params("spike"),
        icon="⚓",
    ),
    "lava": ToolSpec(
        "Lava",
        lambda p: create_hazard(
            AppearanceName.LAVA, p["damage"], p.get("lethal", True)
        ),
        _hazard_params("lava"),
        icon="🔥",
    ),
    "speed": ToolSpec(
        "Speed", lambda p: create_speed_effect(**p), _speed_params, icon="🥾"
    ),
    "shield": ToolSpec(
        "Shield",
        lambda p: create_immunity_effect(time=p["time"], usage=p["usage"]),
        param_ui=lambda: _limit_params("shield"),
        icon="🛡️",
    ),
    "ghost": ToolSpec(
        "Ghost",
        lambda p: create_phasing_effect(time=p["time"], usage=p["usage"]),
        param_ui=lambda: _limit_params("ghost"),
        icon="👻",
    ),
    "erase": ToolSpec("Eraser", None, icon="␡"),
}


# -----------------------------
# Working Grid Helpers
# -----------------------------
def _ensure_working_grid(width: int, height: int) -> List[List[List[Dict[str, Any]]]]:
    key = "editor_working_grid"
    if key not in st.session_state:
        st.session_state[key] = [
            [[{"type": "floor", "params": {"cost": 1}}] for _ in range(width)]
            for _ in range(height)
        ]
    return st.session_state[key]


def _place_tool(
    tool_key: str,
    x: int,
    y: int,
    grid: List[List[List[Dict[str, Any]]]],
    params: Optional[Dict[str, Any]] = None,
) -> None:
    if tool_key == "erase":
        # retain floor only
        grid[y][x] = [next(t for t in grid[y][x] if t["type"] == "floor")]
        return
    if tool_key == "floor":
        # Update existing floor cost (do not append duplicate floor token)
        floor_entry_opt: Optional[Dict[str, Any]] = next(
            (t for t in grid[y][x] if t["type"] == "floor"), None
        )
        if floor_entry_opt is None:
            grid[y][x] = [
                {"type": "floor", "params": {"cost": params.get("cost", 1) if params else 1}}
            ]
        else:
            if params and "cost" in params:
                floor_entry_opt["params"]["cost"] = params["cost"]
        return
    # Remove all non-floor entries
    floor_entry_opt: Optional[Dict[str, Any]] = next(
        (t for t in grid[y][x] if t["type"] == "floor"), None
    )
    if floor_entry_opt is None:
        floor_entry: Dict[str, Any] = {"type": "floor", "params": {"cost": 1}}
    else:
        floor_entry = floor_entry_opt
    grid[y][x] = [floor_entry]  # reset cell
    # Use provided params snapshot (already captured from UI)
    grid[y][x].append({"type": tool_key, "params": params or {}})


def _pair_portals(grid: List[List[List[Dict[str, Any]]]]) -> None:
    portals: List[Tuple[int, int]] = []
    for yy, row in enumerate(grid):
        for xx, cell in enumerate(row):
            if any(t["type"] == "portal" for t in cell):
                portals.append((xx, yy))
    st.session_state["editor_portal_pairs"] = [
        (portals[i], portals[i + 1]) for i in range(0, len(portals) - 1, 2)
    ]


# -----------------------------
# Rebuild Level from snapshot tokens
# -----------------------------
def _build_level_from_tokens(cfg: EditorConfig) -> Level:
    level = Level(
        width=cfg.width,
        height=cfg.height,
        move_fn=cfg.move_fn,
        objective_fn=cfg.objective_fn,
        seed=cfg.seed,
    )

    portal_specs: Dict[Tuple[int, int], Any] = {}
    grid_tokens = cfg.grid_tokens
    for y in range(cfg.height):
        for x in range(cfg.width):
            tokens = list(grid_tokens[y][x])
            for token in tokens:
                ttype = token["type"]
                if ttype == "erase":
                    continue
                builder = PALETTE.get(ttype, None)
                if builder is None:
                    continue
                if builder.builder is None:
                    continue
                params = cast(Dict[str, Any], token.get("params", {}) or {})
                # merge defaults for safety
                defaults = _default_tool_params(ttype)
                merged: Dict[str, Any] = {**defaults, **params}
                try:
                    spec = builder.builder(merged)  # type: ignore[arg-type]
                except Exception:
                    # Fallback: try with defaults only
                    try:
                        spec = builder.builder(defaults)  # type: ignore[arg-type]
                    except Exception:
                        continue
                level.add((x, y), spec)
                if ttype == "portal":
                    portal_specs[(x, y)] = spec

    # Pair portals using stored pairs if available else sequential reading order
    pairs: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
    if "editor_portal_pairs" in st.session_state:
        pairs = cast(
            List[Tuple[Tuple[int, int], Tuple[int, int]]],
            st.session_state["editor_portal_pairs"],
        )  # type: ignore[assignment]
    else:
        ordered = list(portal_specs.keys())
        pairs = [(ordered[i], ordered[i + 1]) for i in range(0, len(ordered) - 1, 2)]
    for a_pos, b_pos in pairs:
        a = portal_specs.get(a_pos)
        b = portal_specs.get(b_pos)
        if a is not None and b is not None and a is not b:
            # Mirror the factory pairing semantics
            try:
                a.portal_pair_ref = b  # type: ignore[attr-defined]
                if getattr(b, "portal_pair_ref", None) is None:
                    b.portal_pair_ref = a  # type: ignore[attr-defined]
            except Exception:
                pass
    return level


# -----------------------------
# UI Builder (3-column layout)
# -----------------------------
def build_editor_config(current: object) -> EditorConfig:
    base = current if isinstance(current, EditorConfig) else _default_editor_config()
    st.info("Interactive level editor.", icon="🛠️")

    # Size + rules row
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        width = st.number_input("Width", 3, 30, base.width, key="editor_width")
    with c2:
        height = st.number_input("Height", 3, 30, base.height, key="editor_height")
    with c3:
        seed = st.number_input("Seed", 0, None, 0, key="editor_seed")
    move_fn = _move_fn_section(base)
    objective_fn = _objective_fn_section(base)
    texture_map = texture_map_section(base)  # type: ignore[arg-type]

    # Working grid (resize if needed)
    grid = _ensure_working_grid(int(width), int(height))
    if len(grid) != height or len(grid[0]) != width:
        new_grid: List[List[List[Dict[str, Any]]]] = [
            [[{"type": "floor", "params": {"cost": 1}}] for _ in range(int(width))]
            for _ in range(int(height))
        ]
        for yy in range(min(int(height), len(grid))):
            for xx in range(min(int(width), len(grid[0]))):
                new_grid[yy][xx] = grid[yy][xx]
        st.session_state["editor_working_grid"] = new_grid
        grid = new_grid

    palette_col, grid_col, preview_col = st.columns([1, 2, 2])

    # Palette
    with palette_col:
        st.subheader("Palette")
        tool_keys = list(PALETTE.keys())
        tool_labels = [f"{PALETTE[k].icon} {PALETTE[k].label}" for k in tool_keys]
        selected_idx = st.radio(
            "**Entity**",
            options=list(range(len(tool_keys))),
            format_func=lambda i: tool_labels[int(i)],
            key="editor_tool_select",
        )
        selected_tool_key = tool_keys[selected_idx]
        tspec = PALETTE[selected_tool_key]
        current_params: Dict[str, Any] = {}
        if tspec.param_ui:
            st.markdown("**Parameters**")
            try:
                current_params = tspec.param_ui() or {}
            except Exception:
                current_params = {}
        if tspec.description:
            st.caption(tspec.description)

    # Grid editing
    with grid_col:
        st.subheader("Grid")
        for yy in range(int(height)):
            cols = st.columns(int(width))
            for xx in range(int(width)):
                cell = grid[yy][xx]
                entries = [t for t in cell if t["type"] != "floor"]
                label = "".join(
                    PALETTE[entry["type"].lower()].icon for entry in entries if entry["type"].lower() in PALETTE
                )
                if cols[xx].button(
                    label or PALETTE["floor"].icon, key=f"editor_cell_{xx}_{yy}"
                ):
                    _place_tool(selected_tool_key, xx, yy, grid, current_params)
                    if selected_tool_key == "portal":
                        _pair_portals(grid)
                    st.rerun()

    # Preview
    with preview_col:
        st.subheader("Preview")
        snap_tokens: Tuple[Tuple[Tuple[Dict[str, Any], ...], ...], ...] = tuple(
            tuple(tuple(cell) for cell in row) for row in grid
        )
        temp_cfg = EditorConfig(
            width=int(width),
            height=int(height),
            move_fn=move_fn,
            objective_fn=objective_fn,
            seed=seed,
            render_texture_map=texture_map,
            grid_tokens=snap_tokens,
        )
        try:
            lvl = _build_level_from_tokens(temp_cfg)
            state = to_state(lvl)
            renderer = TextureRenderer(texture_map=texture_map)
            img = renderer.render(state)
            st.image(img, use_container_width=True)
        except Exception as e:
            msg = str(e) or e.__class__.__name__
            st.error(f"Preview failed: {msg}")

    # Final snapshot config
    snap_tokens: Tuple[Tuple[Tuple[Dict[str, Any], ...], ...], ...] = tuple(
        tuple(tuple(cell) for cell in row) for row in grid
    )
    return EditorConfig(
        width=int(width),
        height=int(height),
        move_fn=move_fn,
        objective_fn=objective_fn,
        seed=seed,
        render_texture_map=texture_map,
        grid_tokens=snap_tokens,
    )


def _move_fn_section(cfg: EditorConfig) -> MoveFn:
    st.subheader("Movement Rule")
    names = list(MOVE_FN_REGISTRY.keys())
    current = next(
        (k for k, v in MOVE_FN_REGISTRY.items() if v is cfg.move_fn), names[0]
    )
    label = st.selectbox(
        "Move Function", names, index=names.index(current), key="editor_move_fn"
    )
    return MOVE_FN_REGISTRY[label]


def _objective_fn_section(cfg: EditorConfig) -> ObjectiveFn:
    st.subheader("Objective Rule")
    names = list(OBJECTIVE_FN_REGISTRY.keys())
    current = next(
        (k for k, v in OBJECTIVE_FN_REGISTRY.items() if v is cfg.objective_fn),
        names[0],
    )
    label = st.selectbox(
        "Objective", names, index=names.index(current), key="editor_objective_fn"
    )
    return OBJECTIVE_FN_REGISTRY[label]


def _make_env(cfg: EditorConfig) -> GridUniverseEnv:
    # Rebuild Level -> State each env reset (ensures fresh IDs)
    def _initial_state_fn(**_ignored: Any):
        level = _build_level_from_tokens(cfg)
        return to_state(level)

    sample_state = _initial_state_fn()
    # Validation: ensure at least one agent entity exists in the authored level.
    # Without an agent the Gym environment will later fail when trying to pick
    # the first agent id.
    if not sample_state.agent:
        raise ValueError(
            "Level must contain an Agent. Use the 'Agent' tool in the palette to place one before starting."
        )
    return GridUniverseEnv(
        render_mode="texture",
        initial_state_fn=_initial_state_fn,
        width=sample_state.width,
        height=sample_state.height,
        render_texture_map=cfg.render_texture_map,
    )


# -----------------------------
# Default Parameter Helpers (avoid KeyErrors)
# -----------------------------
def _default_tool_params(tool_key: str) -> Dict[str, Any]:
    defaults: Dict[str, Dict[str, Any]] = {
        "floor": {"cost": 1},
        "agent": {"health": 5},
        "coin": {"reward": None},
        "core": {"reward": 10, "required": True},
        "key": {"key_id": "A"},
        "door": {"key_id": "A"},
        "monster": {
            "damage": 3,
            "lethal": False,
            "moving_axis": None,
            "moving_direction": None,
            "moving_bounce": True,
            "moving_speed": 1,
        },
        "box": {
            "pushable": True,
            "moving_axis": None,
            "moving_direction": None,
            "moving_bounce": True,
            "moving_speed": 1,
        },
        "spike": {"damage": 2, "lethal": False},
        "lava": {"damage": 2, "lethal": True},
        "speed": {"multiplier": 2, "time": None, "usage": None},
        "shield": {"time": None, "usage": None},
        "ghost": {"time": None, "usage": None},
    }
    return defaults.get(tool_key, {}).copy()


register_level_source(
    LevelSource(
        name="Level Editor",
        config_type=EditorConfig,
        initial_config=_default_editor_config,
        build_config=build_editor_config,
        make_env=_make_env,
    )
)

__all__ = ["EditorConfig"]
