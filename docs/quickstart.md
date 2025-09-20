# Quick Start

This quick start gets you from zero to a running Grid Universe: install the package, build a minimal level, step actions, render images, and (optionally) use the Gym environment. It also covers seeding, assets, and common troubleshooting.

> Looking for gameplay rules? Check the player-focused [Player Guide](guides/player_guide.md) for portals, pushing, damage, keys/doors, scoring, and win/lose behavior.

Contents

- Installation
- Your first level (authoring → state)
- Step actions
- Render an image
- Use the Gym environment
- Seeding and determinism
- Assets and texture maps
- Debugging tips
- Troubleshooting


## Installation

Requirements

- Python 3.11+

- OS packages: none special; Pillow will use system libraries available on your platform.

Install (editable)
```bash
# from your repo root
pip install -e .
```

Optional extras

- Dev: tests, lint, type checking

- App: streamlit (if you plan to build a UI on top)

- Doc: local docs tooling (MkDocs)

```bash
pip install -e ".[dev]"
pip install -e ".[app]"
pip install -e ".[doc]"
```

Verify import

```bash
python -c "import grid_universe as _; print('OK')"
```


## Your first level (authoring → state)

Author a tiny 5x5 world with floors, an agent, a coin, and an exit; then convert it to runtime State.

```python
from grid_universe.levels.grid import Level
from grid_universe.levels.factories import create_floor, create_agent, create_coin, create_exit
from grid_universe.levels.convert import to_state
from grid_universe.moves import default_move_fn
from grid_universe.objectives import default_objective_fn

# 1) Authoring-time Level (mutable)
level = Level(
    width=5,
    height=5,
    move_fn=default_move_fn,           # choose movement semantics
    objective_fn=default_objective_fn, # win when collect required + stand on exit
    seed=123,                          # for reproducibility
)

# 2) Layout: floors, then place objects
for y in range(level.height):
    for x in range(level.width):
        level.add((x, y), create_floor())

level.add((1, 1), create_agent(health=5))
level.add((2, 1), create_coin(reward=10))
level.add((3, 3), create_exit())

# 3) Convert to runtime State (immutable)
state = to_state(level)

# Grab the agent id
agent_id = next(iter(state.agent.keys()))
print("Agent ID:", agent_id)
```


## Step actions

Apply actions with the main reducer step() to advance the simulation.

```python
from grid_universe.actions import Action
from grid_universe.step import step

# A short sequence: move right, pick up, move down twice
for a in [Action.RIGHT, Action.PICK_UP, Action.DOWN, Action.DOWN]:
    state = step(state, a, agent_id=agent_id)
    print(f"After {a}: score={state.score}, turn={state.turn}, win={state.win}, lose={state.lose}")
    if state.win or state.lose:
        break
```


## Render an image

Use the texture renderer to visualize the State as a PNG.

```python
from grid_universe.renderer.texture import TextureRenderer

renderer = TextureRenderer(resolution=480)   # asset_root defaults to "assets"
img = renderer.render(state)                 # PIL.Image (RGBA)
img.save("quickstart.png")
print("Saved quickstart.png")
```

Tip

- Reuse a single TextureRenderer instance across frames for better performance (in-memory cache).

- Keep resolution constant across frames to maximize cache hits.


## Use the Gym environment

Gymnasium wrapper returns an observation dict with an image and structured info.

```python
import numpy as np
from grid_universe.gym_env import GridUniverseEnv

# Initialize
env = GridUniverseEnv(
    render_mode="texture",
    width=7, height=7,
    seed=42,                 # forwarded to the generator
)

# Reset
obs, info = env.reset()
print("Obs image shape:", obs["image"].shape)
print("Status:", obs["info"]["status"])  # contains score, phase, turn

# Step a few random moves (0=UP, 1=DOWN, 2=LEFT, 3=RIGHT, 4=USE_KEY, 5=PICK_UP, 6=WAIT)
done = False
while not done:
    action = env.action_space.sample().astype(np.int64)
    obs, reward, terminated, truncated, info = env.step(action)
    done = terminated or truncated

# Render the last frame to file
img = env.render()
if img is not None:
    img.save("gym_last_frame.png")
print("Saved gym_last_frame.png")
```


## Seeding and determinism

Use seeds to make runs reproducible.

- Level(seed=...): stored on State.seed; procedural generators and certain systems use it.

- Some movement functions (e.g., `windy_move_fn`) derive per‑turn randomness from `(state.seed, state.turn)`. The renderer’s directory‑variant selection uses a deterministic RNG seeded from `state.seed`.

Example pattern for deterministic per-turn RNG:

```python
import random
from grid_universe.state import State

def rng_for_turn(state: State) -> random.Random:
    base = hash(((state.seed or 0), state.turn))
    return random.Random(base)
```


## Assets and texture maps

Texture selection uses a mapping from appearances/properties to files under an asset root.

- Default assets: assets/kenney/* and others (see rendering docs).

- You can override the texture map or asset root.

Customize the texture map:

```python
from copy import deepcopy
from grid_universe.renderer.texture import TextureRenderer, DEFAULT_TEXTURE_MAP
from grid_universe.components.properties import AppearanceName

custom_map = deepcopy(DEFAULT_TEXTURE_MAP)
custom_map[(AppearanceName.WALL, tuple([]))] = "skins/walls"  # directory with multiple .png files

renderer = TextureRenderer(texture_map=custom_map, asset_root="assets")
renderer.render(state).save("custom_textures.png")
```


## Debugging tips

- Summarize State:

```python
desc = state.description
for k, v in desc.items():
    print(k, type(v), len(v) if hasattr(v, "__len__") else "")
```

- Inspect entity positions and components:

```python
from grid_universe.utils.ecs import entities_at, entities_with_components_at

pos = state.position.get(agent_id)
print("Agent at:", (pos.x, pos.y))
print("Blocking here:", entities_with_components_at(state, pos, state.blocking))
```

- Validate terminal state:

```python
from grid_universe.utils.terminal import is_terminal_state
print("Terminal:", is_terminal_state(state, agent_id))
```

- Render frequently while debugging placement or rendering rules.

## Examples

Explore richer or specialized scenarios on the [Level Examples](guides/level_examples.md) page:

- Procedural maze generator with adjustable densities and content counts
- Gameplay progression suite (L0–L13) introducing mechanics stepwise (coins, cores, key–door, hazard, portal, push, enemy, power‑ups, capstone)
- Cipher objective levels focused on decoding `state.message` containing the objective


## Troubleshooting

- Nothing renders or image is blank:

    - Ensure your Level placed at least one background tile (e.g., FLOOR) in each cell you care about. The renderer still draws without backgrounds, but backgrounds help readability.

    - Verify the asset_root and texture map paths exist and are readable.

- Agent doesn’t move:

    - Check for Blocking at the target tile (unless Phasing effect is active).

    - If using `wrap_around_move_fn`, ensure `State.width`/`State.height` are set (they are if you used Level → to_state).

- Score doesn’t change after moving:

    - Confirm you have Rewardable or Cost tiles/items that apply. Rewards for Collectible items are granted on pickup; per-tile Rewardable apply via `tile_reward_system`.

- Gym render returns None:

    - Only `render_mode="texture"` returns a PIL.Image. `render_mode="human"` calls `img.show()` and returns None.

- Reproducibility issues:

    - Set a seed on Level or the generator. Avoid additional non-deterministic sources in your controller/agent unless you seed them as well.