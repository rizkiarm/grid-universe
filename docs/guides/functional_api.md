# Functional API

This page presents practical, task-oriented entry points for building, running, rendering, and inspecting Grid Universe. It complements the module reference with end-to-end flows and focused recipes.

Contents

- Quick start: build, step, render
- Core workflow in code
- State inspection and queries
- Movement, pushing, portals, damage
- Collecting items and unlocking doors
- Rendering programmatically
- Gym environment usage
- Level conversion and serialization
- Procedural generation
- Controlling randomness (seeding)
- Registries and plugin-style selection
- Error handling patterns
- Performance tips


## Quick start: build, step, render

Create a tiny level, step a few actions, and render the result.

```python
from grid_universe.levels.grid import Level
from grid_universe.levels.factories import create_floor, create_agent, create_coin, create_exit
from grid_universe.levels.convert import to_state
from grid_universe.moves import default_move_fn
from grid_universe.objectives import default_objective_fn
from grid_universe.actions import Action
from grid_universe.step import step
from grid_universe.renderer.texture import TextureRenderer

# Authoring-time level
level = Level(5, 5, move_fn=default_move_fn, objective_fn=default_objective_fn, seed=123)
for y in range(level.height):
    for x in range(level.width):
        level.add((x, y), create_floor())
level.add((1, 1), create_agent(health=5))
level.add((2, 1), create_coin(reward=10))
level.add((3, 3), create_exit())

# Runtime state
state = to_state(level)
agent_id = next(iter(state.agent.keys()))

# Step a sequence
for a in [Action.RIGHT, Action.PICK_UP, Action.DOWN, Action.DOWN]:
    state = step(state, a, agent_id)
    if state.win or state.lose:
        break

# Render
TextureRenderer(resolution=480).render(state).save("quickstart.png")
```


## Core workflow in code

Most programs follow this loop:

- Build a Level (or generate a State).

- Convert Level → State if needed.

- For each user or agent action:

    - Call step() with the chosen Action and agent_id to produce a new State.

- Render or extract observations.

- Stop when state.win or state.lose.

```python
from grid_universe.actions import Action
from grid_universe.step import step

running = True
while running:
    # get_action() is your controller/agent logic
    action = Action.RIGHT  # example
    state = step(state, action, agent_id=agent_id)
    if state.win or state.lose:
        running = False
```


## State inspection and queries

Get a compact summary and query entities at positions.

```python
# Summary of non-empty stores
desc = state.description
for k, v in desc.items():
    print(k, type(v), len(v) if hasattr(v, "__len__") else "")

# First agent
agent_id = next(iter(state.agent.keys()))

# Agent position and health
pos = state.position.get(agent_id)
hp = state.health.get(agent_id)
print("Agent at:", (pos.x, pos.y), "HP:", (hp and hp.health))
```

Query entities at a tile:

```python
from grid_universe.utils.ecs import entities_at, entities_with_components_at

ids_here = entities_at(state, pos)
blocking_here = entities_with_components_at(state, pos, state.blocking)
print("At agent tile:", ids_here, "blocking:", blocking_here)
```

Grid helpers and bounds/block checks:

```python
from grid_universe.utils.grid import is_in_bounds, is_blocked_at, compute_destination
from grid_universe.components import Position

p = Position(2, 2)
print("In bounds:", is_in_bounds(state, p))
print("Blocked (strict):", is_blocked_at(state, p, check_collidable=True))

# Compute push destination given current -> next (wrap-aware if move_fn is wrap)
current = state.position[agent_id]
next_pos = Position(current.x + 1, current.y)
dest = compute_destination(state, current, next_pos)
print("Push destination:", dest)
```


## Movement, pushing, portals, damage

Apply a single action:

```python
from grid_universe.actions import Action
from grid_universe.step import step

state = step(state, Action.UP, agent_id)
```

Movement/push happens before portal/damage processing in each submove. You can invoke low-level systems for targeted checks or debugging.

- Push logic (pattern):

    ```python
    from grid_universe.utils.ecs import entities_with_components_at
    from grid_universe.components import Position
    from grid_universe.systems.push import push_system

    # Try to push anything pushable at (current + dx,dy)
    pos = state.position[agent_id]
    target = Position(pos.x + 1, pos.y)
    if entities_with_components_at(state, target, state.pushable):
        state_after_push = push_system(state, agent_id, target)
        # state_after_push may or may not differ based on blocking/destination
    ```

- Portals (system-only debug):

    ```python
    from grid_universe.systems.portal import portal_system
    state = portal_system(state)
    ```

- Damage (who threatens the agent now):

    ```python
    from grid_universe.systems.damage import get_damager_ids
    from grid_universe.utils.trail import get_augmented_trail
    from pyrsistent import pset

    aug = get_augmented_trail(state, pset(set(state.health) | set(state.damage) | set(state.lethal_damage)))
    pos = state.position[agent_id]
    threats = get_damager_ids(state, aug, pos)
    print("Damagers at agent tile:", threats)
    ```


## Collecting items and unlocking doors

