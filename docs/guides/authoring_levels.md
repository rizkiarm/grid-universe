# Authoring Levels

This guide teaches you how to design levels using the authoring-time Level API, wire relationships at authoring time (portals, doors/keys, pathfinding), and convert to the immutable runtime State. It also includes patterns, best practices, and troubleshooting tips.

Contents

- Concepts and workflow
- Level structure and coordinates
- Placing entities with factories
- Appearance, priority, and layering
- Wiring relationships (authoring-time refs)
- Inventory and Status (nested entities)
- Conversion Level → State → Level (round-trip)
- Patterns and recipes
- Determinism and reproducibility
- Debugging and validation
- FAQs and pitfalls


## Concepts and workflow

- `EntitySpec`: A mutable bag of components representing a “thing” you place on the grid. It has no `Position` or ID.

- `Level`: A mutable grid (width × height) of lists of `EntitySpec`. You place specs with `Level.add((x, y), spec)`.

- `State`: An immutable runtime snapshot of entities with unique integer IDs and component maps. Systems operate on `State`.

- Conversion:

    - `levels.convert.to_state(level)`: materializes `EntitySpec` into runtime entities (with `Position`), resolves authoring refs, and creates nested effect/item entities.

    - `levels.convert.from_state(state)`: reconstructs a `Level` with placed `EntitySpec` and restores authoring references for positioned entities.

Typical flow:
```python
from grid_universe.levels.grid import Level
from grid_universe.levels.factories import create_floor, create_agent, create_exit
from grid_universe.moves import default_move_fn
from grid_universe.objectives import default_objective_fn
from grid_universe.levels.convert import to_state

level = Level(7, 5, move_fn=default_move_fn, objective_fn=default_objective_fn, seed=123)
# Place tiles and objects...
state = to_state(level)  # immutable State, ready for systems
```


## Level structure and coordinates

- `Level.grid` is a 2D array accessed as `grid[y][x]`, each cell is a list of `EntitySpec`.

- Coordinates: `(x, y)` with `0 ≤ x < width` and `0 ≤ y < height`.

- A single cell may contain multiple objects (e.g., background + item + hazard).

Useful methods:

- `add((x, y), spec)`: place a single entity.

- `add_many([((x1, y1), spec1), ...])`: place multiple entities.

- `remove((x, y), spec)`: remove by object identity (returns bool).

- `remove_if((x, y), predicate)`: remove all matching objects (returns count).

- `move_obj(from_pos, spec, to_pos)`: move a specific object between cells.

- `clear_cell((x, y))`: remove all objects in a cell.

- `objects_at((x, y))`: get a shallow copy of the cell’s objects.

Example:
```python
from grid_universe.levels.grid import Level
from grid_universe.levels.factories import create_floor, create_wall
from grid_universe.moves import default_move_fn
from grid_universe.objectives import default_objective_fn

w, h = 7, 5
level = Level(w, h, move_fn=default_move_fn, objective_fn=default_objective_fn, seed=1)

# Floors everywhere
for y in range(h):
    for x in range(w):
        level.add((x, y), create_floor())

# Surrounding walls
for x in range(w):
    level.add((x, 0), create_wall())
    level.add((x, h-1), create_wall())
for y in range(h):
    level.add((0, y), create_wall())
    level.add((w-1, y), create_wall())
```


## Placing entities with factories

Factories create `EntitySpec` with sensible defaults. Common ones:

Tiles:

- `create_floor(cost_amount=1)`: background tile with `Cost` applied post-step.

- `create_wall()`: background tile with `Blocking`.

Player and items:

- `create_agent(health=5)`: agent with `Inventory` and `Status`.

- `create_coin(reward: Optional[int])`: `Collectible`; `Rewardable` if reward provided.

- `create_core(reward: Optional[int], required=True)`: collectible; often `Required`.

Doors and portals:

- `create_key(key_id)`: collectible item with `Key(key_id)`.

- `create_door(key_id)`: `Blocking` + `Locked(key_id)`.

- `create_portal(pair=None)`: portal; pair both ends using authoring refs (see “Wiring”).

Objects and hazards:

- `create_box(pushable=True)`: `Blocking` + `Collidable`; optionally `Pushable`.

- `create_hazard(appearance, damage, lethal=False, priority=7)`: e.g., `SPIKE` or `LAVA` tile.

Effects (powerups):

- `create_speed_effect(multiplier, time=None, usage=None)`

- `create_immunity_effect(time=None, usage=None)`

- `create_phasing_effect(time=None, usage=None)`

Minimal placement:
```python
from grid_universe.levels.factories import create_agent, create_coin, create_exit

level.add((1, 1), create_agent(health=7))
level.add((2, 2), create_coin(reward=10))
level.add((5, 3), create_exit())
```


## Appearance, priority, and layering

