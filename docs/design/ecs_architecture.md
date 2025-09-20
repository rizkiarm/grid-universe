# ECS Architecture

This page explains how Grid Universe implements the Entity–Component–System (ECS) pattern, why the `State` is immutable, how systems transform `State`, and how authoring-time data (`Level`/`EntitySpec`) becomes runtime entities. It also covers determinism, performance, debugging, and invariants.

Contents

- ECS overview and rationale
- Entities and IDs
- Components and stores
- Systems: pure transforms and ordering
- Authoring-time vs runtime
- Data flow and lifecycle
- Immutability benefits and update patterns
- Determinism and randomness
- Performance considerations
- Debugging techniques
- Invariants and validation
- Worked example: one `step()` under the hood
- FAQs


## ECS overview and rationale

- ECS separates data (components) from behavior (systems), enabling:

    - Clear, composable logic (systems each handle one aspect).

    - Efficient querying by component presence.

    - Flexible composition of entity “types” without inheritance.

- In Grid Universe:

    - Entities are just integer IDs.

    - Components are lightweight dataclasses (properties/effects).

    - Systems are pure functions `State -> State` applied in a strict order during `step()`.

    - `State` is immutable (functional updates), improving predictability, debugging, and testing.


## Entities and IDs

- Entity

    - An entity is an opaque integer (`EntityID`).

    - No behavior or fields; identity only.

- Allocation

    - `Level → State` conversion auto-allocates `EntityID`s for every placed `EntitySpec`.

    - Nested items/effects (`inventory_list`/`status_list`) are also allocated `EntityID`s but do not get positions.

- Lifetime

    - Entities are removed by the garbage collector (`utils.gc.run_garbage_collector`) when unreachable (not in any live map: `position`, inventory sets, status sets, etc.).


## Components and stores

- Components

    - Small dataclasses: e.g., `Position`, `Blocking`, `Health`, `Damage`, `Locked`, `Key`, etc.

    - Effects are also components (`Immunity`, `Phasing`, `Speed`) with limits (`TimeLimit`, `UsageLimit`).

- Stores

    - Each component type has a `PMap[EntityID, Component]` in `State`.

    - Presence in a store means the entity has that component.

- Example stores

    - Properties:

        - `appearance`, `blocking`, `collectible`, `collidable`, `cost`, `damage`, `dead`, `exit`, `health`, `inventory`, `key`, `lethal_damage`, `locked`, `moving`, `pathfinding`, `portal`, `position`, `pushable`, `required`, `rewardable`, `status`

    - Effects:

        - `immunity`, `phasing`, `speed`, `time_limit`, `usage_limit`

    - Extra:

        - `prev_position` (Position snapshot), `trail` (`Position -> set[EntityID]`)

- Queries

    - Systems often compute “which entities” by intersecting store keys with location sets or by position filtering using helper functions.


## Systems: pure transforms and ordering

- Systems are pure functions: they read a `State` and return a new `State` with specific updates.

- Ordering is crucial and enforced in `step()`:

    - `position_system`: snapshot prev positions.

    - `moving_system`: autonomous movers (`Moving`).

    - `pathfinding_system`: chasers move one step.

    - `status_tick_system`: decrement `TimeLimit`.

    - Trail updates: recorded as entities move.

    - Per-submove (agent MOVE actions):

        - `push_system → movement_system → portal_system → damage_system → tile_reward_system`.

    - Post-step:

        - `status_gc_system → tile_cost_system → win_system → lose_system → turn++ → run_garbage_collector`.

- Rationale

    - position → moving/pathfinding ensures `prev_position` is reliable for the rest.

    - Per-submove effects allow immediate reactions (teleport/damage/score) as the agent moves.


## Authoring-time vs runtime

- Authoring-time

    - `Level`: a `grid[y][x]` of `EntitySpec`, which are mutable “bags” of optional components, plus authoring-only lists (`inventory_list`/`status_list`) and refs (`pathfind_target_ref`/`portal_pair_ref`).

- Runtime

    - `State`: immutable snapshot with entities, positions, and component stores.

- Conversion

    - `to_state(level)`:

        - Allocates `EntityID`s for placed `EntitySpec` and sets `Position`.

        - Copies present components into `State` stores.

        - Materializes `inventory_list`/`status_list` into separate entities referenced from `Inventory`/`Status`.

        - Resolves authoring refs: `Pathfinding.target` and `Portal.pair_entity` are wired to actual `EntityID`s.

    - `from_state(state)`:

        - Reconstructs a `Level` from positioned entities, restoring authoring lists and refs where both ends are positioned.


## Data flow and lifecycle

- At a high level:

    - Authoring: build `Level` → `to_state` → run systems via `step(actions)` → observe/render → (optionally) `from_state` for editors/inspection.

- During each step:

    - Snapshot `prev_position` → move autonomous/pathfinding → tick times → build `trail` → apply action, interleaving push/move with portals, damage, reward → collect costs, check terminal conditions → increment `turn` → GC unreachable entities.


