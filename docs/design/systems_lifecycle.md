# Systems Lifecycle

This page provides a deep dive into the full lifecycle of systems executed per `step()`, why the order matters, what each stage consumes/produces, and how to safely add your own systems. It also covers per-substep vs per-step timing, the role of `prev_position` and `trail`, and practical diagnostics.

Contents

- Big picture: one step, many transforms
- Master order (annotated)
- Data dependencies and invariants
- Per-substep vs per-step systems
- Roles of `prev_position` and `trail`
- Adding your own systems (where to hook)
- Timing examples (timeline snippets)
- Design guidelines (idempotence, purity, determinism)
- Common patterns and pitfalls
- Diagnostics and testing


## Big picture: one step, many transforms

`step(state, action, agent_id)` is the single orchestrator that:

- Prepares the `State` for this turn (snapshot, autonomous movements, timers).

- Applies the agent’s action, possibly executing multiple submoves if `Speed` is active.

- Interleaves critical interactions (push, movement, portals, damage, tile rewards) after each submove to allow immediate consequences.

- Wraps up by cleaning up expired effects, charging tile costs, checking terminal conditions, advancing time, and garbage-collecting unreachable entities.

This fixed order keeps behavior predictable and deterministic, ensuring consistent outcomes across runs given the same seed and actions.


## Master order (annotated)

The exact execution order in `grid_universe.step.step` is:

- Early checks

    - No agent found → raise or no-op depending on context.

    - If agent in `dead` or `state` already terminal (`win`/`lose`) → return current `state`.

- Pre-action systems (world updates and bookkeeping)

    1) `position_system`

        - Snapshot all current positions into `prev_position`.

        - This “freezes” last turn’s locations for downstream systems that need to know “where entities came from.”

    2) `moving_system`

        - Move autonomous entities that have `Moving` (axis, direction, speed).

        - Handles bouncing or stopping on blockage, up to `Moving.speed` micro-steps.

    3) `pathfinding_system`

        - Move entities with `Pathfinding` one step toward targets.

        - `PATH` uses A* on non-blocking tiles; `STRAIGHT_LINE` is greedy.

    4) `status_tick_system`

        - Decrement `TimeLimit` for all effects referenced by `Status` across all entities.

    5) Trail updates

        - Trail entries are recorded incrementally while movers advance and after each substep.

- Action handling

    - If action in `MOVE_ACTIONS`:

        - Determine `move_count` (Speed effect may multiply).

        - For each submove (`1..move_count`):

            - For each proposed `Position` by `move_fn` (some `MoveFn` can propose multiple positions per action):

                - `push_system`: try to push `Pushable` at the target; may move both pusher and pushable if destination is free.

                - `movement_system`: if push did not move, attempt to move agent one cell.

                - Per-substep suite (in this exact order):

                    - Record trail for the agent’s current position.

                    - `portal_system`: teleport collidable entrants to paired portals; uses `prev_position` and `trail` to detect entrants.

                    - `damage_system`: apply `Damage`/`LethalDamage` considering co-location and cross-path; `Immunity`/`Phasing` can negate.

                    - `tile_reward_system`: add score for non-collectible `Rewardable` tiles the agent is on.

                    - `position_system`: snapshot positions again for downstream checks.

                    - `win_system`, `lose_system`: evaluate terminal conditions after the substep.

                - If the move was blocked or `state` became terminal (`win`/`lose`/`dead`), break early.

    - Else if action == `USE_KEY`:

        - `unlock_system`: unlock adjacent doors (`Locked`) if the matching key is in the agent’s inventory.

        - Then run the per-substep suite once:

            - `trail record → portal_system → damage_system → tile_reward_system → position_system → win_system → lose_system`

    - Else if action == `PICK_UP`:

        - `collectible_system`: pick up items/effects on the agent’s tile; may add to `Inventory`/`Status` and grant `Rewardable`.

        - Then run the per-substep suite once:

            - `trail record → portal_system → damage_system → tile_reward_system → position_system → win_system → lose_system`

    - Else if action == `WAIT`:

        - No movement or world change; the per‑substep suite runs once (trail record, portal, damage, tile reward, position snapshot, win/lose).

