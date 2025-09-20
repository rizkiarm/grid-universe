# Gym Environment

This guide explains the Gymnasium-compatible environment, its observation and action spaces, render modes, integration patterns with RL libraries, and customization hooks. It also covers seeding, recording, and common troubleshooting.

Contents

- Overview and capabilities
- Initialization and configuration
- Observation and action spaces
- Reset/step/render lifecycle
- Seeding and determinism
- Using custom generators and renderers
- Wrappers, vectorization, and RL integration
- Recording videos and logging
- Reward shaping and termination logic
- Examples (end-to-end)
- Troubleshooting


## Overview and capabilities

- Class: `grid_universe.gym_env.GridUniverseEnv`

- Compatible with Gymnasium (supports reset, step, render, action/observation spaces).

- Observation includes:
  
    - An RGBA image (texture-rendered snapshot of `State`).
  
    - A structured info dict (agent health/effects/inventory, score/phase/turn, config metadata, message string).

- Reward:
  
    - Default is the change in score since the previous step (delta score).

- Termination and truncation:
  
    - `terminated` is True if the environment reaches a “win” condition.
  
    - `truncated` is True if the agent reaches a “lose” condition (e.g., dead). Use this as a failure terminal for RL.

- Rendering:
  
    - Texture mode returns a `PIL.Image` (RGBA).
  
    - Human mode shows a window via `PIL.Image.show()` (blocking view on some platforms).


## Initialization and configuration

```python
from grid_universe.gym_env import GridUniverseEnv

env = GridUniverseEnv(
    render_mode="texture",        # "texture" returns PIL.Image in render(); "human" shows a window
    render_resolution=640,        # width in pixels (height derived from grid aspect)
    render_texture_map=None,      # use default texture map unless overridden
    initial_state_fn=None,        # default is examples.maze.generate
    width=9,
    height=9,
    seed=123,                     # forwarded to the generator
    # You can pass any kwargs accepted by the initial_state_fn (maze.generate by default)
    num_required_items=1,
    num_rewardable_items=1,
    num_portals=1,
    num_doors=1,
    wall_percentage=0.8,
)
obs, info = env.reset()
```


## Observation and action spaces

- Spaces are defined in `__init__`. The observation is a dict with:
  
    - `image`: `Box(low=0, high=255, shape=(H, W, 4), dtype=uint8)`
  
    - `info`: `Dict` with nested dicts for `agent`, `status`, `config`, and `message` (see below)

- `agent` sub-dict:

    - `health`: `{ health: int | -1, max_health: int | -1 }`
  
    - `effects`: sequence of effect entries:
      
        - `id`: int
        
        - `type`: "", "IMMUNITY", "PHASING", "SPEED"
        
        - `limit_type`: "", "TIME", "USAGE"
        
        - `limit_amount`: int (or -1)
        
        - `multiplier`: int (SPEED only; -1 otherwise)
  
    - `inventory`: sequence of item entries:
      
        - `id`: int
        
        - `type`: "item" | "key" | "core" | "coin"
        
        - `key_id`: str ("" if N/A)
        
        - `appearance_name`: str ("" if unknown)

- `status` sub-dict:

    - `score`: int
    
    - `phase`: "ongoing" | "win" | "lose"
    
    - `turn`: int

- `config` sub-dict:
- `message` field:

    - A free-form text string (empty string if None) for narrative or task hints.


    - `move_fn`: str (function name)
    
    - `objective_fn`: str (function name)
    
    - `seed`: int (or -1)
    
    - `width`: int
    
    - `height`: int

- Action space:

    - `Discrete(len(Action))` with Action enum order (UP, DOWN, LEFT, RIGHT, USE_KEY, PICK_UP, WAIT)
    
    - Index mapping:
      
        - `0 → UP`
        
        - `1 → DOWN`
        
        - `2 → LEFT`
        
        - `3 → RIGHT`
        
        - `4 → USE_KEY`
        
        - `5 → PICK_UP`
        
        - `6 → WAIT`


## Reset/step/render lifecycle

- `reset(seed=None, options=None)`:

    - Generates a new `State` using `initial_state_fn(**kwargs)` from constructor.
  
    - Selects the first `agent_id` by default.
  
    - Builds or reuses `TextureRenderer` for rendering.
  
    - Returns observation dict and info dict (currently empty).

