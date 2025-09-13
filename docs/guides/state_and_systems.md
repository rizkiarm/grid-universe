# State and Systems

This page explains the immutable runtime `State`, every system that transforms it, and the precise `step()` lifecycle that orchestrates them. It includes data model details, ordering rationales, and practical examples.

Contents

- The State data model
- Immutability and updates
- System-by-system reference
- The step() lifecycle (full order)
- Submoves: speed effects and per-substep systems
- Determinism and randomness
- Practical examples
- Troubleshooting and gotchas


## The State data model

The runtime `State` is an immutable dataclass that holds:

- Level configuration

    - `width`, `height`: Grid dimensions.
    - `move_fn`: Movement function (e.g., default, wrap, slippery, windy, gravity).
    - `objective_fn`: Win condition function.

- Entity registry

    - `entity`: `PMap[EntityID, Entity]`.
    - `EntityID` is an int; every placeable or nested (e.g., inventory/effect) item is an entity.

- Components (pyrsistent PMaps keyed by `EntityID`)

    - Effects

        - `immunity`: `PMap[EntityID, Immunity]`
        - `phasing`: `PMap[EntityID, Phasing]`
        - `speed`: `PMap[EntityID, Speed]`
        - `time_limit`: `PMap[EntityID, TimeLimit]`
        - `usage_limit`: `PMap[EntityID, UsageLimit]`

    - Properties

        - `agent`
        - `appearance`
        - `blocking`
        - `collectible`
        - `collidable`
        - `cost`
        - `damage`
        - `dead`
        - `exit`
        - `health`
        - `inventory`
        - `key`
        - `lethal_damage`
        - `locked`
        - `moving`
        - `pathfinding`
        - `portal`
        - `position`
        - `pushable`
        - `required`
        - `rewardable`
        - `status`

    - Extra

        - `prev_position`: Snapshot of positions at the start of the step.
        - `trail`: `Position → set[EntityID]` for entities that traversed a tile this turn.

- Meta and RNG

    - `turn`: int (increments after each step).
    - `score`: int.
    - `win`, `lose`: booleans.
    - `message`: optional text.
    - `seed`: `Optional[int]` used by deterministic systems/rendering.

Tip

- Only non-empty maps are shown in `State.description`, which is a convenient, compact debug view.


## Immutability and updates

- `State` is frozen (`@dataclass(frozen=True)`); systems produce a brand-new `State` using `dataclasses.replace`.

- Component maps are pyrsistent PMaps; updates use `.set(key, value)` and `.remove(key)`.

- Benefits:

    - Predictable, testable transformations.

    - Easier debugging and time-travel.

    - Avoid accidental in-place mutations across systems.


## System-by-system reference

This section lists each system with its purpose, inputs, outputs, and key details.

- `position_system(state) -> state`

    - Purpose: Snapshot current positions into `prev_position` for use by other systems (trail, portals, cross-damage).

    - Input: `state.position`.

    - Output: `state.prev_position` updated to the positions at the start of the turn.

    - Notes: Should run before any movement happens this turn.

- `moving_system(state) -> state`

    - Purpose: Move autonomous movers according to their `Moving` component (axis, direction, speed, bounce).

    - Input: `state.moving`, `state.position`.

    - Output: Updated position (and possibly `moving.direction` if a bounce happens).

    - Blocking rules: Considers in-bounds and `is_blocked_at`; if blocked and `bounce=True`, reverse direction once.

    - Speed: Applies discrete micro-steps up to `Moving.speed`.

- `pathfinding_system(state) -> state`

    - Purpose: Move entities that have `Pathfinding` toward their target per turn.

    - Modes:

        - `STRAIGHT_LINE`: Greedy Manhattan step.

        - `PATH`: A* pathfinding (uses blocking tiles as obstacles).

    - Input: `state.pathfinding`, `state.position`, `state.blocking`.

    - Output: Updated position of pathfinders.

    - Rules:

        - Checks bounds and blocking (ignores `collidable` for movement viability).

        - If the pathfinding target has active `Phasing`, a usage tick can be consumed and pursue may be skipped for this step (per code).

        - Moves at most one step per turn.

- `status_tick_system(state) -> state`

    - Purpose: Decrement `TimeLimit` for all effects in `Status` sets across all entities.

    - Input: `state.status`, `state.time_limit`.

    - Output: Updated `time_limit` for effect IDs present in `Status.effect_ids`.

- `trail_system(state) -> state`

    - Purpose: Record intermediate tiles traversed between `prev_position` and `position` (Manhattan path).

    - Input: `state.position`, `state.prev_position`.

    - Output: `state.trail` augmented with traversed tiles for entities that moved this turn.

    - Used by: `portal_system` (to detect entrants), `damage_system` (to detect overlaps and cross paths).

