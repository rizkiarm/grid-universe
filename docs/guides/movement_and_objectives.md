# Movement and Objectives

This guide dives deeper into movement functions (MoveFn) and objective functions (ObjectiveFn): how they work, how to select and combine them, and how to write your own. It also covers speed effects, determinism, and common pitfalls.

Contents

- MoveFn basics
- Built-in movement functions
- Selecting and configuring movement
- Speed effects and submoves
- Writing a custom MoveFn
- ObjectiveFn basics
- Built-in objective functions
- Selecting and configuring objectives
- Writing a custom ObjectiveFn
- Determinism, testing, and pitfalls


## MoveFn basics

- A MoveFn is any callable with signature MoveFn(State, EntityID, Action) -> Sequence[Position].

- The function computes a list of target positions the agent will attempt to traverse in this action. The step() loop will:
  - Iterate over the sequence returned by the MoveFn.
  - For each proposed Position, try push_system first, then movement_system.
  - After each attempt, run per-substep systems (portal, damage, tile_reward).
  - Stop early if blocked or terminal.

- Important: Returning multiple positions implements “multi-tile motion” within one action (e.g., slippery slide). It does not guarantee reaching the last position—blocking or collisions can stop it early.


## Built-in movement functions

All functions interpret Action.UP/DOWN/LEFT/RIGHT as single-tile deltas. They differ in how many positions they propose and how they handle grid edges.

- default_move_fn

    - Behavior: One step in the action direction.

    - Returns: [next_pos].

    - Use when: You want classic grid movement.

- wrap_around_move_fn

    - Behavior: One step in the action direction, wrapping on edges.

    - Returns: [wrapped_pos] where x and y are modulo width/height.

    - Requirements: State must have width and height; else raises ValueError.

    - Use when: Toroidal grids (Pac-Man-like wrap).

- mirror_move_fn

    - Behavior: Mirrors horizontal directions. LEFT behaves as RIGHT and vice versa. UP and DOWN unchanged.

    - Returns: [mirrored_step_pos].

    - Use when: Puzzle variations or tricky controls.

- slippery_move_fn

    - Behavior: Slides in the action direction until blocked or out-of-bounds.

    - Returns: A sequence of all intermediate positions up to (but not including) the blocking/out-of-bounds tile; if the first step is blocked, returns [current_pos] so the step results in no movement.

    - Blocking rule: Checks the world for any Blocking entities at each candidate tile; stops before collision.

    - Use when: Ice/sliding puzzles. The step() loop will attempt each returned position in order; it may still stop earlier if another system intervenes.

- windy_move_fn

    - Behavior: Takes one step as usual. With 30% chance (deterministic per turn via seed/turn), adds a second “wind” step in a random cardinal direction if in-bounds.

    - Returns: [primary_step] or [primary_step, wind_step].

    - Determinism: Uses a Random seeded by hash((state.seed or 0, state.turn)).

    - Use when: Stochastic perturbations with reproducibility.

- gravity_move_fn

    - Behavior: Attempts the initial step; if valid, repeatedly “falls” down (dy=+1) until blocked or out-of-bounds.

    - Returns: [initial_step, fall1, fall2, ...]; if the initial step is blocked, returns [current_pos].

    - Use when: Platformer-like gravity after moving laterally or up.


## Selecting and configuring movement

You select a movement function at authoring time when you construct the Level.

```python
from grid_universe.levels.grid import Level
from grid_universe.moves import default_move_fn, slippery_move_fn, wrap_around_move_fn

# Classic movement
level = Level(9, 9, move_fn=default_move_fn, objective_fn=..., seed=123)

# Sliding puzzles
level = Level(9, 9, move_fn=slippery_move_fn, objective_fn=..., seed=123)

# Toroidal map
level = Level(9, 9, move_fn=wrap_around_move_fn, objective_fn=..., seed=123)
```

You can also pick by name using the registry:

```python
from grid_universe.moves import MOVE_FN_REGISTRY

move_fn = MOVE_FN_REGISTRY["slippery"]
level = Level(9, 9, move_fn=move_fn, objective_fn=..., seed=123)
```


## Speed effects and submoves

- Speed(multiplier) is an effect entity that can be added to the agent’s Status (e.g., by picking up a speed powerup).