- Post-step systems (exactly once per step)

    1) `status_gc_system`

        - Remove expired effects from `Status` and delete orphan/expired effect entities.

    2) `tile_cost_system`

        - Subtract `Cost` for the agent’s current tile (only once per action, not per submove).

    3) turn increment

        - `turn += 1`

    4) `run_garbage_collector`

        - Prune entities not reachable via any live maps (positions, inventory sets, status sets, etc.).


## Data dependencies and invariants

Many systems consume artifacts produced by earlier systems:

- `position_system` must run before anything else that compares “before vs after” positions.

- `moving_system` and `pathfinding_system` occur before the agent acts to “advance the world” around the agent first.

- Trail is updated during autonomous movement and after each substep; `portal` and `damage` consult `trail` (and `prev_position`) to detect entrants, swaps, and cross‑through collisions.

- `portal_system` uses both `trail` and `prev_position` to detect entrants and avoid re-teleport loops in the same turn.

- `damage_system` consults `trail` (for cross paths), and `prev_position` (for swap collisions).

- `tile_cost_system` runs post-step to avoid multi-charging with `Speed`.

Invariants you should preserve:

- Positions remain in-bounds.

- `movement_system` does not allow walking into `Blocking` unless `Phasing` is active (and then consumes it via usage limit, if present).

- GC removes entities only if they are not found in any live structure (including nested references).


## Per-substep vs per-step systems

Per-substep (executed after each micro‑move or attempted push, and once for non‑move actions):

- Record trail for the acting agent’s current tile

- `portal_system`

- `damage_system`

- `tile_reward_system`

- `position_system` (snapshot after substep)

- `win_system`, `lose_system`

Per-step (executed once, after action handling):

- `status_gc_system`

- `tile_cost_system`

- turn increment

- `run_garbage_collector`

Why this matters:

- Immediate effects (teleport, damage, immediate rewards) should react to each micro-move, enabling realistic motion–interaction coupling.

- Persistent bookkeeping (costs, GC, victory/defeat) should occur once to keep semantics and scoring fair and deterministic.


## Roles of `prev_position` and `trail`

- `prev_position`

    - Snapshot from the start of the step. Used to compare where an entity was vs where it is, which is vital for:

        - Detecting “entrants” into portals (avoid double teleporting stationary entities).

        - Detecting cross damage (two entities moving through each other’s tiles).

- `trail`

    - A map of `Position → set[EntityID]` collected during the step showing all tiles traversed between prev and current positions (Manhattan path, x then y).

    - Used by:

        - `portal_system` to confirm entries.

        - `damage_system` to handle both co-location and cross paths (swap/cross-through collisions).


## Adding your own systems (where to hook)

Where a new system should be placed depends on its semantics:

- If it depends on the agent’s micro-movement and should apply immediately (e.g., a bounce pad, poison tile tick):

    - Place it in the per-substep suite. For example, after `tile_reward_system` if you want rewards to apply before your effect.

- If it modifies the world generally each turn (autonomous changes, environmental decay):

    - Place it in pre-action updates (after `status_tick_system`). Trail is recorded incrementally as movers/pathfinders advance.

- If it’s a “once-per-action” effect (e.g., banking points, draining resources post-action):

    - Place it in the post-step list, possibly before or after `tile_cost_system`.

Typical extension placements:

- Per-substep (after movement):

    - `portal → damage → tile_reward → your_system` (e.g., bounce_pad, poison, conveyor belt).

- Pre-action:

    - After moving/pathfinding, before `trail` if your system moves entities that should contribute to the `trail`; otherwise after `trail` if you only inspect current locations.

- Post-step:

    - Before/after `tile_cost_system` depending on whether your cost interacts with tile costs.


## Timing examples (timeline snippets)

Consider a turn where:

- A moving box moves horizontally.

- A pathfinding enemy takes one step toward the agent.

- The agent has `Speed ×2` and takes `Action.RIGHT`.

- There’s a portal to the right, and a spike (damage) beyond it.