- `step(action: np.integer)`:

    - Converts integer action to `Action` enum via ordering.
  
    - Applies `grid_universe.step.step` to advance the `State`.
  
    - Computes `reward = new_score − old_score`.
  
    - `terminated = state.win`; `truncated = state.lose`.
  
    - Returns `(obs, reward, terminated, truncated, info)`.

- `render(mode=None)`:

    - Returns a `PIL.Image` if mode (or `render_mode`) is `"texture"`.
  
    - Calls `img.show()` and returns `None` if `"human"`.
  
    - Raises `NotImplementedError` for unknown mode.

- `close()`:

    - No-op (reserved for compatibility).

Minimal loop:

```python
import numpy as np
from grid_universe.gym_env import GridUniverseEnv

env = GridUniverseEnv(render_mode="texture", width=7, height=7, seed=1)
obs, info = env.reset()

done = False
while not done:
    action = np.int64(0)  # UP
    obs, reward, terminated, truncated, info = env.step(action)
    done = terminated or truncated

img = env.render()  # PIL.Image when render_mode="texture"
img.save("episode_last_frame.png")
```


## Seeding and determinism

- Pass `seed` to `GridUniverseEnv` to forward to the generator (`examples.maze.generate`), which sets `State.seed`.

- Some movement functions (e.g., `windy_move_fn`) use per‑turn RNG derived from `(state.seed, state.turn)`. The renderer’s directory‑based texture choice uses a seed derived from `state.seed` to pick a file deterministically per state.

- For strict reproducibility:
  
    - Fix the environment seed in constructor.
  
    - Avoid non-deterministic policies during tests, or seed the policy RNG.

- Gymnasium’s `reset(seed=...)` param: The current env ignores the reset call’s seed and uses the constructor’s seed forwarded to the generator. If you need per-episode seeding, set it on construction time or implement a custom `initial_state_fn` that reads a seed passed via `options` and propagate it in `reset`.


## Using custom generators and renderers

- Custom `initial_state_fn`:

    - Provide a function that returns a `grid_universe.state.State`, and pass it as `initial_state_fn`.
  
    - All extra kwargs are forwarded to that function.

Example replacing the generator:

```python
from typing import Optional
from grid_universe.state import State
from grid_universe.moves import default_move_fn
from grid_universe.objectives import default_objective_fn
from grid_universe.levels.grid import Level
from grid_universe.levels.factories import create_floor, create_agent, create_exit
from grid_universe.levels.convert import to_state
from grid_universe.gym_env import GridUniverseEnv

def my_small_world(width=5, height=5, seed: Optional[int] = None) -> State:
    lvl = Level(width, height, move_fn=default_move_fn, objective_fn=default_objective_fn, seed=seed)
    for y in range(height):
        for x in range(width):
            lvl.add((x, y), create_floor())
    lvl.add((1, 1), create_agent())
    lvl.add((width - 2, height - 2), create_exit())
    return to_state(lvl)

env = GridUniverseEnv(initial_state_fn=my_small_world, width=6, height=4, seed=99, render_mode="texture")
obs, info = env.reset()
```

- Custom texture map or resolution:

    - The env stores a `TextureRenderer` internally. To customize rendering globally, supply `render_resolution` and `render_texture_map` in constructor.

```python
from grid_universe.renderer.texture import DEFAULT_TEXTURE_MAP

env = GridUniverseEnv(
    render_mode="texture",
    render_resolution=800,
    render_texture_map=DEFAULT_TEXTURE_MAP,  # or a customized mapping
    width=9, height=9, seed=7,
)
```


## Wrappers, vectorization, and RL integration

- Gym wrappers:

    - You can wrap `GridUniverseEnv` with standard Gymnasium wrappers (FrameStack, GrayScaleObservation, ResizeObservation, etc.). Many wrappers expect numeric arrays from render; here image is provided via `obs["image"]`, not returned by `render()` on step. Wrap the observation key you need.

- Observation key selection:

    - Use a custom wrapper to replace `obs` with `obs["image"]` or to add embeddings of `info` if your agent expects a simpler observation.

Example wrapper to expose only the image as observation:

```python
import gymnasium as gym
import numpy as np

class ImageOnlyWrapper(gym.ObservationWrapper):
    def __init__(self, env: gym.Env):
        super().__init__(env)
        h, w = self.observation_space["image"].shape[:2]
        self.observation_space = gym.spaces.Box(low=0, high=255, shape=(h, w, 4), dtype=np.uint8)

    def observation(self, observation):
        return observation["image"]

# Usage:
# env = ImageOnlyWrapper(GridUniverseEnv(...))
```

