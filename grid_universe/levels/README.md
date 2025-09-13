# Grid Universe: Levels

This README teaches you how to author levels with the Level API in `grid_universe/levels`, convert them into the immutable runtime ECS `State`, and wire gameplay elements like portals, doors/keys, enemies, and powerups. It includes a component-by-component reference and many examples.

## Concepts at a glance

- Authoring time (mutable):
  - You build a `Level` with a grid of `EntitySpec` (component bundles with no IDs).
  - You place specs into cells via `Level.add((x, y), spec)`.

- Runtime (immutable):
  - Convert to a `State` via `levels.convert.to_state(level)`.
  - Each placed spec becomes a runtime entity with a unique ID and a `Position` component.
  - Systems operate on `State` (movement, damage, pathfinding, push, portals, etc.).

Why? Authoring stays simple and composable; runtime stays consistent, reproducible, and easier to debug.


## Core files and how they fit together

- `grid_universe/levels/grid.py`
  - `Level`: authoring-time grid of cells; each cell holds a list of `EntitySpec`.
- `grid_universe/levels/entity_spec.py`
  - `EntitySpec`: a bag of ECS components (no Position/ID).
  - `COMPONENT_TO_FIELD`: maps component classes to `State` stores.
- `grid_universe/levels/factories.py`
  - Helpers to create common `EntitySpec` (agent, floor, wall, key/door, portal, box, hazard, enemy, powerups).
- `grid_universe/levels/convert.py`
  - `to_state(Level) -> State`: instantiates entities, Position, wiring, nested lists.
  - `from_state(State) -> Level`: reconstructs placed `EntitySpec` and authoring references.
- `grid_universe/examples/maze.py`
  - Procedural generator using the Level API.


## Quick start (tiny level)

Create a 5x5 level: floors, border walls, an agent, a coin, and an exit. Then convert to `State`.

```python
from grid_universe.levels.grid import Level
from grid_universe.levels.factories import (
    create_floor, create_wall, create_agent, create_coin, create_exit
)
from grid_universe.moves import default_move_fn
from grid_universe.objectives import default_objective_fn
from grid_universe.levels.convert import to_state

# 1) Level with movement and objective functions
level = Level(
    width=5,
    height=5,
    move_fn=default_move_fn,
    objective_fn=default_objective_fn,
    seed=123,
)

# 2) Floors everywhere
for y in range(level.height):
    for x in range(level.width):
        level.add((x, y), create_floor(cost_amount=1))

# 3) Border walls
for x in range(level.width):
    level.add((x, 0), create_wall())
    level.add((x, level.height - 1), create_wall())
for y in range(level.height):
    level.add((0, y), create_wall())
    level.add((level.width - 1, y), create_wall())

# 4) Agent, coin, exit
level.add((1, 1), create_agent(health=5))
level.add((2, 2), create_coin(reward=10))
level.add((3, 3), create_exit())

# 5) Convert to runtime State
state = to_state(level)
```


## Authoring patterns and common objects (factories)

Factories return `EntitySpec` with sensible defaults.

- Tiles
  - `create_floor(cost_amount=1)`: floor background + movement cost.
  - `create_wall()`: wall background + `Blocking` (obstructs movement).
  - `create_exit()`: exit marker (win condition target).
- Player and items
  - `create_agent(health=5)`: agent with `Inventory` and `Status`.
  - `create_coin(reward=None)`: collectible; add `Rewardable` if you pass `reward`.
  - `create_core(reward=None, required=True)`: collectible; can be `Required`.
  - `create_key(key_id)`: collectible key carrying `Key(key_id)`.
- Doors and portals
  - `create_door(key_id)`: `Locked(key_id)` + `Blocking`.
  - `create_portal(pair=None)`: portal that can be paired at authoring time.