- When present and valid (not expired by time or usage), step() multiplies the number of submoves (micro-steps) for this action by the multiplier.

- After each submove attempt, per-substep systems run (portal/damage/tile_reward), which can end the action early.

- tile_cost_system runs once per action (post-step), so fast movement does not pay multiple costs.

- If the Speed effect also has UsageLimit, it is consumed when actually used to multiply movement; TimeLimit is decremented by status_tick_system each turn regardless of use.


## Writing a custom MoveFn

You can define your own movement logic. The contract is simple: return a sequence of Positions you want the agent to attempt.

Example: “two-step dash” with obstacle check between steps.

```python
from typing import Sequence
from grid_universe.components import Position
from grid_universe.actions import Action
from grid_universe.state import State
from grid_universe.types import EntityID, MoveFn

def dash_two_steps(state: State, eid: EntityID, action: Action) -> Sequence[Position]:
    pos = state.position[eid]
    dx, dy = {
        Action.UP: (0, -1),
        Action.DOWN: (0, 1),
        Action.LEFT: (-1, 0),
        Action.RIGHT: (1, 0),
    }[action]
    # Propose 1-step, then 2-step in a straight line
    return [Position(pos.x + dx, pos.y + dy), Position(pos.x + 2*dx, pos.y + 2*dy)]
```

Considerations for custom MoveFns:

- Bounds and blocking are enforced later by systems; the MoveFn just proposes targets.

- If you want “no movement” on failure, you can return [current_pos] to make the intent explicit (as slippery and gravity do in a blocked-first-step case).

- If you need determinism across runs, derive any randomness from (state.seed, state.turn) similar to windy_move_fn.

- Interactions (push/portal/damage) are applied by systems after each proposed position—so it’s safe to return multiple steps and let systems stop early if needed.


## ObjectiveFn basics

- An ObjectiveFn is any callable with signature ObjectiveFn(State, EntityID) -> bool.

- win_system calls state.objective_fn(state, agent_id) after each step; if it returns True, state.win becomes True.

- Objectives usually inspect the agent’s position, inventory/status, or global conditions (e.g., all doors unlocked).


## Built-in objective functions

- default_objective_fn

    - Composite: collect_required_objective_fn AND exit_objective_fn.

    - Win when: All Required collectibles are obtained and the agent stands on an Exit.

- exit_objective_fn

    - Win when: Agent is on a cell containing an Exit entity.

- collect_required_objective_fn

    - Win when: No entity in state.required remains collectible (i.e., they’ve been picked up/removed from the world).

- all_unlocked_objective_fn

    - Win when: There are no Locked entities left in state.locked.

- all_pushable_at_exit_objective_fn

    - Win when: Every Pushable entity’s position overlaps a cell that also contains an Exit.


## Selecting and configuring objectives

Pick an objective when you construct the Level. You can also select by name from the registry.

```python
from grid_universe.levels.grid import Level
from grid_universe.objectives import default_objective_fn, OBJECTIVE_FN_REGISTRY

# Default composite objective (collect required + stand on exit)
level = Level(9, 9, move_fn=..., objective_fn=default_objective_fn, seed=42)

# Registry by name
objective_fn = OBJECTIVE_FN_REGISTRY["unlock"]  # all_unlocked_objective_fn
level = Level(9, 9, move_fn=..., objective_fn=objective_fn, seed=42)
```


## Writing a custom ObjectiveFn

Design your own win condition by examining the State. Keep it fast and pure (no side effects).

Example: “Reach score ≥ target AND stand on an exit.”

```python
from grid_universe.types import ObjectiveFn, EntityID
from grid_universe.state import State
from grid_universe.utils.ecs import entities_with_components_at

def score_and_exit_objective_fn_factory(target_score: int) -> ObjectiveFn:
    def _obj(state: State, agent_id: EntityID) -> bool:
        pos = state.position.get(agent_id)
        if pos is None:
            return False
        on_exit = len(entities_with_components_at(state, pos, state.exit)) > 0
        return on_exit and state.score >= target_score
    return _obj

# Usage:
# level = Level(..., objective_fn=score_and_exit_objective_fn_factory(50), seed=...)
```

Example: “Collect N coins” (counting inventory items of type coin).