- Vectorized envs:

    - Use Gymnasium’s `SyncVectorEnv`/`AsyncVectorEnv` to run multiple instances. Ensure each one has its own seed and independent `initial_state_fn` kwargs.

- RL libraries:

    - Stable-Baselines3: Works with Gymnasium compatibility wrappers. Ensure the observation is a Box; consider `ImageOnlyWrapper` above.

    - CleanRL / RLlib: Similar considerations; ensure observation shape/dtype matches the algorithm’s expectations.


## Recording videos and logging

- Because `render(mode="texture")` returns a `PIL.Image`, you can manually record frames and assemble a GIF or MP4.

Record frames:

```python
frames = []
obs, info = env.reset()
done = False
while not done:
    frames.append(env.render())
    obs, reward, terminated, truncated, info = env.step(np.int64(0))
    done = terminated or truncated
frames.append(env.render())  # final frame
```

Save a GIF (Pillow):

```python
from PIL import Image

frames_rgba = [im.convert("RGBA") for im in frames]
frames_rgba[0].save(
    "episode.gif",
    save_all=True,
    append_images=frames_rgba[1:],
    duration=200,
    loop=0,
)
```

Save MP4 (imageio-ffmpeg):

```python
import imageio.v3 as iio
import numpy as np

with iio.get_writer("episode.mp4", fps=5) as w:
    for im in frames:
        w.append_data(np.array(im.convert("RGB")))
```


## Reward shaping and termination logic

- Reward:

    - Default reward is delta score per step. To change this, wrap the env and post-process the reward or replace step logic by subclassing.

- Termination:

    - `terminated` (win) is True if objective function is satisfied.

    - `truncated` (lose) is True if the agent dies or lose condition is set. Treat both as episode terminal in RL loops.

- Shaping strategies:

    - Add dense signals (e.g., distance-to-goal) via a wrapper; do not modify `State` directly. Keep the environment source reward consistent and add shaped terms externally for clarity and reproducibility.


## Examples (end-to-end)

Basic random policy loop:

```python
import numpy as np
import gymnasium as gym
from grid_universe.gym_env import GridUniverseEnv

env = GridUniverseEnv(render_mode="texture", width=7, height=7, seed=3)
obs, info = env.reset()
done = False

while not done:
    action = env.action_space.sample().astype(np.int64)  # random discrete action
    obs, reward, terminated, truncated, info = env.step(action)
    if (terminated or truncated):
        done = True

env.render().save("random_last.png")
```

Stable-Baselines3 (with image-only observations):

```python
# pip install stable-baselines3[extra] gymnasium
import gymnasium as gym
import numpy as np
from stable_baselines3 import PPO
from grid_universe.gym_env import GridUniverseEnv

class ImageOnlyWrapper(gym.ObservationWrapper):
    def __init__(self, env):
        super().__init__(env)
        h, w = self.observation_space["image"].shape[:2]
        self.observation_space = gym.spaces.Box(0, 255, shape=(h, w, 4), dtype=np.uint8)
    def observation(self, observation):
        return observation["image"]

def make_env():
    base = GridUniverseEnv(render_mode="texture", width=9, height=9, seed=7)
    return ImageOnlyWrapper(base)

env = make_env()
model = PPO("CnnPolicy", env, verbose=1)
model.learn(total_timesteps=1000)
```


## Troubleshooting

- “Render returns None”:

    - `render_mode` must be `"texture"` to return `PIL.Image`. In `"human"`, it calls `show()` and returns `None`.

- “Observations are not images”:

    - The observation is a dict with `"image"` and `"info"`. If your agent expects only an array, wrap to extract `obs["image"]`.

- “Episodes never end”:

    - Confirm your objective function can be satisfied (or lose condition can occur). Check `obs["info"]["status"]["phase"]` and `"turn"`.

- “Multiple envs have identical layouts”:

    - Provide distinct seeds per env instance or pass per-env kwargs to the generator.

- “High rendering cost”:

    - Reuse env instances across episodes.
  
    - Reduce `render_resolution`.
  
    - Consider skipping `render()` during training and only render evaluation episodes.

- “Texture map not applied”:

    - Ensure `render_texture_map` is passed at construction, and that asset paths resolve under `asset_root`.

- “Gym wrapper errors about spaces”:

    - The base observation is a `Dict` space; ensure your wrappers adapt it to the expected shape (e.g., `ImageOnlyWrapper`).