- Boxes and hazards
  - `create_box(pushable=True)`: `Blocking`, `Collidable`, optionally `Pushable`.
  - `create_hazard(appearance, damage, lethal=False, priority=7)`: e.g., SPIKE/LAVA tiles.
- Enemies and powerups
  - `create_monster(damage=3, lethal=False, pathfind_target=None, path_type=...)`
  - `create_speed_effect(multiplier, time=None, usage=None)`
  - `create_immunity_effect(time=None, usage=None)`
  - `create_phasing_effect(time=None, usage=None)`

Example: a simple locked door puzzle.

```python
from grid_universe.levels.grid import Level
from grid_universe.levels.factories import create_floor, create_key, create_door, create_agent, create_exit
from grid_universe.moves import default_move_fn
from grid_universe.objectives import all_unlocked_objective_fn
from grid_universe.levels.convert import to_state

level = Level(7, 5, move_fn=default_move_fn, objective_fn=all_unlocked_objective_fn, seed=1)
for y in range(level.height):
    for x in range(level.width):
        level.add((x, y), create_floor())

level.add((1, 2), create_agent())
level.add((2, 2), create_key("red"))
level.add((3, 2), create_door("red"))
level.add((5, 2), create_exit())

state = to_state(level)
```


## Wiring relationships (portals, pathfinding)

Portals and enemy pathfinding use authoring-time references; the converter resolves them to entity IDs.

- Portals (pairing both ends):

```python
from grid_universe.levels.factories import create_portal

p1 = create_portal()
p2 = create_portal(pair=p1)  # reciprocal authoring refs

level.add((1, 1), p1)
level.add((5, 3), p2)
# After to_state(level): each gets Portal(pair_entity=<eid_of_other>)
```

- Enemies that chase the agent:

```python
from grid_universe.levels.factories import create_agent, create_monster
from grid_universe.components.properties import PathfindingType

agent = create_agent()
enemy = create_monster(damage=2, pathfind_target=agent, path_type=PathfindingType.PATH)
level.add((2, 2), agent)
level.add((2, 4), enemy)
# After to_state(level): enemy gets Pathfinding(target=<agent_eid>, type=PATH)
```


## Inventory and Status (effects)

You can pre-load items and effects using authoring-time nested lists on `EntitySpec`:
- `inventory_list`: items become separate entities added to holder’s `Inventory.item_ids`.
- `status_list`: effects become separate entities added to holder’s `Status.effect_ids`.

Example: start with a key and a phasing effect.

```python
from grid_universe.levels.factories import create_agent, create_key, create_phasing_effect

agent = create_agent()
agent.inventory_list.append(create_key("blue"))
agent.status_list.append(create_phasing_effect(time=None, usage=3))
level.add((1, 1), agent)
```

Notes:
- Nested entities do not get a `Position`.
- If the holder already has `Inventory`/`Status`, lists are merged during conversion.


## Converting Level <-> State

- `to_state(level)`:
  - Creates entities with IDs and `Position`.
  - Copies components from `EntitySpec`.
  - Materializes `inventory_list` and `status_list` into separate off-grid entities and wires them to holders.
  - Resolves authoring refs (portals, pathfinding).

- `from_state(state)`:
  - Rebuilds a `Level` with placed `EntitySpec` (for entities that have `Position`).
  - Restores inventory/effects as authoring lists.
  - Restores wiring refs where both ends are placed.

Round trip:

```python
from grid_universe.levels.convert import to_state, from_state
state = to_state(level)
level2 = from_state(state)
```


## Movement and objectives

Set these when constructing the `Level`.

Movement functions (`grid_universe.moves`):
- `default_move_fn`: 1-step in the arrow direction.
- `wrap_around_move_fn`: wraps X/Y at edges.
- `mirror_move_fn`: mirrors left/right.
- `slippery_move_fn`: slides until blocked (through open cells).
- `windy_move_fn`: sometimes adds a wind step (deterministic per turn via seed).
- `gravity_move_fn`: move, then repeatedly fall down while possible.

