# API Reference

This page groups and expands the public API by area. Each section includes a brief description of the modules followed by auto-generated API docs (mkdocstrings). Use the grouped structure to locate functionality quickly, then dive into the detailed signatures and docstrings.

Contents

- How to read this reference
- Core
- Components
- Systems
- Utilities
- Levels (Authoring)
- Rendering
- Examples
- Gym Environment
- Registries and enums


## How to read this reference

- Modules are grouped by domain. Each entry links to the module’s classes and functions.

- Headings provide a short summary of what the module does before the auto-doc.

- Code examples for common tasks live in the Functional API and Guides pages; this reference focuses on signatures and behavior.

- Tip: If module headings are too large in the Table of Contents, set `heading_level: 3` in `mkdocs.yml` under mkdocstrings options so modules render as H3 under these H2 sections.


## Core

### State and stepping

- `grid_universe.state`: Immutable State dataclass holding component stores, meta, and RNG seed.

- `grid_universe.step`: The main reducer that applies one action and orchestrates all systems in the correct order.

::: grid_universe.state
::: grid_universe.step

### Actions and types

- `grid_universe.actions`: Agent actions, including movement and non-movement (use key, pick up, wait); includes GymAction index mapping.

- `grid_universe.types`: Core type aliases and enums used across the codebase (`EntityID`, `MoveFn`, `ObjectiveFn`, `EffectType`, `EffectLimit`).

- `grid_universe.objectives`: Built-in objective functions (default, collect, exit, unlock, push), plus a registry for selection by name.

::: grid_universe.actions
::: grid_universe.types
::: grid_universe.objectives


## Components

### Property components (authoring/runtime)

- Appearance controls rendering and layering; Position locates entities. Other components model gameplay (Blocking, Collectible, etc.).

::: grid_universe.components.properties.appearance
::: grid_universe.components.properties.position
::: grid_universe.components.properties.agent
::: grid_universe.components.properties.blocking
::: grid_universe.components.properties.collectible
::: grid_universe.components.properties.collidable
::: grid_universe.components.properties.cost
::: grid_universe.components.properties.damage
::: grid_universe.components.properties.dead
::: grid_universe.components.properties.exit
::: grid_universe.components.properties.health
::: grid_universe.components.properties.inventory
::: grid_universe.components.properties.key
::: grid_universe.components.properties.lethal_damage
::: grid_universe.components.properties.locked
::: grid_universe.components.properties.moving
::: grid_universe.components.properties.pathfinding
::: grid_universe.components.properties.portal
::: grid_universe.components.properties.pushable
::: grid_universe.components.properties.required
::: grid_universe.components.properties.rewardable
::: grid_universe.components.properties.status

### Effects and limits

- Effect entities are referenced from `Status.effect_ids` and may include limits.

::: grid_universe.components.effects.immunity
::: grid_universe.components.effects.phasing
::: grid_universe.components.effects.speed
::: grid_universe.components.effects.time_limit
::: grid_universe.components.effects.usage_limit
::: grid_universe.components.effects


## Systems

### Movement, pathfinding, position

- `movement_system`: Agent’s single-step application obeying Blocking unless Phasing is active.

- `moving_system`: Autonomous movers with axis/direction/speed/bounce.

- `pathfinding_system`: Greedy or A* pursuit.

- `position_system`: Snapshots positions into `prev_position` at turn start.

::: grid_universe.systems.movement
::: grid_universe.systems.moving
::: grid_universe.systems.pathfinding
::: grid_universe.systems.position

### Interactions (portal, damage, push, tile)

- `portal_system`: Teleports collidable entrants to the paired portal.

- `damage_system`: Applies Damage/LethalDamage on co-location and cross paths; respects Immunity/Phasing.

- `push_system`: Pushes Pushable objects if destination is free; moves agent and pushable.

- Tile systems: Reward and Cost handling.

::: grid_universe.systems.portal
::: grid_universe.systems.damage
::: grid_universe.systems.push
::: grid_universe.systems.tile

### Status and terminal

- Status tick/GC: Decrement time limits and garbage-collect expired/orphaned effects.

- Terminal: Win/lose conditions.

::: grid_universe.systems.status
::: grid_universe.systems.terminal


## Utilities

### Grid and ECS helpers

- Grid helpers: bounds, blocking, wrap, push destination math.

- ECS helpers: query entities at a position and with components.

::: grid_universe.utils.grid
::: grid_universe.utils.ecs

### Status/inventory and health helpers

- Status helpers: finding/consuming effects with limits.

- Inventory helpers: keys lookup; add/remove items.

- Health helpers: damage application and death check.

::: grid_universe.utils.status
::: grid_universe.utils.inventory
::: grid_universe.utils.health

### Rendering helpers and image ops

- Numpy-based HSV recoloring preserving tone.

- Direction triangle overlays.

::: grid_universe.utils.image

### Trail and terminal checks

- Trail: record traversed positions between prev and current.

- Terminal: convenience validation and terminal checks.

::: grid_universe.utils.trail
::: grid_universe.utils.terminal

### GC (entity pruning)

- Prune entities not reachable from any live structure to keep State compact.

::: grid_universe.utils.gc


## Levels (Authoring)

### Authoring model and factories

- Level: mutable grid of `EntitySpec` for authoring.

