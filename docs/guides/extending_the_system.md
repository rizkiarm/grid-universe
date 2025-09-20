# Extending the System

This guide explains how to add new components, systems, movement/objective functions, rendering rules, and authoring-time factories to Grid Universe. It walks through the required code changes, ordering in the `step()` lifecycle, testing strategies, and common pitfalls.

Contents

- Extension points overview
- Adding a new component
- Mapping components for authoring and runtime
- Creating factories (authoring-time helpers)
- Implementing a new system
- Wiring the system into the `step()` lifecycle
- Rendering integration (textures, grouping, recolor)
- Adding a new `MoveFn`
- Adding a new `ObjectiveFn`
- Serialization and conversion considerations
- Testing and determinism
- Performance and maintenance tips


## Extension points overview

Grid Universe is built on ECS (Entity–Component–System). You can extend it by:

- Components

    - New “property” components (e.g., `BouncePad`, `PoisonCloud`).

    - New “effect” components (e.g., `Slow`, `DoubleScore`).

- Systems

    - Pure functions `State -> State` that read/write relevant component maps.

- Movement and objectives

    - `MoveFn`: different movement semantics.

    - `ObjectiveFn`: new win conditions.

- Authoring-time tooling

    - `EntitySpec` fields and `Level` factories for convenient content creation.

- Rendering

    - Texture maps, grouping rules, recoloring, overlays.

- Gym environment integration

    - Use a custom `initial_state_fn` for your levels; no changes to env class needed.


## Adding a new component

Suppose we want a “BouncePad” tile that pushes the agent forward an extra step after entering the tile.

1) Create the component dataclass

- Place it under `grid_universe/components/properties` if it is a property, or `grid_universe/components/effects` if it is an effect.

```python
# grid_universe/components/properties/bounce_pad.py
from dataclasses import dataclass

@dataclass(frozen=True)
class BouncePad:
    strength: int = 1  # number of extra steps to push in the same direction
```

2) Export it

- Export from `grid_universe/components/properties/__init__.py` and `grid_universe/components/__init__.py`.

3) Add it to State

- Add a `PMap` field keyed by `EntityID` in `grid_universe/state.py`.

```python
# grid_universe/state.py (extract)
from grid_universe.components.properties import BouncePad
from pyrsistent import PMap, pmap
from grid_universe.types import EntityID

@dataclass(frozen=True)
class State:
    # ...
    bounce_pad: PMap[EntityID, BouncePad] = pmap()
    # ...
```

4) Map it for authoring

- Add an entry to `COMPONENT_TO_FIELD` in `grid_universe/levels/entity_spec.py`.

```python
# grid_universe/levels/entity_spec.py (extract)
from grid_universe.components.properties import BouncePad

COMPONENT_TO_FIELD = {
    # ...
    BouncePad: "bounce_pad",
}
```

5) Import/export hygiene

- Ensure imports do not create circular references.

- Keep consistent naming and placement alongside existing components.


## Mapping components for authoring and runtime

- Authoring-time `EntitySpec` is a bag of optional component fields (`None` means absent).

- Conversion to State (`levels.convert.to_state`):

    - Entities placed on the Level grid become runtime entities with `Position`.

    - Fields present on `EntitySpec` are copied into the corresponding State component stores.

- Conversion from State (`levels.convert.from_state`):

    - Positioned entities are reconstructed into `EntitySpec` with components set from State fields.

    - Inventory/status lists are reconstructed as authoring-only nested lists.


## Creating factories (authoring-time helpers)

Add a helper in `levels/factories.py` to quickly create your object with sensible defaults.

```python
# grid_universe/levels/factories.py (extract)
from grid_universe.components.properties import Appearance, AppearanceName, BouncePad
from .entity_spec import EntitySpec

def create_bounce_pad(strength: int = 1, priority: int = 6) -> EntitySpec:
    return EntitySpec(
        appearance=Appearance(name=AppearanceName.GEM, priority=priority),  # reuse an icon, or add a new appearance
        bounce_pad=BouncePad(strength=strength),
        # Typically no Blocking/Collidable; acts like a floor behavior overlay
    )
```

Notes:

- For new tiles with blocking behavior, include `Blocking`.

- For damage-like hazards, add `Damage` and optionally `LethalDamage`.

- For collectables, add `Collectible` and optionally `Rewardable`.


## Implementing a new system

Systems are small, pure functions that transform State. Let’s implement a `bounce_pad_system` that, after a successful agent move, pushes the agent forward by `BouncePad.strength` steps in the same direction of travel.

Key decision: where to hook

- Since this depends on the last move direction, we should run after `movement_system` within each submove (i.e., inside the per-substep suite) or derive direction from `prev_position → position`.

- A simple approach: compute direction from `(prev_position[agent] -> position[agent])` for the current step.