Objective functions (`grid_universe.objectives`):
- `default_objective_fn`: collect all `Required` and stand on an `Exit`.
- `exit_objective_fn`: stand on an `Exit`.
- `collect_required_objective_fn`: collect all `Required`.
- `all_unlocked_objective_fn`: no `Locked` remain.
- `all_pushable_at_exit_objective_fn`: all `Pushable` objects are on `Exit` cells.

Example:

```python
from grid_universe.levels.grid import Level
from grid_universe.moves import wrap_around_move_fn
from grid_universe.objectives import all_unlocked_objective_fn

level = Level(10, 10, move_fn=wrap_around_move_fn, objective_fn=all_unlocked_objective_fn, seed=42)
```


## Procedural maze example (high-level)

`grid_universe/examples/maze.py` demonstrates:
- Maze carving + wall density control.
- Placing floors/walls.
- Required cores, reward coins.
- Portals, doors/keys.
- Enemies (directional or pathfinding).
- Hazards and powerups.
- Keeping some cells for non-essential entities (path analysis).


## Running the maze generator

Generate a `State` and step it with actions.

```python
from grid_universe.examples.maze import generate
from grid_universe.actions import Action
from grid_universe.step import step

state = generate(
    width=9, height=9,
    num_required_items=1,
    num_rewardable_items=2,
    num_portals=1,
    num_doors=1,
    seed=42,
)

agent_id = next(iter(state.agent.keys()))
actions = [Action.RIGHT, Action.DOWN, Action.DOWN, Action.LEFT, Action.USE_KEY, Action.PICK_UP, Action.WAIT]

for i, a in enumerate(actions, 1):
    state = step(state, a, agent_id=agent_id)
    print(f"Step {i:02d}: action={a}, score={state.score}, turn={state.turn}, win={state.win}, lose={state.lose}")
    if state.win or state.lose:
        break
```


## Rendering a State

Render directly with the texture renderer.

```python
from grid_universe.renderer.texture import TextureRenderer, DEFAULT_TEXTURE_MAP

renderer = TextureRenderer(
    resolution=640,
    subicon_percent=0.4,
    texture_map=DEFAULT_TEXTURE_MAP,
    asset_root="assets",
)

img = renderer.render(state)  # PIL.Image (RGBA)
img.show()
img.save("maze_state.png")
print("Saved snapshot to maze_state.png")
```

Render a short sequence as frames (and optional GIF):

```python
from grid_universe.examples.maze import generate
from grid_universe.actions import Action
from grid_universe.step import step
from grid_universe.renderer.texture import TextureRenderer
from PIL import Image

state = generate(width=9, height=9, seed=7)
agent_id = next(iter(state.agent.keys()))
renderer = TextureRenderer(resolution=640)
sequence = [Action.RIGHT, Action.RIGHT, Action.DOWN, Action.DOWN, Action.LEFT, Action.USE_KEY, Action.WAIT]

for t, a in enumerate(sequence):
    renderer.render(state).save(f"frame_{t:02d}.png")
    state = step(state, a, agent_id=agent_id)
renderer.render(state).save(f"frame_{len(sequence):02d}.png")

# Compose GIF (optional)
frames = [Image.open(f"frame_{i:02d}.png").convert("RGBA") for i in range(len(sequence)+1)]
frames[0].save("maze_run.gif", save_all=True, append_images=frames[1:], duration=200, loop=0)
print("Saved frames and maze_run.gif")
```


## Rendering with the Gym environment

```python
import numpy as np
from grid_universe.gym_env import GridUniverseEnv

env = GridUniverseEnv(render_mode="texture", width=7, height=7, seed=123)
obs, info = env.reset()

obs, reward, terminated, truncated, info = env.step(np.int64(0))  # Action.UP
image_np = obs["image"]  # (H, W, 4)
info_dict = obs["info"]
```


## Component reference (what each component does)

