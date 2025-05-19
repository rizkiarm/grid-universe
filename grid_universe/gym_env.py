import gymnasium as gym
import numpy as np
import numpy.typing as npt
from typing import Optional, Dict, Tuple, Any, List
from PIL.Image import Image as PILImage
from enum import IntEnum

from grid_universe.state import State
from grid_universe.actions import (
    Action,
    MoveAction,
    Direction,
    PickUpAction,
    UseKeyAction,
    WaitAction,
)
from grid_universe.levels.maze import generate
from grid_universe.renderer.texture import TextureRenderer
from grid_universe.step import step
from grid_universe.types import EffectType, EntityID

# --- Observation type ---
ObsType = Dict[str, npt.NDArray[Any]]


class MazeEnvAction(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    WAIT = 4
    PICKUP = 5
    USEKEY = 6


def agent_feature_vector(
    state: State,
    agent_id: EntityID,
    powerup_types: List[EffectType],
    key_ids: List[str],
) -> np.ndarray[Any, Any]:
    # Health
    agent_hp = state.health.get(agent_id)
    health: float = np.nan
    max_health: float = np.nan
    if agent_hp:
        health = agent_hp.health
        max_health = agent_hp.max_health

    # Score
    score = state.score

    # Inventory: count of each key type
    inventory = state.inventory.get(agent_id)
    items = inventory.item_ids if inventory else set()
    key_counts = []
    for kid in key_ids:
        count = sum(
            1 for eid in items if eid in state.key and state.key[eid].key_id == kid
        )
        key_counts.append(count)

    # Powerups: active flag (1/0) for each EffectType
    powerup_flags = []
    # Simple: active if any effect (of given EffectType) is in agent's status
    for effect_type in powerup_types:
        active = 0
        for eff_id in state.status[agent_id].effect_ids:
            # Check which effect types are present (immunity, phasing, speed)
            if effect_type == EffectType.IMMUNITY and eff_id in state.immunity:
                active = 1
            elif effect_type == EffectType.PHASING and eff_id in state.phasing:
                active = 1
            elif effect_type == EffectType.SPEED and eff_id in state.speed:
                active = 1
        powerup_flags.append(active)

    base_vec = np.array([health, max_health, float(score)], dtype=np.float32)
    key_count_vec = np.array(key_counts, dtype=np.float32)
    powerup_flags_vec = np.array(powerup_flags, dtype=np.float32)
    return np.concatenate([base_vec, key_count_vec, powerup_flags_vec])


class GridUniverseEnv(gym.Env[ObsType, np.integer]):
    metadata = {"render_modes": ["human", "texture"]}
    DIR_ACTIONS: Dict[int, Direction] = {
        MazeEnvAction.UP: Direction.UP,
        MazeEnvAction.DOWN: Direction.DOWN,
        MazeEnvAction.LEFT: Direction.LEFT,
        MazeEnvAction.RIGHT: Direction.RIGHT,
    }

    def __init__(
        self,
        render_mode: str = "texture",
        renderer_cell_size: int = 64,
        **kwargs: Any,
    ):
        self._generator_kwargs = kwargs
        self.state: Optional[State] = None
        self.agent_id: Optional[EntityID] = None
        self.width: int = int(kwargs.get("width", 9))
        self.height: int = int(kwargs.get("height", 9))
        self._powerup_types: List[EffectType] = [
            EffectType.IMMUNITY,
            EffectType.PHASING,
            EffectType.SPEED,
        ]
        self._renderer_cell_size = renderer_cell_size
        self._texture_renderer: Optional[TextureRenderer] = None
        # We'll initialize self._key_ids after first reset (when keys are known)
        self._max_key_types = 8

        # Compute agent vector length for observation space
        agent_vec_len = 3 + self._max_key_types + len(self._powerup_types)
        self.observation_space = gym.spaces.Dict(
            {
                "image": gym.spaces.Box(
                    low=0,
                    high=255,
                    shape=(
                        self.height * renderer_cell_size,
                        self.width * renderer_cell_size,
                        4,
                    ),
                    dtype=np.uint8,
                ),
                "agent": gym.spaces.Box(
                    low=-1e5, high=1e5, shape=(agent_vec_len,), dtype=np.float32
                ),
            }
        )
        self.action_space = gym.spaces.Discrete(7)
        self._render_mode = render_mode
        self._key_ids: List[
            str
        ] = []  # List of all key types in this level (populated in reset)
        self.reset()

    def reset(
        self, *, seed: Optional[int] = None, options: Optional[Dict[str, object]] = None
    ) -> Tuple[ObsType, Dict[str, object]]:
        self.state = generate(**self._generator_kwargs)
        self.agent_id = next(iter(self.state.agent.keys()))
        if self._texture_renderer is None:
            self._texture_renderer = TextureRenderer(cell_size=self._renderer_cell_size)
        # Find all key_id strings in this level, padded to self._max_key_types
        key_ids_set = {key.key_id for key in self.state.key.values()}
        self._key_ids = sorted(key_ids_set)
        # Pad to max length
        if len(self._key_ids) < self._max_key_types:
            self._key_ids += [""] * (self._max_key_types - len(self._key_ids))
        else:
            self._key_ids = self._key_ids[: self._max_key_types]
        obs = self._get_obs()
        return obs, self._get_info()

    def step(
        self, action: np.integer
    ) -> Tuple[ObsType, float, bool, bool, Dict[str, object]]:
        assert self.state is not None and self.agent_id is not None
        if action in self.DIR_ACTIONS:
            ecs_action: Action = MoveAction(
                entity_id=self.agent_id, direction=self.DIR_ACTIONS[int(action)]
            )
        elif action == MazeEnvAction.WAIT:
            ecs_action = WaitAction(entity_id=self.agent_id)
        elif action == MazeEnvAction.PICKUP:
            ecs_action = PickUpAction(entity_id=self.agent_id)
        elif action == MazeEnvAction.USEKEY:
            ecs_action = UseKeyAction(entity_id=self.agent_id)
        else:
            raise ValueError("Invalid action")

        prev_score = self.state.score
        self.state = step(self.state, ecs_action, agent_id=self.agent_id)
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
            self._texture_renderer = TextureRenderer(cell_size=self._renderer_cell_size)
        img = self._texture_renderer.render(self.state)
        if render_mode == "human":
            img.show()
            return None
        elif render_mode == "texture":
            return img
        else:
            raise NotImplementedError(f"Render mode '{render_mode}' not supported.")

    def _get_obs(self) -> ObsType:
        assert self.state is not None and self.agent_id is not None
        if self._texture_renderer is None:
            self._texture_renderer = TextureRenderer(cell_size=self._renderer_cell_size)
        img = self._texture_renderer.render(self.state)
        img_np = np.array(img)
        agent_vec = agent_feature_vector(
            self.state, self.agent_id, self._powerup_types, self._key_ids
        )
        return {"image": img_np, "agent": agent_vec}

    def _get_info(self) -> Dict[str, object]:
        assert self.state is not None
        return {
            "score": self.state.score,
            "turn": self.state.turn,
            "win": self.state.win,
            "lose": self.state.lose,
        }

    def close(self) -> None:
        pass
