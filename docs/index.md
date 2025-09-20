# Grid Universe

A modular, extensible, entity–component–system (ECS) gridworld for research, teaching, and prototyping. Author levels in a simple, mutable API; convert to an immutable State; run deterministic systems for movement, damage, portals, pathfinding, effects, and more; render with textures; and integrate with Gymnasium.

Contents

- Why Grid Universe
- Key features
- Concepts at a glance
- Architecture (high level)
- What’s in the box
- Quick start (2 minutes)
- Live rendering snapshot
- Ecosystem and integrations
- Contributing
- FAQ


## Why Grid Universe

- Clear separation of concerns with ECS: authoring vs runtime, data vs behavior.

- Deterministic simulations driven by seeds for reproducible experiments.

- Batteries-included systems: pushing, moving, pathfinding, portals, damage, status/effects, tile rewards/costs, terminal checks, GC.

- Practical tooling: texture renderer with recoloring groups, Gymnasium environment, procedural maze example, and convenient level factories.


## Key features

- Immutable runtime State with fast functional updates (pyrsistent PMaps).

- Systems pipeline with precise ordering and per-substep effects.

- Authoring-time Level API (mutable) and bidirectional conversion (to/from State).

- Movement options: default, wrap, mirror, slippery, windy, gravity; extend via custom `MoveFn`.

- Objective options: default, exit, collect-required, unlock-all, push-all-to-exit; extend via custom `ObjectiveFn`.

- Texture rendering with priority/layering, corner icons, grouping/recoloring, and animation overlays for movers.

- Gymnasium wrapper returning image observations and structured info.

- Procedural generator for mazes with controllable density and content placement.


## Concepts at a glance

- Authoring time

    - Level: `grid[y][x]` of `EntitySpec` (no positions/IDs). Place with `Level.add((x, y), spec)`.

    - `EntitySpec`: bag of component dataclasses plus authoring-only lists (`inventory_list`/`status_list`) and wiring refs (`pathfind_target_ref`, `portal_pair_ref`).

- Runtime

    - `State`: immutable snapshot with `EntityID`s, `Position` components, and per-type stores (Agent, Blocking, Portal, Health, etc.).

    - Systems: pure functions `State -> State` applied in a fixed order in `step()`.

- Determinism

    - Movement-related stochastic behaviors generally derive per‑turn randomness from `(state.seed, state.turn)`. The renderer’s directory‑variant selection uses a deterministic choice based on `state.seed`. Set seeds for reproducible runs.


## Architecture (high level)

- ECS split:

    - Entities: opaque integer IDs.

    - Components: small dataclasses, stored in PMaps keyed by `EntityID`.

    - Systems: pure transforms; each system handles one concern.

- Step lifecycle:

    - Pre: position → moving → pathfinding → status tick.

    - Per-submove (on MOVE actions, and once for non‑move actions): record trail → portal → damage → tile reward → position snapshot → win/lose.

    - Post: status GC → tile cost → turn++ → garbage collector.

- Conversion:

    - Level ↔ State via `levels.convert` (copies components, resolves wiring, materializes nested lists into `Inventory`/`Status` sets).


## What’s in the box

- Components

    - Properties (Agent, Appearance, Blocking, Collectible, Collidable, Cost, Damage, Dead, Exit, Health, Inventory, Key, LethalDamage, Locked, Moving, Pathfinding, Portal, Position, Pushable, Required, Rewardable, Status)

    - Effects (Immunity, Phasing, Speed) and limits (TimeLimit, UsageLimit)

- Systems

    - movement/push/moving/pathfinding/portal/damage/tile rewards & costs/status GC/terminal, plus position & trail bookkeeping

- Utilities

    - Grid helpers (bounds, blocking, destinations), ECS queries, status/inventory helpers, GC, image ops

- Rendering

    - `TextureRenderer` with default texture maps, recoloring groups for keys/doors and portal pairs, direction overlays for movers

- Gym

    - `GridUniverseEnv` with image observations, action mapping, reward = delta score, and rendering modes

- Examples

    - Maze generator with walls/floors, agent/exit, keys/doors, portals, enemies, hazards, and powerups
    - Authored gameplay progression suite (L0–L13) introducing mechanics incrementally (coins, required cores, key–door, hazard, portal, pushable box, enemy patrol, power‑ups, capstone puzzle)
    - Cipher objective levels injecting ciphertext objective via `state.message`

See full usage patterns and seed customization on the [Level Examples page](guides/level_examples.md).


## Quick start (2 minutes)

Install and run a minimal level.
```
# Install (editable)
pip install -e .

# (Optional) docs, dev extras
pip install -e ".[doc]" ".[dev]"
```

```python
# Your first level: author, step, render
from grid_universe.levels.grid import Level
from grid_universe.levels.factories import create_floor, create_agent, create_coin, create_exit
from grid_universe.levels.convert import to_state
from grid_universe.moves import default_move_fn
from grid_universe.objectives import default_objective_fn
from grid_universe.actions import Action
from grid_universe.step import step
from grid_universe.renderer.texture import TextureRenderer

level = Level(5, 5, move_fn=default_move_fn, objective_fn=default_objective_fn, seed=123)
for y in range(level.height):
    for x in range(level.width):
        level.add((x, y), create_floor())
level.add((1, 1), create_agent(health=5))
level.add((2, 1), create_coin(reward=10))
level.add((3, 3), create_exit())

state = to_state(level)
agent_id = next(iter(state.agent.keys()))

for a in [Action.RIGHT, Action.PICK_UP, Action.DOWN, Action.DOWN]:
    state = step(state, a, agent_id)
    if state.win or state.lose:
        break

TextureRenderer(resolution=480).render(state).save("quickstart.png")
print("Saved quickstart.png")
```

## Live rendering snapshot

- The texture renderer composes per cell:

    - One background tile, a main object, up to 4 corner icons, and any remaining overlays.

- Group recoloring:

    - Keys/doors sharing `key_id`, and paired portals, are recolored with a shared hue while preserving texture tone.

- Movers:

    - Direction triangles indicate moving direction and speed.


## Ecosystem and integrations

- Gymnasium: RL-friendly environment API with image-based observations.

- Docs: MkDocs Material + mkdocstrings (API pages from docstrings).

- CI: GitHub Actions workflow for building and publishing docs to Pages.

- Extensibility:

    - Add components, systems, movement/objective functions, factories, rendering rules, and grouping heuristics.


## Contributing

- Development

    - Install dev extras: `pip install -e ".[dev]"`

    - Run tests: `pytest`

    - Lint/format/type-check: `ruff`, `mypy`

- Docs

    - Serve: `mkdocs serve`

    - Build: `mkdocs build`

- Pull requests

    - Update or add docs for new features.

    - Include tests for systems and conversions.

    - Follow project coding style and type hints (strict mypy config).


## FAQ

- Is the State mutable?

    - No. State is an immutable dataclass; systems return a new State using functional updates.

- Do I need to place a background tile in every cell?

    - Not strictly, but it improves readability. The renderer can still draw foreground objects.

- How do I make runs reproducible?

    - Set a seed on your Level or generator; stochastic systems derive randomness from `(state.seed, state.turn)`.

- Can I add custom textures?

    - Yes. Provide a custom texture map and assets under your `asset_root`; map `(AppearanceName, properties)` → file or directory.

- Can I add a new system (e.g., conveyor belts)?

    - Yes. Implement a pure function `State -> State` and hook it into `step()` at the appropriate point (per-substep or post-step) to respect ordering.