## Immutability benefits and update patterns

- Immutability

    - `State` is `@dataclass(frozen=True)`. Updates use `dataclasses.replace` along with `PMap.set/remove`.

    - Prevents accidental mutation and makes transformations explicit.

- Update patterns

    - For multiple edits to the same store, reuse local variables and replace `State` at the end for performance.

    - For chain updates across several stores, construct new maps and pass into `replace` once.


## Determinism and randomness

- Seed

    - `State.seed` (from `Level` or generator) stores a base seed.

- Deterministic RNG

    - Movement randomness (e.g., `windy_move_fn`) derives from a hash of `(state.seed, state.turn)`. Texture directory variant selection uses a deterministic choice seeded from `state.seed`.

- Best practice

    - Always provide a seed for reproducible experiments.

    - If adding randomness in new systems, derive from `(seed, turn)` or a similar stable context.


## Performance considerations

- Stores are PMaps (immutable), which are efficient for persistent updates but still benefit from batching changes.

- Systems should:

    - Iterate over relevant keys only (e.g., `state.moving`, not all entities).

    - Use helper lookups (`entities_with_components_at`) sparingly in hot loops.

- Rendering:

    - Reuse the same `TextureRenderer` across frames.

    - Keep stable resolution and avoid frequent recolor/cache-key changes unless needed.


## Debugging techniques

- `State.description`

    - A compact `PMap` of non-empty fields; quickly inspect what’s present.

- Step-by-step replay

    - Apply `step()` with a fixed sequence of actions; dump `State.description` or key fields every turn.

- Targeted system invocation

    - Call a specific system (e.g., `portal_system(state)`) to isolate effects.

- Use the `TextureRenderer`

    - Render frames to visually debug movement, portals, damage overlaps, and grouping recolors.


## Invariants and validation

- Spatial integrity

    - Each positioned entity’s `Position` is within bounds.

    - Portals’ `pair_entity` should refer to another entity that has `Position`.

- Component consistency

    - Dead agents imply lose condition (`lose_system` sets `lose=True`).

    - `Required` items should not remain collectible if considered “collected” by objectives.

- Limits and status

    - `TimeLimit` and `UsageLimit` must tick/consume and eventually GC expired effects.

- Blocking

    - `movement_system` should never move agent into a `Blocking` tile unless `Phasing` is active (and usage limited if necessary).


## Worked example: one `step()` under the hood

We’ll walk through one `Action.RIGHT` with `default_move_fn` and a `Speed(multiplier=2)` effect active.

- Pre-action

    - `position_system` snapshots prev positions of all entities.

    - `moving_system` advances any `Moving` entities (e.g., oscillating boxes) up to their speed.

    - `pathfinding_system` moves chasers one tile toward their targets (if path exists).

    - `status_tick_system` decrements `TimeLimit` for all `Status` effect IDs.

    - Trail is recorded incrementally as movers/pathfinders advance.

- Action (RIGHT)

    - `Speed` effect multiplies submoves (`move_count = 2`). For `i ∈ {1,2}`:

        - `default_move_fn` returns `[pos + (1,0)]`.

        - `push_system` tries to push a `Pushable` at the target; if success, both move.

        - Otherwise `movement_system` attempts agent move; if blocked (no `Phasing`), stay.

        - After the move (or failed attempt), run:

            - Record trail; then `portal_system`: if the agent just entered a portal tile, teleport.

            - `damage_system`: apply damage/lethal based on co-location or cross paths; `Immunity`/`Phasing` can cancel with usage.

            - `tile_reward_system`: add reward for non-collectible `Rewardable` at current tile.

            - `position_system` and terminal checks (`win_system`/`lose_system`).

        - If blocked or terminal (`win/lose/dead`), break early.

- Post-action

    - `status_gc_system` removes expired/orphaned effects and prunes their entity IDs.

    - `tile_cost_system` subtracts movement cost (once per action, not per submove).

    - `win_system` checks objective; `lose_system` checks dead.

    - `turn` increments.

    - `run_garbage_collector` prunes entities unreachable from live structures.

At the end, you get the new `State` with updated position, score, effects usage/time, and any terminal flags set.


## FAQs

- Why is `Collidable` not used for blocking movement?

    - `movement_system` only blocks on `Blocking` (unless `Phasing`). `Collidable` is for collision-based interactions (damage/portals/trail), mirroring many gridworld conventions.

- How do I ensure my new system doesn’t break determinism?

    - Use seeded RNG derived from `(state.seed, state.turn)`. Avoid relying on dict iteration order for logic.

- Can I add a component that changes rendering without affecting systems?

    - Yes. Add a component, map it in `State` and `EntitySpec`, and extend the renderer’s texture map or grouping rules accordingly. Systems can ignore it.

- What happens if I forget to wire a new component in `EntitySpec` mapping?

    - `to_state` will not copy it into `State`; your system won’t see it. Also, `from_state` won’t reconstruct it. Always update `COMPONENT_TO_FIELD` and `State`.