Timeline:

- Pre-action:

    - `position_system`: snapshot positions.

    - `moving_system`: box moves 1 step; may bounce.

    - `pathfinding_system`: enemy steps toward agent.

    - `status_tick_system`: decrement `TimeLimit`.

    - Trail is recorded as movers advance (no global trail pass).

- Action, submove 1:

    - `push_system`: agent tries to push if needed.

    - `movement_system`: agent moves right (if not blocked).

    - `portal_system`: if agent enters the portal tile, teleport.

    - `damage_system`: apply damage if agent now overlaps spikes or crossed a damager.

    - `tile_reward_system`: add rewards (e.g., floor bonuses).

    - `position_system` then `win_system / lose_system`.

- Action, submove 2 (`Speed`):

    - Same sequence as above; may exit early if agent died or won.

- Post-step:

    - `status_gc_system`: remove expired effects.

    - `tile_cost_system`: subtract cost (once).

    - `win_system / lose_system`: set flags.

    - `turn++` and `run_garbage_collector`.


## Design guidelines (idempotence, purity, determinism)

- Purity:

    - Systems should be pure: `State` in → `State` out (no side effects, no global mutation).

- Idempotence:

    - Within a single call, avoid making the same change twice if called repeatedly (e.g., resist additive side-effects if called on unchanged input).

- Determinism:

    - Any randomness should be derived from `(state.seed, state.turn)` and not from global RNG, ensuring reproducibility.

- Minimal scope:

    - Iterate only over relevant entities (e.g., keys of a particular component store).

- Avoid order races:

    - If two systems might conflict, verify the intended ordering constraints and document them (e.g., “must run before `tile_reward_system`”).


## Common patterns and pitfalls

Patterns:

- “Conditional single-shot” effects:

    - Place in the per-substep suite after movement, check a condition on the agent’s tile, adjust state accordingly.

- “Global tick” effects:

    - Place in pre-action updates, reading/writing only small parts of `State`.

Pitfalls:

- Double-counting:

    - Do not add costs/rewards both per-substep and per-step unless that is intended.

- Blocking confusion:

    - `movement_system` ignores `Collidable` but respects `Blocking`; `pathfinding_system` uses similar logic. Keep consistency across new systems.

- Trail confusion:

    - Remember that `trail` is Manhattan interpolation between prev and current; don’t assume diagonal adjacency is tracked unless split into axis steps.

- Portal loops:

    - Let `portal_system` use `prev_position` and entering detection to avoid instant back-and-forth loops.

- GC surprises:

    - If you hold references to entities only in local variables, GC will remove them. Keep needed references in `State` stores (`Inventory`/`Status`/etc.).


## Diagnostics and testing

- Instrumentation:

    - Log key fields per step: `turn`, agent position, `score`, `win/lose`, counts of specific components.

- Visual debug:

    - Save frames from `TextureRenderer` at multiple points (pre-action, after each submove, post-step) if you temporarily expose hooks, or simply render each `State` after step.

- Unit tests:

    - Write scenario-specific tests for your systems, isolating inputs and asserting outputs (e.g., a poison tile reduces HP by X per submove).

- Reproducibility:

    - Fix `seed` and action sequences to make tests deterministic.

- `State.description`:

    - Use it as a quick health check to assert non-empty stores you expect and zero where you don’t.


## Example: inserting a custom per-substep system

Suppose you’ve implemented `conveyor_belt_system` that nudges the agent along the belt direction if they stand on it after moving.

- Place `conveyor_belt_system` after movement and after portal/damage/reward (so that teleports and damage apply first), or move it just after movement if you want belts to act before portals/damage.

Insertion example:

```python
# step.py (conceptual snippet)
def _after_substep(state: State, action: Action, agent_id: EntityID) -> State:
    state = portal_system(state)
    state = damage_system(state)
    state = tile_reward_system(state, agent_id)
    state = conveyor_belt_system(state, agent_id)  # custom per-substep
    return state
```

Guideline:

- Always reason about relative ordering to existing effects to avoid surprises (e.g., getting shoved into a portal or damage tile before or after application).