```python
# grid_universe/systems/bounce_pad.py
from dataclasses import replace
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.components import Position
from grid_universe.utils.ecs import entities_with_components_at
from grid_universe.utils.grid import is_in_bounds, is_blocked_at

def bounce_pad_system(state: State, agent_id: EntityID) -> State:
    # If no movement happened, there's no direction to push
    curr = state.position.get(agent_id)
    prev = state.prev_position.get(agent_id)
    if curr is None or prev is None or (curr.x == prev.x and curr.y == prev.y):
        return state

    dx = (curr.x > prev.x) - (curr.x < prev.x)
    dy = (curr.y > prev.y) - (curr.y < prev.y)
    if dx == 0 and dy == 0:
        return state

    # Is there a BouncePad at the agent's current tile?
    pads = entities_with_components_at(state, curr, state.bounce_pad)
    if not pads:
        return state

    pad_id = pads[0]
    strength = max(0, state.bounce_pad[pad_id].strength)
    if strength == 0:
        return state

    # Push forward up to strength steps (stop if blocked or OOB)
    pos = curr
    for _ in range(strength):
        next_pos = Position(pos.x + dx, pos.y + dy)
        if not is_in_bounds(state, next_pos) or is_blocked_at(state, next_pos, check_collidable=False):
            break
        # Move the agent by directly updating position (since we're inside a system)
        state = replace(state, position=state.position.set(agent_id, next_pos))
        pos = next_pos

    return state
```

Notes:

- We used `prev_position` to derive direction. Ensure `position_system` ran earlier this step.

- We used `is_blocked_at` with `check_collidable=False` to mirror `movement_system`’s blocking rule.

- For multi-agent or NPC effects, loop over all relevant entities.


## Wiring the system into the `step()` lifecycle

The `step()` lifecycle (`grid_universe/step.py`) calls:

- Pre: `position_system → moving_system → pathfinding_system → status_tick_system`

- Per-submove (for MOVE actions): `push_system → movement_system → portal_system → damage_system → tile_reward_system`

- Post: `status_gc_system → tile_cost_system → win_system → lose_system → turn++ → run_garbage_collector`

To include `bounce_pad_system` after each submove, insert it into `_after_substep`:

```python
# grid_universe/step.py (extract)
from grid_universe.systems.bounce_pad import bounce_pad_system

def _after_substep(state: State, action: Action, agent_id: EntityID) -> State:
    state = portal_system(state)
    state = damage_system(state)
    state = tile_reward_system(state, agent_id)
    # Add bounce behavior after we've potentially teleported/damaged/scored
    state = bounce_pad_system(state, agent_id)
    return state
```

Ordering rationale:

- We want the pad to react to where the agent ended up after any portal teleport. If you want bounce to happen before portals or before damage, adjust ordering accordingly.

Alternative hooks:

- If your system must happen only once per action, add it to `_after_step`.

- If it changes world tiles before movement, place it before `moving_system` (rare).


## Rendering integration (textures, grouping, recolor)

- Add a texture entry for your new appearance or reuse existing ones in `renderer.texture.DEFAULT_TEXTURE_MAP`.

- If you want group-based recoloring (like keys/doors, portals), add a `GroupRule` that assigns a group ID string to your entities and the renderer will recolor via `apply_recolor_if_group`.

Example: color all BouncePads by strength bucket

```python
# custom grouping rule
from typing import Optional
from grid_universe.state import State
from grid_universe.types import EntityID

def bounce_pad_group_rule(state: State, eid: EntityID) -> Optional[str]:
    if eid in state.bounce_pad:
        s = state.bounce_pad[eid].strength
        bucket = "low" if s <= 1 else "mid" if s <= 3 else "high"
        return f"bpad:{bucket}"
    return None
```

- To use this, pass a custom rules list to `derive_groups` in `renderer.texture.render` (copy and adapt the function if needed), appending your rule to `DEFAULT_GROUP_RULES`.

- For overlays: you can mimic `draw_direction_triangles_on_image` to add special glyphs on top of textures if the overlay depends on component state.


## Adding a new `MoveFn`

`MoveFn` signature: `MoveFn(State, EntityID, Action) -> Sequence[Position]`. The function proposes positions for a single high-level action.

Example: “dash then drift” `MoveFn`

```python
from typing import Sequence
from grid_universe.components import Position
from grid_universe.actions import Action
from grid_universe.types import EntityID
from grid_universe.state import State

def dash_then_drift_move_fn(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    pos = state.position[eid]
    dx, dy = {
        Action.UP: (0, -1),
        Action.DOWN: (0, 1),
        Action.LEFT: (-1, 0),
        Action.RIGHT: (1, 0),
    }[action]
    # 2-step dash then one orthogonal drift to the right of the direction
    path = [Position(pos.x + dx, pos.y + dy), Position(pos.x + 2*dx, pos.y + 2*dy)]
    drift_dx, drift_dy = -dy, dx  # rotate 90 degrees
    path.append(Position(path[-1].x + drift_dx, path[-1].y + drift_dy))
    return path
```

Register it for convenience:

```python
# grid_universe/moves.py (append)
from grid_universe.types import MoveFn

def dash_then_drift_move_fn(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    # (same as above)
    ...

MOVE_FN_REGISTRY["dash_drift"] = dash_then_drift_move_fn
```

Notes:

