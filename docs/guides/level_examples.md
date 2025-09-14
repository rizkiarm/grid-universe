# Level Examples

A consolidated overview of level and task-focused example modules. These return immutable `State` objects suitable for rendering, stepping, or Gym wrappers.

Contents

- Procedural maze generator
- Gameplay progression suite (L0–L13)
- Cipher objective micro-levels
- Seed customization patterns

## Procedural maze generator

Module: `grid_universe.examples.maze`

Features:
- Adjustable width/height, wall density, optional counts for keys, doors, portals, enemies, hazards, power‑ups
- Deterministic when `seed` is provided
- Adds agent + exit and optional gating mechanics

```python
from grid_universe.examples import maze
state = maze.generate(width=20, height=20, seed=123, n_keys=1, n_doors=1)
```

## Gameplay progression suite (L0–L13)

Module: `grid_universe.examples.gameplay_levels`

Mechanic ramp (movement → coins → required cores → key–door → hazard → portal → pushable → enemy patrol → power‑ups → capstone):

| Level | Focus | New Mechanic(s) |
|-------|-------|-----------------|
| L0 | Basic movement | Exit |
| L1 | Maze turns | Corridor layout |
| L2 | Optional coins | Cost-reducing tiles |
| L3 | Required core | Collect then exit |
| L4 | Two required cores | Backtracking |
| L5 | Key–Door | Gating |
| L6 | Hazard detour | Damage tile |
| L7 | Portal shortcut | Teleport pair |
| L8 | Pushable box | Pushing |
| L9 | Enemy patrol | Moving obstacle |
| L10 | Shield power-up | Immunity effect |
| L11 | Ghost power-up | Phasing through door |
| L12 | Boots power-up | Speed timing |
| L13 | Capstone | Integrated puzzle |

Seeding:
```python
from grid_universe.examples import gameplay_levels as gp
suite_default = gp.generate_task_suite()
suite_shifted = gp.generate_task_suite(base_seed=5000)
suite_custom  = gp.generate_task_suite(seed_list=[10*i for i in range(14)])
boots_state   = gp.build_level_power_boots(seed=9001)
```

## Cipher micro-levels (maze-based)

Module: `grid_universe.examples.cipher_objective_levels`

Reuse the procedural maze generator and then adapt with cipher/objective sampling.

```python
from grid_universe.examples.cipher_objective_levels import generate, to_cipher_level
from grid_universe.examples import maze

exit_state = generate(width=9, height=7, num_required_items=0, cipher_objective_pairs=[("ABC","exit")], seed=42)
collect_state = generate(width=11, height=9, num_required_items=2, cipher_objective_pairs=[("DATA","default")], seed=99)

base = maze.generate(width=9, height=7, seed=777, num_required_items=1)
adapted = to_cipher_level(base, [("SECRET","exit")], seed=777)
```

## Seed customization patterns

All examples set `state.seed`; derive per-turn RNG from `(state.seed, state.turn)` if needed:

```python
import random
from grid_universe.state import State

def rng_for_turn(state: State) -> random.Random:
    return random.Random(hash(((state.seed or 0), state.turn)))
```

Guidelines:
- Shift a base seed to create curricula: `generate_task_suite(base_seed=epoch*1000)`
- Log the exact seed list for reproducibility
- Keep structural layouts constant while varying cosmetic randomness via seeds

## Next steps
- See API reference for function signatures
- Combine authored + procedural levels for mixed datasets
- Clone a gameplay builder to design custom mechanics