- `push_system(state, eid, next_pos) -> state`

    - Purpose: When an agent attempts to step into a cell with a `Pushable`, compute and attempt the push.

    - Input: current agent position, `next_pos`.

    - Output: If push is valid (destination in-bounds and not blocked), moves both agent and pushable; otherwise no change.

    - Rules:

        - Computes `push_to` via `utils.grid.compute_destination(current_pos, next_pos)`, including wrap-around if `move_fn` is `wrap_around_move_fn`.

        - Considers blocking/pushable/collidable for the destination.

- `movement_system(state, eid, next_pos) -> state`

    - Purpose: Apply a single-cell move for the agent.

    - Input: `next_pos` from `move_fn` or push flow.

    - Output: state with updated agent position if move is valid.

    - Rules:

        - If `Phasing` is active for the agent and valid, consumes usage (if applicable) and ignores `Blocking`.

        - Otherwise, requires in-bounds and not `is_blocked_at(..., check_collidable=False)`.

        - `Collidable` does not block movement here; `Blocking` does.

- `portal_system(state) -> state`

    - Purpose: Teleport collidable entities that enter a portal tile to the paired portal’s position.

    - Input: `state.portal`, `state.position`, `state.prev_position`, `state.trail`.

    - Output: Updated positions of entities that just entered a portal this turn.

    - Rules:

        - Detects entrants using “augmented trail” and checks `prev_position != position` to avoid re-teleporting.

        - Requires both portal ends have valid `Position`.

- `damage_system(state) -> state`

    - Purpose: Apply damage and lethal checks based on co-location or crossing paths with damagers.

    - Input: `state.position`, `state.prev_position`, `state.trail`, `state.damage`, `state.lethal_damage`, `state.health`.

    - Output: Updated `health`/`dead`; `usage_limit` may be consumed when `Immunity`/`Phasing` negate damage.

    - Rules:

        - `damager_ids` include both `Damage` and `LethalDamage` entities in the same tile this turn (trail-aware).

        - Cross-damage: If an entity moved out of a tile that a damager moved into from where the entity now is, count it as contact (head-on swap).

        - `Immunity` or `Phasing` can prevent damage, consuming usage/time.

- `tile_reward_system(state, agent_id) -> state`

    - Purpose: Add score for `Rewardable` entities on the agent’s tile that are not collectible.

    - Input: `state.rewardable`, `state.collectible`, agent position.

    - Output: Updated score.

- `tile_cost_system(state, agent_id) -> state`

    - Purpose: Subtract score for `Cost` entities on the agent’s tile (post-action, once per action).

    - Input: `state.cost`.

    - Output: Updated score.

    - Note: Designed to avoid multiplying cost when `Speed` multiplies submoves.

- `collectible_system(state, agent_id) -> state`

    - Purpose: Pick up items/effects on the agent’s tile.

    - Behavior:

        - If the entity is an effect (`Immunity`/`Phasing`/`Speed`) and limits allow, add to `Status.effect_ids`.

        - Else add to `Inventory.item_ids` (e.g., keys, coins).

        - If the entity has `Rewardable`, add to score.

        - Remove collected entities from world `position`/`collectible` maps.

    - Output: Updated status/inventory/score and removal from world.

- `unlock_system(state, agent_id) -> state`

    - Purpose: Unlock adjacent doors with `Locked(key_id)` if the agent holds a matching key.

    - Input: Adjacent tiles; `Inventory`; `Key` store.

    - Output: Removes `Locked` (and `Blocking`) from matching doors and consumes the key.

    - Note: Triggered by `Action.USE_KEY`; checks four-neighborhood around agent.

- `status_gc_system(state) -> state`

    - Purpose: Garbage-collect effect IDs from `Status` sets and remove orphan/expired effect entities.

    - Removes:

        - Effect IDs that no longer exist as a component in any effect store (orphaned).

        - Expired effects by time or usage (`<= 0`).

    - Output: Updated `status`/`entity`/`time_limit`/`usage_limit` (entity map pruned where needed).

- `win_system(state, agent_id) -> state`

    - Purpose: Set `win=True` if the configured `objective_fn` returns true.

    - Input: `state.objective_fn`, agent position, stores used by objective.

    - Output: `win` flag possibly set.

- `lose_system(state, agent_id) -> state`

    - Purpose: Set `lose=True` if the agent is `Dead`.

    - Input: `state.dead`.

    - Output: `lose` flag possibly set.

- `run_garbage_collector(state) -> state` (utils.gc)

    - Purpose: Remove entities not reachable from live structures (positions, inventories, status lists, etc.).

    - Output: All component PMaps filtered to only include alive entities.


## The step() lifecycle (full order)

The main reducer is `grid_universe.step.step`. Its control flow:

- Early checks

    - If there is no agent or agent is dead → `lose=True` or no-op.

    - If already terminal (`win` or `lose`) → no-op.

