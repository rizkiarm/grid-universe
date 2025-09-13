# ----- grid_universe/gym_env.py -----
import gymnasium as gym
import numpy as np
from typing import Callable, Optional, Dict, Tuple, Any, List

from PIL.Image import Image as PILImage

from grid_universe.state import State
from grid_universe.actions import Action
from grid_universe.examples.maze import generate
from grid_universe.renderer.texture import (
    DEFAULT_RESOLUTION,
    DEFAULT_TEXTURE_MAP,
    TextureRenderer,
    TextureMap,
)
from grid_universe.step import step
from grid_universe.types import EffectLimit, EffectType, EntityID

# Observation now includes:
#   - image: np.ndarray (H x W x 4)
#   - info: dict with agent, status, config
ObsType = Dict[str, Any]


def _serialize_effect(state: State, effect_id: EntityID) -> Dict[str, Any]:
    """
    Convert an effect entity into a serializable dict with type, limits, and any extras.
    """
    effect_type: Optional[str] = None
    extra: Dict[str, Any] = {}

    if effect_id in state.immunity:
        effect_type = EffectType.IMMUNITY.name
    elif effect_id in state.phasing:
        effect_type = EffectType.PHASING.name
    elif effect_id in state.speed:
        effect_type = EffectType.SPEED.name
        extra["multiplier"] = state.speed[effect_id].multiplier

    # Limits (if any)
    limit_type = None
    limit_amount = None
    if effect_id in state.time_limit:
        limit_type = EffectLimit.TIME.name
        limit_amount = state.time_limit[effect_id].amount
    if effect_id in state.usage_limit:
        # If both exist, report usage, otherwise time
        limit_type = EffectLimit.USAGE.name
        limit_amount = state.usage_limit[effect_id].amount

    return {
        "id": int(effect_id),
        "type": effect_type,
        "limit_type": limit_type,
        "limit_amount": limit_amount,
        **extra,
    }


def _serialize_inventory_item(state: State, item_id: EntityID) -> Dict[str, Any]:
    """
    Convert an inventory entity into a serializable dict with type info and useful fields.
    """
    item: Dict[str, Any] = {"id": int(item_id), "type": "item"}
    # Key?
    if item_id in state.key:
        item["type"] = "key"
        item["key_id"] = state.key[item_id].key_id
    # Collectibles (categorize core vs coin if we can)
    elif item_id in state.collectible:
        if item_id in state.required:
            item["type"] = "core"
        else:
            item["type"] = "coin"
    # Appearance (optional extra metadata)
    if item_id in state.appearance:
        try:
            item["appearance_name"] = state.appearance[item_id].name.name
        except Exception:
            pass
    return item


def agent_observation_dict(state: State, agent_id: EntityID) -> Dict[str, Any]:
    # Health
    hp = state.health.get(agent_id)
    health_dict: Dict[str, Any] = {
        "health": hp.health if hp else None,
        "max_health": hp.max_health if hp else None,
    }

    # Active effects (status)
    effects: List[Dict[str, Any]] = []
    status = state.status.get(agent_id)
    if status is not None:
        for eff_id in status.effect_ids:
            effects.append(_serialize_effect(state, eff_id))

    # Inventory items
    inv_items: List[Dict[str, Any]] = []
    inv = state.inventory.get(agent_id)
    if inv:
        for item_eid in inv.item_ids:
            inv_items.append(_serialize_inventory_item(state, item_eid))

    return {
        "health": health_dict,
        "effects": effects,
        "inventory": inv_items,
    }


def env_status_observation_dict(state: State) -> Dict[str, Any]:
    # Derive phase for clarity
    phase = "ongoing"
    if state.win:
        phase = "win"
    elif state.lose:
        phase = "lose"
    return {
        "score": int(state.score),
        "phase": phase,
        "turn": int(state.turn),
    }


def env_config_observation_dict(state: State) -> Dict[str, Any]:
    move_fn_name = getattr(state.move_fn, "__name__", str(state.move_fn))
    objective_fn_name = getattr(state.objective_fn, "__name__", str(state.objective_fn))
    return {
        "move_fn": move_fn_name,
        "objective_fn": objective_fn_name,
        "seed": state.seed,
        "width": state.width,
        "height": state.height,
    }