Collect items/effects on the current tile:

```python
from grid_universe.systems.collectible import collectible_system

state = collectible_system(state, agent_id)
inv = state.inventory.get(agent_id)
print("Inventory count:", (inv and len(inv.item_ids)) or 0)
```

Use key on adjacent doors:

```python
from grid_universe.actions import Action
from grid_universe.step import step

state = step(state, Action.USE_KEY, agent_id=agent_id)
print("Remaining locked:", len(state.locked))
```


## Rendering programmatically

Use TextureRenderer or plug a custom lookup function.

```python
from grid_universe.renderer.texture import TextureRenderer, DEFAULT_TEXTURE_MAP

renderer = TextureRenderer(resolution=640, texture_map=DEFAULT_TEXTURE_MAP, asset_root="assets")
img = renderer.render(state)  # PIL.Image.RGBA
img.save("frame.png")
```

Customize textures by overriding entries or using directories for variants:

```python
from copy import deepcopy
from grid_universe.renderer.texture import TextureRenderer, DEFAULT_TEXTURE_MAP
from grid_universe.components.properties import AppearanceName

custom_map = deepcopy(DEFAULT_TEXTURE_MAP)
custom_map[(AppearanceName.HUMAN, tuple([]))] = "my_assets/hero_idle.png"
custom_map[(AppearanceName.WALL, tuple([]))] = "skins/walls"  # directory -> deterministic pick

TextureRenderer(texture_map=custom_map, asset_root="assets").render(state).save("custom.png")
```


## Gym environment usage

The Gymnasium wrapper provides obs dicts with an image and structured info.

```python
import numpy as np
from grid_universe.gym_env import GridUniverseEnv

env = GridUniverseEnv(render_mode="texture", width=9, height=9, seed=7)
obs, info = env.reset()
print(obs["image"].shape, obs["info"]["status"])

# Apply an action (0 == Action.UP)
obs, reward, terminated, truncated, info = env.step(np.int64(0))
if terminated or truncated:
    obs, info = env.reset()

# Render (PIL image) if render_mode="texture"
img = env.render()
img.save("gym_frame.png")
```


## Level conversion and serialization

Convert back and forth between authoring Level and runtime State.

```python
from grid_universe.levels.convert import to_state, from_state

state = to_state(level)
level2 = from_state(state)
# level2 is a mutable authoring representation reconstructed from positioned entities
```

Serialization notes:

- The library does not impose a file format for Level/State.

- For reproducibility, prefer regenerating levels from seeds.

- If you need persistence, you can:

    - Serialize Level: your own JSON/YAML schema capturing grid and EntitySpec fields.

    - Serialize State: custom encoder for PMaps and dataclasses; or pickle for internal tooling (not recommended for long-term storage).


## Procedural generation

Use the example generator for a rich layout with floors/walls, items, doors/keys, portals, hazards, enemies, and powerups.

```python
from grid_universe.examples.maze import generate

state = generate(
    width=13, height=11,
    num_required_items=2,
    num_rewardable_items=3,
    num_portals=1,
    num_doors=1,
    wall_percentage=0.8,
    seed=42,
)
agent_id = next(iter(state.agent.keys()))
```


## Controlling randomness (seeding)

Set seeds to make runs reproducible.

- Level(seed=...): stored in State.seed.

- Some features derive per-turn randomness from (state.seed, state.turn), such as windy_move_fn and renderer directory choices.

Pattern for per-turn RNG:

```python
import random
from grid_universe.state import State

def rng_for_turn(state: State) -> random.Random:
    base = hash(((state.seed or 0), state.turn))
    return random.Random(base)
```


## Registries and plugin-style selection

Select movement/objective functions by name.

```python
from grid_universe.levels.grid import Level
from grid_universe.moves import MOVE_FN_REGISTRY
from grid_universe.objectives import OBJECTIVE_FN_REGISTRY

move_fn = MOVE_FN_REGISTRY["slippery"]
objective_fn = OBJECTIVE_FN_REGISTRY["unlock"]
level = Level(9, 9, move_fn=move_fn, objective_fn=objective_fn, seed=1)
```


## Error handling patterns

Common runtime checks:

- Missing agent or terminal state:

    - step() returns the same state or sets lose=True if the agent is dead.

- Invalid action:

    - step() raises ValueError if action not in Action enum.

- wrap_around_move_fn without width/height:

    - Raises ValueError; ensure State has proper dimensions.

Defensive usage example:

```python
from grid_universe.utils.terminal import is_terminal_state, is_valid_state

if not is_valid_state(state, agent_id) or is_terminal_state(state, agent_id):
    # Skip stepping or handle end-of-episode
    pass
```


## Performance tips

- Reuse a single TextureRenderer across frames to benefit from texture cache.

- Keep render resolution constant to maximize cache hits.

- Prefer smaller grids or fewer simultaneous moving overlays for real-time loops.

- Avoid heavy postprocessing per frame; batch-render only when needed.

- For large automation runs, skip rendering and log State.description or extract concise signals (score, win/lose, positions).