```python
from grid_universe.types import ObjectiveFn, EntityID
from grid_universe.state import State

def collect_n_coins_objective_fn_factory(n: int) -> ObjectiveFn:
    def _obj(state: State, agent_id: EntityID) -> bool:
        inv = state.inventory.get(agent_id)
        if inv is None:
            return False
        # Treat collectible items without Required as coins
        count = 0
        for item_id in inv.item_ids:
            if item_id in state.collectible and item_id not in state.required:
                count += 1
        return count >= n
    return _obj
```


## Determinism, testing, and pitfalls

Determinism

- If your MoveFn or ObjectiveFn uses randomness, derive it from (state.seed, state.turn) to keep runs reproducible.

- Example pattern:

    ```python
    import random
    def rng_for_turn(state: State) -> random.Random:
        base_seed = hash((state.seed if state.seed is not None else 0, state.turn))
        return random.Random(base_seed)
    ```

Testing MoveFns

- Unit test MoveFns by constructing a small State with known positions and checking the returned sequence of Positions (do not execute systems there).

- For integrated tests, call step() with a fixed seed and verify positions/score/flags after actions.

Common pitfalls

- Returning an empty list from a MoveFn: step() won’t attempt any movement; if you intend “no movement,” prefer returning [current_pos] to make it explicit.

- Multi-step proposals and blocking: Systems stop the agent early if blocked, so proposing aggressive paths is fine—but be aware that damage, portals, or pushes will interleave.

- ObjectiveFn performance: Called after every step; make sure it traverses only the necessary parts of State. Precompute sets when possible (e.g., using sets of IDs in maps).

- Counting coins vs cores: In this project, Required items (cores) are a separate component; coins are typically Collectible without Required. Differentiate based on presence/absence of Required.

- Exit detection: Use entities_with_components_at(state, pos, state.exit) rather than scanning the whole grid.


## End-to-end examples

Classic puzzle: Collect all required cores and exit with sliding movement

```python
from grid_universe.levels.grid import Level
from grid_universe.levels.factories import create_floor, create_agent, create_core, create_exit
from grid_universe.levels.convert import to_state
from grid_universe.moves import slippery_move_fn
from grid_universe.objectives import default_objective_fn
from grid_universe.actions import Action
from grid_universe.step import step

# Level
lvl = Level(7, 5, move_fn=slippery_move_fn, objective_fn=default_objective_fn, seed=7)
for y in range(lvl.height):
    for x in range(lvl.width):
        lvl.add((x, y), create_floor())
lvl.add((1, 1), create_agent(health=5))
lvl.add((3, 1), create_core(reward=10, required=True))
lvl.add((5, 3), create_exit())

# Runtime
st = to_state(lvl)
aid = next(iter(st.agent.keys()))

# Play (example actions)
for a in [Action.RIGHT, Action.RIGHT, Action.DOWN, Action.DOWN, Action.LEFT]:
    st = step(st, a, aid)
    if st.win or st.lose:
        break

print("Score:", st.score, "Turn:", st.turn, "Win:", st.win)
```

Custom objective: Unlock all doors with wrap-around movement

```python
from grid_universe.levels.grid import Level
from grid_universe.levels.factories import create_floor, create_agent, create_key, create_door, create_exit
from grid_universe.levels.convert import to_state
from grid_universe.moves import wrap_around_move_fn
from grid_universe.objectives import all_unlocked_objective_fn
from grid_universe.actions import Action
from grid_universe.step import step

lvl = Level(6, 4, move_fn=wrap_around_move_fn, objective_fn=all_unlocked_objective_fn, seed=5)
for y in range(lvl.height):
    for x in range(lvl.width):
        lvl.add((x, y), create_floor())

lvl.add((0, 0), create_agent())
lvl.add((1, 0), create_key("red"))
lvl.add((2, 0), create_door("red"))
lvl.add((4, 0), create_exit())  # Exit is optional for this objective

st = to_state(lvl)
aid = next(iter(st.agent.keys()))
for a in [Action.RIGHT, Action.RIGHT, Action.USE_KEY]:
    st = step(st, a, aid)

print("All unlocked:", all(len(st.locked) == 0 for _ in [0]), "Win:", st.win)
```