class GridUniverseEnv(gym.Env[ObsType, np.integer]):
    metadata = {"render_modes": ["human", "texture"]}

    def __init__(
        self,
        render_mode: str = "texture",
        render_resolution: int = DEFAULT_RESOLUTION,
        render_texture_map: TextureMap = DEFAULT_TEXTURE_MAP,
        initial_state_fn: Callable[..., State] = generate,
        **kwargs: Any,
    ):
        from gymnasium import spaces  # ensure gymnasium.spaces is available
        import numpy as np

        # Generator/config kwargs for level creation
        self._initial_state_fn = initial_state_fn
        self._initial_state_kwargs = kwargs

        # Runtime state
        self.state: Optional[State] = None
        self.agent_id: Optional[EntityID] = None

        # Basic config
        self.width: int = int(kwargs.get("width", 9))
        self.height: int = int(kwargs.get("height", 9))
        self._render_resolution = render_resolution
        self._render_texture_map = render_texture_map
        self._render_mode = render_mode

        # Rendering setup
        render_width: int = render_resolution
        render_height: int = int(self.height / self.width * render_width)
        self._texture_renderer: Optional[TextureRenderer] = None

        # Observation space helpers (Gymnasium has no Integer/Optional)
        text_space_short = spaces.Text(max_length=32)  # small enums like type/phase
        text_space_medium = spaces.Text(max_length=128)  # function names, key ids

        def int_box(low: int, high: int) -> spaces.Box:
            return spaces.Box(
                low=np.array(low, dtype=np.int64),
                high=np.array(high, dtype=np.int64),
                shape=(),
                dtype=np.int64,
            )

        # Effect entry: use "" for absent strings, -1 for absent numbers
        effect_space = spaces.Dict(
            {
                "id": int_box(0, 1_000_000_000),
                "type": text_space_short,  # "", "IMMUNITY", "PHASING", "SPEED"
                "limit_type": text_space_short,  # "", "TIME", "USAGE"
                "limit_amount": int_box(-1, 1_000_000_000),  # -1 if none
                "multiplier": int_box(-1, 1_000_000),  # -1 if N/A (only SPEED)
            }
        )

        # Inventory item: type in {"key","core","coin","item"}; empty strings for optional text
        item_space = spaces.Dict(
            {
                "id": int_box(0, 1_000_000_000),
                "type": text_space_short,
                "key_id": text_space_medium,  # "" if not a key
                "appearance_name": text_space_short,  # "" if unknown
            }
        )

        # Health: -1 to indicate missing
        health_space = spaces.Dict(
            {
                "health": int_box(-1, 1_000_000),
                "max_health": int_box(-1, 1_000_000),
            }
        )

        # Full observation space: image + structured info dict
        self.observation_space = spaces.Dict(
            {
                "image": spaces.Box(
                    low=0,
                    high=255,
                    shape=(render_height, render_width, 4),
                    dtype=np.uint8,
                ),
                "info": spaces.Dict(
                    {
                        "agent": spaces.Dict(
                            {
                                "health": health_space,
                                "effects": spaces.Sequence(effect_space),
                                "inventory": spaces.Sequence(item_space),
                            }
                        ),
                        "status": spaces.Dict(
                            {
                                "score": int_box(-1_000_000_000, 1_000_000_000),
                                "phase": text_space_short,  # "win" / "lose" / "ongoing"
                                "turn": int_box(0, 1_000_000_000),
                            }
                        ),
                        "config": spaces.Dict(
                            {
                                "move_fn": text_space_medium,
                                "objective_fn": text_space_medium,
                                "seed": int_box(
                                    -1_000_000_000, 1_000_000_000
                                ),  # use -1 to represent None if needed
                                "width": int_box(1, 10_000),
                                "height": int_box(1, 10_000),
                            }
                        ),
                    }
                ),
            }
        )

        # Actions
        self.action_space = spaces.Discrete(len(Action))

        # Initialize first episode
        self.reset()

    def reset(
        self, *, seed: Optional[int] = None, options: Optional[Dict[str, object]] = None
    ) -> Tuple[ObsType, Dict[str, object]]:
        self.state = self._initial_state_fn(**self._initial_state_kwargs)
        self.agent_id = next(iter(self.state.agent.keys()))
        if self._texture_renderer is None:
            self._texture_renderer = TextureRenderer(
                resolution=self._render_resolution, texture_map=self._render_texture_map
            )
        obs = self._get_obs()
        return obs, self._get_info()

    def step(
        self, action: np.integer
    ) -> Tuple[ObsType, float, bool, bool, Dict[str, object]]:
        assert self.state is not None and self.agent_id is not None

        if action >= len(Action):
            raise ValueError("Invalid action:", action)
        step_action: Action = [a for a in Action][int(action)]

        prev_score = self.state.score
        self.state = step(self.state, step_action, agent_id=self.agent_id)
        reward = float(self.state.score - prev_score)
        obs = self._get_obs()
        terminated = self.state.win
        truncated = self.state.lose
        info = self._get_info()
        return obs, reward, terminated, truncated, info

    def render(self, mode: Optional[str] = None) -> Optional[PILImage]:  # type: ignore
        render_mode = mode or self._render_mode
        assert self.state is not None
        if self._texture_renderer is None:
            self._texture_renderer = TextureRenderer(
                resolution=self._render_resolution, texture_map=self._render_texture_map
            )
        img = self._texture_renderer.render(self.state)
        if render_mode == "human":
            img.show()
            return None
        elif render_mode == "texture":
            return img
        else:
            raise NotImplementedError(f"Render mode '{render_mode}' not supported.")

    def state_info(self) -> Dict[str, Dict[str, Any]]:
        assert self.state is not None and self.agent_id is not None
        info_dict = {
            "agent": agent_observation_dict(self.state, self.agent_id),
            "status": env_status_observation_dict(self.state),
            "config": env_config_observation_dict(self.state),
        }
        return info_dict

    def _get_obs(self) -> ObsType:
        assert self.state is not None and self.agent_id is not None
        if self._texture_renderer is None:
            self._texture_renderer = TextureRenderer(
                resolution=self._render_resolution, texture_map=self._render_texture_map
            )
        img = self._texture_renderer.render(self.state)
        img_np = np.array(img)

        info_dict = self.state_info()
        return {"image": img_np, "info": info_dict}

    def _get_info(self) -> Dict[str, object]:
        return {}

    def close(self) -> None:
        pass