Rendering uses the `Appearance` component to decide what to draw and how to layer:

- `background=True`: background tiles; exactly one background is chosen per cell for rendering.

- `icon=True`: corner overlays; up to four icons are drawn with subicon scaling.

- `priority`: resolves ordering; lower numeric priority is considered “more foreground” for main object, while backgrounds use highest numeric priority among backgrounds.

Rules used by the texture renderer:

- Background: chooses the item with `background=True` and the lowest priority after sorting descending (i.e., visually behind).

- Main: among non-backgrounds, chooses the highest priority (lowest number).

- Corner icons: up to four `icon=True` objects (by top priority).

- Others: remaining non-background, non-icon items are drawn behind the main but above background.

Tip: Use priority consistently:

- Background tiles: higher numeric priority (e.g., 10 for floors, 9 for walls).

- Foreground objects: lower numbers (e.g., 1 for monsters, 2 for boxes, 4 for icons).


## Wiring relationships (authoring-time refs)

Some relationships are easier to define at authoring time and resolved during conversion.

Portals (pairing both ends)
```python
from grid_universe.levels.factories import create_portal

p1 = create_portal()
p2 = create_portal(pair=p1)  # reciprocal authoring refs
level.add((1, 1), p1)
level.add((5, 3), p2)
# to_state wires Portal(pair_entity=<eid_of_other>) for both ends
```

Enemy pathfinding (target the agent)
```python
from grid_universe.levels.factories import create_agent, create_monster
from grid_universe.components.properties import PathfindingType

agent = create_agent()
enemy = create_monster(damage=3, lethal=False, pathfind_target=agent, path_type=PathfindingType.PATH)
level.add((2, 2), agent)
level.add((4, 4), enemy)
# to_state sets enemy Pathfinding(target=<agent_eid>, type=PATH)
```

Multiple doors/keys
```python
from grid_universe.levels.factories import create_key, create_door

level.add((2, 2), create_key("red"))
level.add((4, 2), create_door("red"))

level.add((2, 3), create_key("blue"))
level.add((5, 2), create_door("blue"))
# Unlocking requires the matching key in inventory
```

Notes:

- Wiring is resolved only if both referenced objects are actually placed on the grid at conversion time.

- `from_state` restores authoring refs for positioned entities where possible.


## Inventory and Status (nested entities)

You can pre-load items and effects onto a holder (e.g., the agent) via authoring-only lists on `EntitySpec`:

- `inventory_list`: list of `EntitySpec` that become separate item entities in the holder’s `Inventory.item_ids`. These nested entities are created with no `Position`.

- `status_list`: list of `EntitySpec` that become separate effect entities in the holder’s `Status.effect_ids`. Also created with no `Position`.

Example: Start with a key and a time-limited speed effect
```python
from grid_universe.levels.factories import create_agent, create_key, create_speed_effect

agent = create_agent()
agent.inventory_list.append(create_key("gold"))
agent.status_list.append(create_speed_effect(multiplier=2, time=5))  # time-limited
level.add((1, 1), agent)
```

Merging behavior:

- If the holder already has an `Inventory`/`Status` component, the lists are merged into it.

- If missing, an empty `Inventory`/`Status` is created and then populated.


## Conversion Level → State → Level (round-trip)

To State (`to_state`)

- Each placed `EntitySpec` becomes a runtime entity with:

  - A unique integer `EntityID`

  - A `Position` component equal to the grid cell

  - All authored components copied to the appropriate `State` stores

- Authoring refs are resolved:

  - Pathfinding target references → `Pathfinding.target` entity ID

  - Portal pair references → mutual `Portal(pair_entity=<eid>)`

- Nested lists are materialized:

  - `inventory_list`/`status_list` become separate entities, referenced from `Inventory`/`Status` on the holder.

From State (`from_state`)

- Rebuilds a `Level` with placed `EntitySpec` for entities that have `Position`.

- Restores `inventory_list`/`status_list` from `Inventory.item_ids` / `Status.effect_ids`.

- Restores authoring refs for `Pathfinding` targets and portal pairs when both ends are positioned.

- Useful for:

  - Inspecting/editing a runtime State

  - Saving/loading editor views

  - Debugging placements

Example round-trip:
```python
from grid_universe.levels.convert import to_state, from_state

state = to_state(level)
# ... run some steps, or serialize state ...
level2 = from_state(state)
```


## Patterns and recipes

Sokoban-like push puzzle
```python
from grid_universe.levels.factories import create_box, create_exit, create_agent, create_floor
from grid_universe.levels.grid import Level
from grid_universe.moves import default_move_fn
from grid_universe.objectives import all_pushable_at_exit_objective_fn

w, h = 7, 5
lvl = Level(w, h, move_fn=default_move_fn, objective_fn=all_pushable_at_exit_objective_fn, seed=5)

# Floors
for y in range(h):
    for x in range(w):
        lvl.add((x, y), create_floor())

# Agent, box, exit
lvl.add((1, 2), create_agent())
lvl.add((3, 2), create_box(pushable=True))
lvl.add((5, 2), create_exit())
```