Effects (entities in Status.effect_ids)
- `Immunity`: Negates damage for the entity when present/consumed by damage_system.
- `Phasing`: Allows passing through blocking/collidable when moving (consumed by movement).
- `Speed(multiplier)`: Increases number of move substeps per action (consumed per action if usage-limited).
- `TimeLimit(amount)`: Ticks down each turn; when <= 0, effect expires.
- `UsageLimit(amount)`: Decrements when the effect is used; when <= 0, effect expires.

Properties (on world entities or agents/items)
- `Agent`: Marks the entity as an agent controlled by actions.
- `Appearance(name, priority=0, icon=False, background=False)`:
  - Controls rendering: background tiles, main object selection, icon overlays (corners), draw order via priority.
- `Blocking`: Occupies space; agents cannot enter unless phasing active.
- `Collectible`: Can be picked up (items, powerups). On pickup:
  - If it has effect components (e.g., Speed/Immunity/Phasing), it’s added to Status effects (if valid by limits).
  - Otherwise, added to Inventory (e.g., Key, Coin/Core).
  - `Rewardable` increases score immediately.
- `Collidable`: Included in impact checks; interacts with damage/portal trail logic. For agents, commonly set to true.
- `Cost(amount)`: Per-tile cost deducted after actions if the agent is on such a tile (tile_cost_system).
- `Damage(amount)`: Inflicts `amount` of damage to entities present on the same cell (damage_system).
- `Dead`: Marks entity as dead (e.g., after lethal or HP reaches 0). For agents, triggers lose condition.
- `Exit`: A tile that can satisfy exit-based objectives.
- `Health(health, max_health)`: Health pool for damage/lose condition.
- `Inventory(item_ids)`: Set of item entity IDs the holder carries (keys, coins, cores, etc.).
- `Key(key_id)`: Identifies a key; used to unlock matching `Locked(key_id)` doors.
- `LethalDamage`: When present on a damager, any contact kills regardless of damage amount.
- `Locked(key_id)`: Requires a key with matching `key_id`; `unlock_system` removes `Locked` and `Blocking` when used.
- `Moving(axis, direction, bounce=True, speed=1)`: Autonomous movers (boxes/enemies). Moves each turn along axis (H/V).
- `Pathfinding(target, type)`: Enemies move toward target:
  - `STRAIGHT_LINE`: greedy Manhattan step
  - `PATH`: A* over non-blocking, in-bounds tiles
- `Portal(pair_entity)`: Teleports collidable entities that enter the cell to the paired portal’s position.
- `Position(x, y)`: Location on the grid (State only; Level/EntitySpec does not carry `Position`).
- `Pushable`: Can be pushed by an agent; the agent steps into the cell and the pushable moves to the next cell along the vector.
- `Required`: Required items for default objectives.
- `Rewardable(amount)`: Grants score when on the same tile (if non-collectible), or on collection (if collectible).
- `Status(effect_ids)`: Active effect IDs on the entity (agent usually has this).

How systems use them (high-level)
- position_system: snapshots current positions into prev_position each turn for cross-effects (damage, portals, trail).
- moving_system: updates entities with Moving along their axis up to speed steps; bounces or stops if blocked.
- pathfinding_system: moves entities with Pathfinding toward target (A* for PATH, greedy for STRAIGHT_LINE); respects bounds and Blocking (ignores Collidable like the agent move).
- movement_system: applies the agent’s single-step move if in-bounds and not blocked; if Phasing effect is active, ignores blocking (and consumes usage if limited).
- push_system: when the agent attempts to step into a Pushable, computes the destination cell and moves both agent and pushable if destination is not blocked.
- portal_system: teleports collidable entities that enter a portal position to the paired portal; uses trail/prev_position to detect entrants.
- damage_system: applies Damage (and LethalDamage) from co-located entities to any Health carriers, unless Immunity is active (consumes usage/time).
- tile systems:
  - tile_reward_system: adds score for Rewardable items on the agent’s tile that are not collectible (e.g., floor-based score).
  - tile_cost_system: subtracts score for Cost items on the agent’s tile (movement cost).