- `EntitySpec`: bag of components with authoring-only lists and wiring refs.

- Factories: ready-made objects (agent, floor, wall, key/door, portal, box, hazards, enemies, powerups).

::: grid_universe.levels.grid
::: grid_universe.levels.entity_spec
::: grid_universe.levels.factories

### Conversion between Level and State

- `to_state`: instantiate entities with `Position`; wire references; materialize nested lists.

- `from_state`: reconstruct authoring specs from positioned entities; restore lists and refs.

::: grid_universe.levels.convert


## Rendering

### Texture renderer

- `TextureRenderer`: Compose background, main, corner icons; pick textures by `(AppearanceName, properties)`; recolor groups; draw moving overlays.

::: grid_universe.renderer.texture


## Examples

### Procedural maze

- Rich generator with walls/floors, agent/exit, keys/doors, portals, enemies, hazards, and powerups. Provides knobs for density and counts.

::: grid_universe.examples.maze


## Gym Environment

- `GridUniverseEnv`: Gymnasium-compatible Env returning image observations and structured info; reward is delta score.

::: grid_universe.gym_env


## Registries and enums

- Movement registry: Name → `MoveFn`.

- Objective registry: Name → `ObjectiveFn`.

- Actions: string enum for core actions; `GymAction` int enum for compatibility.

- `EffectType` and `EffectLimit` enums.

Reference snippets:

```python
from grid_universe.moves import MOVE_FN_REGISTRY
from grid_universe.objectives import OBJECTIVE_FN_REGISTRY
from grid_universe.actions import Action, GymAction

print(MOVE_FN_REGISTRY.keys())
print(OBJECTIVE_FN_REGISTRY.keys())
print(list(Action))
print(list(GymAction))
```


# Schemas and Data Shapes

This page captures common data structures you may want to reference without digging into code: observation dicts from the Gym env, texture map keys/values, and group recoloring rules.

Contents

- Gym observation schema
- Texture map schema
- Grouping rules and color mapping


## Gym observation schema

Observation (`obs: Dict[str, Any]`) returned by `GridUniverseEnv`:

- `image`

    - Type: `numpy.ndarray`

    - Shape: `(H, W, 4)`, `dtype=uint8` (RGBA)

- `info`

    - `agent`

        - `health`

            - `health`: int or `-1`

            - `max_health`: int or `-1`

        - `effects`: list of effect entries

            - `id`: int

            - `type`: "", "IMMUNITY", "PHASING", "SPEED"

            - `limit_type`: "", "TIME", "USAGE"

            - `limit_amount`: int or `-1`

            - `multiplier`: int (SPEED only; `-1` otherwise)

        - `inventory`: list of item entries

            - `id`: int

            - `type`: "item" | "key" | "core" | "coin"

            - `key_id`: str ("" if not a key)

            - `appearance_name`: str ("" if unknown)

    - `status`

        - `score`: int

        - `phase`: "ongoing" | "win" | "lose"

        - `turn`: int

    - `config`

        - `move_fn`: str (function name)

        - `objective_fn`: str (function name)

        - `seed`: int (or `-1`)

        - `width`: int

        - `height`: int

Action space:

- `Discrete(7)`, mapping to `Action` enum indices:

    - `0`: UP

    - `1`: DOWN

    - `2`: LEFT

    - `3`: RIGHT

    - `4`: USE_KEY

    - `5`: PICK_UP

    - `6`: WAIT

Reward:

- Delta score between steps (float).


## Texture map schema

TextureMap entry key/value:

- Key

    - `Tuple[AppearanceName, Tuple[str, ...]]`

    - Example: `(AppearanceName.BOX, ())`, `(AppearanceName.BOX, ("pushable",))`

- Value

    - `str`: path under `asset_root` to a file or directory

    - If directory: renderer picks a deterministic file per `state.seed`

Resolution:

- Asset path = `f"{asset_root}/{value}"`

- File types: `.png`, `.jpg`, `.jpeg`, `.gif`

Property matching:

- When rendering an entity, the renderer constructs the set of string “properties” for that entity based on which component maps contain its EID (e.g., `"pushable"`, `"pathfinding"`, `"dead"`, `"locked"`, `"required"`).

- The best-matching texture is chosen by maximizing overlap and minimizing unmatched properties among the available keys for that `AppearanceName`.


## Grouping rules and color mapping

Grouping rules (`derive_groups`) assign entities into color groups, e.g.:

- Keys/doors by key id:

    - `key_door_group_rule → "key:<key_id>"`

- Paired portals:

    - `portal_pair_group_rule → "portal:<min_eid>-<max_eid>"`

Color mapping:

- `group_to_color(group_id) → (r, g, b)`

    - Deterministic mapping using `random.Random(group_id)` to sample HSV; converted to RGB.

Recolor:

- `apply_recolor_if_group(image, group)` replaces hue while preserving per-pixel tone (value) and, by default, saturation.

Extensibility:

- Add new `GroupRule` functions to `DEFAULT_GROUP_RULES` (locally in your render wrapper) to recolor custom categories consistently.

```python
from typing import Optional
from grid_universe.state import State
from grid_universe.types import EntityID

def my_group_rule(state: State, eid: EntityID) -> Optional[str]:
    if eid in state.pushable:
        return "pushable"
    return None
```