Door/Key corridor with two locks
```python
from grid_universe.levels.factories import create_floor, create_agent, create_key, create_door
from grid_universe.levels.grid import Level
from grid_universe.moves import default_move_fn
from grid_universe.objectives import default_objective_fn

lvl = Level(9, 3, move_fn=default_move_fn, objective_fn=default_objective_fn, seed=2)
for y in range(3):
    for x in range(9):
        lvl.add((x, y), create_floor())

lvl.add((1, 1), create_agent())
lvl.add((2, 1), create_key("red"))
lvl.add((4, 1), create_door("red"))
lvl.add((6, 1), create_key("blue"))
lvl.add((7, 1), create_door("blue"))
```

Portals across rooms
```python
from grid_universe.levels.factories import create_portal

p1 = create_portal()
p2 = create_portal(pair=p1)
level.add((1, 1), p1)   # room A
level.add((8, 3), p2)   # room B
```

Preloading effects and items
```python
from grid_universe.levels.factories import create_agent, create_key, create_speed_effect, create_immunity_effect

agent = create_agent()
agent.inventory_list.extend([
    create_key("alpha"),
    create_key("beta"),
])
agent.status_list.extend([
    create_speed_effect(multiplier=2, usage=3),
    create_immunity_effect(time=2),
])
level.add((1, 1), agent)
```


## Determinism and reproducibility

- `Level(seed=...)`: store a seed for procedural generation or deterministic behavior.

- Systems may derive randomness from `(state.seed, state.turn)`, e.g., `windy_move_fn`.

- The texture renderer uses `State.seed` to choose a file variation from a directory (if a texture map entry points to a folder).

Best practices:

- Always pass a seed for repeatable layouts and runs.

- Keep deterministic ordering when placing from lists (shuffle with a local RNG seeded by `Level.seed` when you want variety that is still repeatable).


## Debugging and validation

Check placements before conversion:
```python
for y in range(level.height):
    for x in range(level.width):
        objs = level.objects_at((x, y))
        if objs:
            print((x, y), [type(o).__name__ for o in objs])
```

Inspect runtime State:
```python
from grid_universe.levels.convert import to_state
st = to_state(level)

print("Entities:", len(st.entity))
print("Agent IDs:", list(st.agent.keys()))
print("Positions:", len(st.position))

# Summarized description (non-empty fields)
desc = st.description
for k, v in desc.items():
    print(k, type(v), len(v) if hasattr(v, "__len__") else "")
```

Validate a minimal playable state:

- Ensure at least one `Agent` with a `Position` exists.

- Ensure the objective is attainable (e.g., required cores exist and an `Exit` is reachable).

- Use the renderer for a quick visual sanity check.


## FAQs and pitfalls

Q: My portal pair didn’t wire up.

- Ensure both ends are placed in the `Level` prior to `to_state`.

- Use `create_portal(pair=other)` or set `portal_pair_ref` on both ends.

- `from_state` only restores refs if both ends have `Position`.

Q: Items/effects disappear after pickup.

- `Collectible`s are removed from world (`position`/`collectible` maps) when collected, and referenced from `Inventory`/`Status` on the collector.

- This is expected; use `State.inventory` or `State.status` to find collected items/effects.

Q: The main object in a cell isn’t the one I expected.

- Check `Appearance.priority` and flags. Background tiles should have higher numeric priority (e.g., 10), foreground actors lower (e.g., 1–4). Only one background is drawn; main object is the non-background with highest priority (lowest number).

Q: A push fails even though the next cell is free.

- `push_system` computes destination from `current_pos → next_pos`. If the destination is out of bounds or blocked (`Blocking`/`Pushable`/`Collidable` unless phasing applies), the push won’t occur.

Q: Pathfinding enemies don’t move.

- Ensure the enemy has `Pathfinding` with a valid target (wired via authoring ref or directly in components).

- Moving/pathfinding occurs each step before the agent moves.

- They obey bounds and `Blocking` (collidable is ignored for pathfinding movement checks).

Q: My effect never triggers or expires.

- For time-limited effects: `TimeLimit` ticks each turn (`status_tick_system`).

- For usage-limited effects: usage decrements only when the effect is actually used (e.g., `Speed` multiplies movement; `Phasing` to ignore `Blocking`; `Immunity` negates a damage instance).


## Next steps

- See “Movement and Objectives” for configuring `MoveFn`/`ObjectiveFn` and speed/phasing/immunity behaviors.

- See “Rendering” for texture maps, recoloring groups (keys/doors by `key_id`, portal pairs), and moving overlays.

- Explore “Level Examples” for examples of complete generator.