- status systems:
  - status_tick_system: decrements TimeLimit for all active effects on all entities with Status.
  - status_gc_system: removes expired or orphaned effects from Status and entity store (garbage-collecting effect entities).
- trail_system: records traversed cells between prev_position and position for collidable/damaging/portal interactions.
- terminal systems:
  - win_system: sets win if objective function is satisfied.
  - lose_system: sets lose if agent is Dead.
- run_garbage_collector (utils.gc): removes entities not referenced from any live structure (positions, inventories, status lists, etc.) to keep State compact.


## Extending the system

This section shows how to add a new component/tile, expose it in factories, integrate it into rendering, and (optionally) create a system if it affects gameplay.

Example A: New tile “BouncePad” that pushes the agent 1 extra step forward after entering.

1. Define the component
- Add a dataclass in `grid_universe/components/properties/bounce_pad.py`:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class BouncePad:
    strength: int = 1  # extra steps to move in the same direction
```

- Export it from `grid_universe/components/properties/__init__.py` and `grid_universe/components/__init__.py`.
- Add a new PMap field to `grid_universe/state.py`:
  - `bounce_pad: PMap[EntityID, BouncePad] = pmap()`

2. Map component for authoring conversion
- In `grid_universe/levels/entity_spec.py`, extend `COMPONENT_TO_FIELD`:
  - `BouncePad: "bounce_pad"`

3. Create a factory
- In `levels/factories.py`:

```python
from grid_universe.components.properties import Appearance, AppearanceName, BouncePad

def create_bounce_pad(strength: int = 1, priority: int = 6):
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.GEM, priority=priority),  # pick an icon / add a new AppearanceName
        collidable=None,   # usually not needed for floor-like behavior
        bounce_pad=BouncePad(strength=strength),
    )
```

4. Add gameplay behavior
- Implement a small hook in movement flow. For example, after a successful agent move (in `_after_substep` or in `movement_system` post-move), if the agent is on a cell with `BouncePad`, perform an extra movement in the same direction (`strength` steps) if not blocked. This is a design choice:
  - Minimal approach: add a new system `bounce_pad_system(state, agent_id)` and call it inside `_after_substep`.

Pseudocode for a `bounce_pad_system`:

```python
from dataclasses import replace
from grid_universe.utils.ecs import entities_with_components_at
from grid_universe.components import Position
from grid_universe.actions import MOVE_ACTIONS

def bounce_pad_system(state: State, agent_id: EntityID, last_move_dir: tuple[int,int] | None) -> State:
    if last_move_dir is None:
        return state
    pos = state.position.get(agent_id)
    if pos is None:
        return state
    pad_ids = entities_with_components_at(state, pos, state.bounce_pad)
    if not pad_ids:
        return state
    pad_id = pad_ids[0]
    strength = state.bounce_pad[pad_id].strength
    dx, dy = last_move_dir
    for _ in range(max(0, strength)):
        next_pos = Position(pos.x + dx, pos.y + dy)
        moved = movement_system(state, agent_id, next_pos)
        if moved == state:
            break
        state = moved
        pos = state.position[agent_id]
    return state