- Pre-action systems (world updates and bookkeeping)

    1) `position_system`

    2) `moving_system`

    3) `pathfinding_system`

    4) `status_tick_system`

    5) `trail_system`

- Action handling

    - If action is a MOVE (`UP/DOWN/LEFT/RIGHT`):

        - Call `_step_move`:

            - Determine `move_count` based on `Speed` effect (consumes usage if applicable).

            - For each submove (`1..move_count`):

                - For each target `Position` from `move_fn(state, agent, action)`:

                    - Try `push_system`.

                    - Else try `movement_system`.

                    - After either, run the per-substep suite:

                        - `portal_system`

                        - `damage_system`

                        - `tile_reward_system`

                    - If `win/lose/dead` or blocked, exit early.

    - If action is `USE_KEY` → `unlock_system`.

    - If action is `PICK_UP` → `collectible_system`.

    - If action is `WAIT` → no movement; skip straight to post-step.

- If action is not a MOVE, immediately run the per-substep suite once

    - `portal_system`

    - `damage_system`

    - `tile_reward_system`

- Post-step systems (always run if not returned earlier)

    1) `status_gc_system`

    2) `tile_cost_system`

    3) `win_system`

    4) `lose_system`

    5) `turn += 1`

    6) `run_garbage_collector`


## Submoves: speed effects and per-substep systems

- `Speed(multiplier)` in the agent’s `Status` can increase the number of submoves for one action.

- Usage limits for `Speed` are decremented when it actually increases movement.

- Per-substep suite (portals, damage, tile rewards) runs after each micro-move or push attempt, so immediate effects (like teleport or damage) can end the step early.

- `tile_cost_system` is deliberately post-step (once) to avoid penalizing more for higher speed.


## Determinism and randomness

- `State.seed` (if provided) is a base for deterministic behavior.

- Examples:

    - `windy_move_fn`: secondary step trigger derives from `hash((state.seed or 0, state.turn))` for reproducibility.

    - The renderer’s directory-based texture selection uses the seed to choose deterministically.

- Best practice:

    - Always set seeds for reproducible runs and tests.

    - Avoid non-deterministic iteration orders; sort when needed for stable behavior.


## Practical examples

Selecting a `move_fn` and `objective_fn` on a `Level`
```python
from grid_universe.levels.grid import Level
from grid_universe.moves import slippery_move_fn
from grid_universe.objectives import exit_objective_fn

level = Level(
    width=9, height=9,
    move_fn=slippery_move_fn,
    objective_fn=exit_objective_fn,
    seed=7,
)
```

Applying a single step with an action
```python
from grid_universe.actions import Action
from grid_universe.step import step

agent_id = next(iter(state.agent.keys()))
state = step(state, Action.RIGHT, agent_id=agent_id)
```

Manually invoking a system (debugging)
```python
from grid_universe.systems.portal import portal_system

state = portal_system(state)  # apply only portal logic to current state
```

Inspect damage contacts for an entity (pattern)
```python
from grid_universe.systems.damage import get_damager_ids
from grid_universe.utils.trail import get_augmented_trail
from pyrsistent import pset
from grid_universe.components import Position

# Build augmented trail (who traversed each tile) for entities relevant to damage
aug = get_augmented_trail(state, pset(set(state.health) | set(state.damage) | set(state.lethal_damage)))

pos = state.position.get(agent_id)
if pos is not None:
    print("Damagers at agent position:", get_damager_ids(state, aug, pos))
```


## Troubleshooting and gotchas

- My agent appears to move “through” enemies but still takes damage.

    - `movement_system` ignores `Collidable` for blocking (it only blocks on `Blocking`), but `damage_system` still applies contact-based damage when positions overlap or cross. Use `Immunity` to negate, or avoid the overlap.

- Speed seems to make me pay multiple movement costs.

    - By design, `tile_cost_system` is applied once after the action (not per submove). If you observe otherwise, check if you’re adding custom costs elsewhere.

- Portals feel inconsistent.

    - Entrants are detected via `trail` and `prev_position`; ensure `position_system` ran before moving, and that both portal ends exist with `Position`. Also verify the entity is `Collidable`.

- Effects don’t expire.

    - `status_tick_system` decrements `TimeLimit` each turn; `status_gc_system` removes effects when `time/usage <= 0`. Confirm the effect entity is actually in the holder’s `Status.effect_ids`, and that limits were set on that effect entity (not on the holder).

- Pathfinding enemy won’t move.

    - Confirm blocking rules: if all neighbors are blocked, it won’t step. For `PATH` mode, ensure there is a valid path; for `STRAIGHT_LINE`, it greedily moves closer only if the next tile isn’t blocking.

Tip

- Use `State.description` to quickly see which component stores are non-empty during debugging.