from __future__ import annotations
from typing import Optional, Iterable, Tuple, List
import random
from dataclasses import replace

from grid_universe.gym_env import GridUniverseEnv, Observation
from grid_universe.levels.grid import Level
from grid_universe.state import State
from grid_universe.objectives import OBJECTIVE_FN_REGISTRY
from grid_universe.examples import maze


TURN_LIMIT = 20


CipherObjectivePair = Tuple[str, str]


def _sample_cipher_pair(
    rng: random.Random,
    pairs: Iterable[CipherObjectivePair],
) -> CipherObjectivePair:
    """Sample a valid (cipher, objective_name) pair.

    Args:
        rng: Random source.
        pairs: Iterable of (cipher, objective_name) pairs. Each objective name must
            exist in ``OBJECTIVE_FN_REGISTRY``.

    Returns:
        CipherObjectivePair: A single sampled valid pair.

    Raises:
        ValueError: If no valid pairs are provided.
    """
    items: List[CipherObjectivePair] = [
        (c, o) for c, o in pairs if c and o in OBJECTIVE_FN_REGISTRY
    ]
    if not items:
        raise ValueError(
            "cipher_objective_pairs must contain at least one valid (cipher, objective_name) pair"
        )
    return rng.choice(items)


def to_cipher_level(
    base_state: State,
    cipher_text_pairs: Iterable[CipherObjectivePair],
    seed: Optional[int] = None,
) -> State:
    """Transform an existing state into a cipher micro-level variant.

    Args:
        base_state: Source state (e.g. from ``maze.generate``).
        cipher_text_pairs: Iterable of (cipher_text, objective_name) pairs (required).
            At least one valid pair (objective registered) must be present.
        seed: Optional seed for deterministic sampling of the pair.

    Returns:
        State: New immutable state with updated ``objective_fn`` and ``message``.

    Raises:
        ValueError: If no valid pairs are supplied.
    """
    rng = random.Random(seed)
    cipher, obj_name = _sample_cipher_pair(rng, cipher_text_pairs)
    new_obj = OBJECTIVE_FN_REGISTRY[obj_name]
    return replace(base_state, objective_fn=new_obj, message=cipher)


def generate(
    width: int,
    height: int,
    num_required_items: int,
    cipher_objective_pairs: Iterable[CipherObjectivePair],
    seed: Optional[int] = None,
) -> State:
    """Generate a cipher micro-level using the maze generator and adapt it.

    Args:
        width: Grid width.
        height: Grid height.
        num_required_items: Number of required cores in the base maze.
        cipher_objective_pairs: Iterable of (cipher, objective_name) pairs; required.
        seed: Deterministic seed for maze + cipher sampling.

    Returns:
        State: Immutable cipher micro-level state.
    """
    base = maze.generate(
        width=width,
        height=height,
        num_required_items=num_required_items,
        num_rewardable_items=0,
        num_portals=0,
        num_doors=0,
        health=5,
        movement_cost=3,
        required_item_reward=0,
        rewardable_item_reward=0,
        boxes=[],
        powerups=[],
        hazards=[],
        enemies=[],
        wall_percentage=0.8,
        seed=seed,
        turn_limit=TURN_LIMIT,
    )

    return to_cipher_level(base, cipher_objective_pairs, seed=seed)


def redact_objective_fn(obs: Observation | Level) -> Observation | Level:
    if isinstance(obs, Level):
        obs.objective_fn = lambda state, entity: False
    else:
        obs["info"]["config"]["objective_fn"] = "<REDACTED>"
    return obs


def patch_env_redact_objective_fn(env: GridUniverseEnv) -> None:
    _orig_get_obs = env._get_obs
    env._get_obs = lambda: redact_objective_fn(_orig_get_obs())  # type: ignore


__all__ = [
    "generate",
    "to_cipher_level",
    "redact_objective_fn",
    "patch_env_redact_objective_fn",
]