```

You would need to pass or infer the last move direction (e.g., compute from prev_position -> position, or thread it through `_step_move`).

5. Rendering asset
- Add an `AppearanceName` or reuse an existing one in `renderer/texture.py` by mapping properties to an asset.
- Optionally supply a directory of multiple variations.

Example B: New damage type “PoisonCloud” that applies low damage over time
1. Component:
- `PoisonCloud` with `amount` per turn.
2. System:
- A system that finds entities co-located with clouds each substep and applies damage.
3. Factory:
- `create_poison_cloud(amount=1, priority=7)`.

This mirrors the existing `Damage` pattern but lets you control timing or stacking in a custom system.


## Tips and gotchas

- Level vs. State
  - `EntitySpec` is authoring-time: no `Position`, no ID. `State` is runtime: immutable, entities have IDs and `Position`.
- Placing multiple specs
  - You can add many specs to one cell; rendering uses `Appearance` background/main/icon with priority to layer them.
- Background/main/icon
  - Use `Appearance(background=True)` for tiles; the renderer picks one background per cell. Use `icon=True` for small corner overlays (up to 4 per cell).
- Movement vs. Collidable/Blocking
  - Agent movement checks `Blocking` (unless `Phasing` is active). Pathfinding uses the same rule. `Collidable` is used in interactions (damage overlap, portal trail) rather than blocking movement.
- Push vs. move direction
  - `push_system` computes push direction from agent’s attempted step. If the push destination is blocked or OOB, push doesn’t happen.
- Effects and limits
  - `Speed`, `Phasing`, `Immunity` can have `TimeLimit` and/or `UsageLimit`. Time ticks each turn; usage decrements when the effect is actually used (e.g., passing through a block or making extra moves).
- Doors and keys
  - `unlock_system` checks adjacent cells; correct key removes `Locked` and `Blocking` from doors and consumes the key from the agent’s Inventory.
- Portals
  - Teleportation happens when a collidable entity moves into the portal cell (detected via trail and prev_position). Ensure paired portals have valid positions.
- Procedural randomness
  - Use `seed` arguments on Level or generators for deterministic layouts. Some systems (like `windy_move_fn`) derive per-turn randomness from `state.seed` and `state.turn`.
- Garbage collection
  - `run_garbage_collector` prunes entities not reachable via state maps (e.g., removed collectibles, expired effects with no references). Don’t keep critical data only in local variables.


## Appendix: Extra examples

Mini sokoban-like push puzzle:

```python
from grid_universe.levels.grid import Level
from grid_universe.levels.factories import create_floor, create_wall, create_box, create_exit, create_agent
from grid_universe.moves import default_move_fn
from grid_universe.objectives import all_pushable_at_exit_objective_fn
from grid_universe.levels.convert import to_state

w, h = 7, 5
level = Level(w, h, move_fn=default_move_fn, objective_fn=all_pushable_at_exit_objective_fn, seed=5)

# floors
for y in range(h):
    for x in range(w):
        level.add((x, y), create_floor())

# walls
for x in range(w):
    level.add((x, 0), create_wall())
    level.add((x, h-1), create_wall())
for y in range(h):
    level.add((0, y), create_wall())
    level.add((w-1, y), create_wall())

# agent, box, goal
level.add((1, 2), create_agent())
level.add((3, 2), create_box(pushable=True))
level.add((5, 2), create_exit())

state = to_state(level)
```

Start agent with a powerup and a key:

```python
from grid_universe.levels.factories import create_agent, create_key, create_speed_effect

agent = create_agent(health=7)
agent.inventory_list.append(create_key("gold"))
agent.status_list.append(create_speed_effect(multiplier=2, time=5))
level.add((1, 1), agent)
```

Group-colored keys/doors/portals (renderer)
- The texture renderer includes grouping rules to recolor related entities deterministically:
  - Keys/doors with the same `key_id` share a hue.
  - Paired portals share a hue.
- You get visual grouping automatically when assets are recolored per-group.


## References

- Authoring API: `grid_universe/levels/grid.py`, `grid_universe/levels/entity_spec.py`, `grid_universe/levels/factories.py`
- Conversion: `grid_universe/levels/convert.py`
- Procedural: `grid_universe/examples/maze.py`
- Runtime state and systems: `grid_universe/state.py`, `grid_universe/systems/*`
- Movement and objectives: `grid_universe/moves.py`, `grid_universe/objectives.py`
- Rendering: `grid_universe/renderer/texture.py`