- Do not enforce bounds/blocking inside the `MoveFn`; systems will handle that.

- If you need randomness, derive it deterministically from `(state.seed, state.turn)`.


## Adding a new `ObjectiveFn`

`ObjectiveFn` signature: `ObjectiveFn(State, EntityID) -> bool`. Return `True` to set win.

Example: “survive N turns and stand on exit”

```python
from grid_universe.types import ObjectiveFn, EntityID
from grid_universe.state import State
from grid_universe.utils.ecs import entities_with_components_at

def survive_and_exit_objective_fn_factory(turns: int) -> ObjectiveFn:
    def _obj(state: State, agent_id: EntityID) -> bool:
        if state.turn < turns:
            return False
        pos = state.position.get(agent_id)
        if pos is None:
            return False
        return len(entities_with_components_at(state, pos, state.exit)) > 0
    return _obj
```

Register it if desired:

```python
# grid_universe/objectives.py (append)
from grid_universe.types import ObjectiveFn

def survive_and_exit_objective_fn_factory(turns: int) -> ObjectiveFn:
    # (same as above)
    ...

OBJECTIVE_FN_REGISTRY["survive_exit_20"] = survive_and_exit_objective_fn_factory(20)
```

Notes:

- Keep it fast and pure: do not mutate State.

- Prefer local checks (e.g., positions, component presence) over scanning all stores.


## Serialization and conversion considerations

- `to_state(level)` copies present components; ensure your new component is included in `COMPONENT_TO_FIELD` and the `State` class.

- `from_state(state)` reconstructs authoring-time `EntitySpec` for positioned entities; it will set your component field if present.

- Nested entities (inventory/effects) are handled via `inventory_list`/`status_list`. If your new effect is collectible, ensure `collectible_system` logic recognizes it via `has_effect(state, eid)`.


## Testing and determinism

Unit tests

- Components: verify round-trip `Level -> State -> Level` preserves your component fields.

- Systems: small, controlled State to test system behavior, including edge cases (OOB, blocked, zero strength).

- Step lifecycle: integration test to ensure ordering produces expected outcomes.

Determinism

- Any randomness within new systems or `MoveFn`s should be seeded by `(state.seed, state.turn)`, e.g.:

```python
import random

def rng_for_turn(state: State) -> random.Random:
    base_seed = hash((state.seed if state.seed is not None else 0, state.turn))
    return random.Random(base_seed)
```

Coverage

- Add tests to ensure expired effects are GC’d, bonuses apply once, etc.

- Assert that performance-sensitive loops don’t scale badly (e.g., O(N^2) scans).


## Performance and maintenance tips

- Keep systems focused and cheap: read only required maps, write only what you change.

- Reuse helper utilities (`is_in_bounds`, `is_blocked_at`, `entities_with_components_at`).

- Respect existing blocking rules (movement ignores `Collidable`; `Blocking` blocks).

- Think about where your system sits in the lifecycle for best UX and correctness.

- For rendering:

    - Use cache-friendly parameters (size, group, overlay inputs).

    - Avoid recomputing recolors every frame unless necessary.

- Documentation:

    - Add docstrings following Google style so mkdocstrings renders nice API docs.

    - Update guides referencing your new features.

- Versioning:

    - If you change `step()` ordering or semantics, note it in the Changelog and bump a minor/major version as appropriate.


## Additional example: `PoisonCloud` (damage over time)

Define the component:

```python
# grid_universe/components/properties/poison_cloud.py
from dataclasses import dataclass

@dataclass(frozen=True)
class PoisonCloud:
    amount: int = 1  # damage per substep
```

Add to State, map in `EntitySpec`, export in `__init__`. Then implement a system:

```python
# grid_universe/systems/poison.py
from dataclasses import replace
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.components import Health, Dead
from grid_universe.utils.ecs import entities_with_components_at

def poison_system(state: State, agent_id: EntityID) -> State:
    pos = state.position.get(agent_id)
    if pos is None:
        return state
    cloud_ids = entities_with_components_at(state, pos, state.poison_cloud)  # requires State.poison_cloud
    if not cloud_ids or agent_id not in state.health:
        return state
    hp = state.health[agent_id]
    dmg = sum(state.poison_cloud[cid].amount for cid in cloud_ids)
    new_hp = max(0, hp.health - dmg)
    state = replace(state, health=state.health.set(agent_id, Health(health=new_hp, max_health=hp.max_health)))
    if new_hp == 0:
        state = replace(state, dead=state.dead.set(agent_id, Dead()))
    return state
```

Hook into `_after_substep` so the damage applies right after movement/portal. Adjust order with `damage_system` if you want stacking or precedence.


## Additional example: Renderer grouping for your component

If `PoisonCloud` instances should be tinted by intensity:

```python
def poison_group_rule(state: State, eid: EntityID):
    if eid in state.poison_cloud:
        amt = state.poison_cloud[eid].amount
        return f"poison:{amt}"
    return None
```

Append to `DEFAULT_GROUP_RULES` (in your local render wrapper) so clouds of different strength get distinct hues while preserving texture tone.