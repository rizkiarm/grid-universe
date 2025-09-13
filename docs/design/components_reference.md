# Components Reference

This page documents every component used in Grid Universe, what data it carries, how systems interpret it, how it appears at authoring time (EntitySpec) and runtime (State), and any rendering or conversion notes. Components are small dataclasses attached to entities and stored in per-type PMaps on State.

Contents

- Effects (entities referenced from Status.effect_ids)
- Properties (world/entity attributes)
- Authoring-time mapping (EntitySpec ↔ State)
- Rendering notes (Appearance and prioritization)
- Cross-component interactions


## Effects (entities referenced from Status.effect_ids)

Effect entities are standalone entities (often created as collectibles/powerups) that are linked from a holder via the Status component (Status.effect_ids). They may also have TimeLimit and/or UsageLimit that control their lifetime or uses.

- Immunity

    - Dataclass: Immunity()

    - Meaning: Prevents damage for one damage event when consumed. If limits exist, usage/time is decremented appropriately.

    - Used by: damage_system (consumes usage/time via use_status_effect_if_present)

    - Authoring: Add an effect entity with Immunity; make it collectible to be picked up.

- Phasing

    - Dataclass: Phasing()

    - Meaning:

        - In movement_system: ignore Blocking when moving (consumes usage if usage-limited).

        - In damage_system: can also negate damage similar to Immunity (consumes usage/time).

    - Used by: movement_system, damage_system

    - Authoring: As a collectible effect; optionally add limits.

- Speed

    - Dataclass: Speed(multiplier: int)

    - Meaning: Multiplies the number of submoves per action (e.g., multiplier=2 doubles micro-steps). Usage/time decremented when used.

    - Used by: step._step_move

    - Authoring: As a collectible effect; commonly combined with TimeLimit or UsageLimit.

- TimeLimit

    - Dataclass: TimeLimit(amount: int)

    - Meaning: Max remaining turns (ticks down each turn by status_tick_system).

    - Used by: status_tick_system (decrement), status_gc_system (expiry removal)

    - Authoring: Optional effect limit attached to an effect entity.

- UsageLimit

    - Dataclass: UsageLimit(amount: int)

    - Meaning: Remaining uses (decremented when an effect is actually used).

    - Used by: movement_system (Phasing), damage_system (Immunity/Phasing), step._step_move (Speed), status_gc_system (expiry removal)

    - Authoring: Optional effect limit attached to an effect entity.


## Properties (world/entity attributes)

Property components define the static or dynamic attributes of world tiles and entities (agent, items, doors, portals, hazards, etc.).

- Agent

    - Dataclass: Agent()

    - Meaning: Marks an entity as a controllable agent (only agents respond to step action).

    - Used by: step, movement_system, terminal systems.

- Appearance

    - Dataclass: Appearance(name: AppearanceName, priority: int = 0, icon: bool = False, background: bool = False)

    - Meaning: Controls rendering selection and layering.

        - name: enumeration of visual category (e.g., HUMAN, WALL, FLOOR, COIN, MONSTER, etc.).

        - priority: ordering (lower number is more foreground for non-background; background tiles use highest numeric).

        - icon: True to render as small corner icon (subicon).

        - background: True to be considered a background tile for the cell.

    - Used by: renderer.texture (choose background/main/icons, layering)

    - Authoring: Set on most objects; backgrounds often have higher priority (e.g., FLOOR=10, WALL=9).

- Blocking

    - Dataclass: Blocking()

    - Meaning: Occupies space; agents and pathfinding entities cannot enter unless Phasing is active.

    - Used by: movement_system, pathfinding_system, moving_system (via is_blocked_at)

    - Authoring: Present on walls, closed doors, boxes (often combined with Collidable).

- Collectible

    - Dataclass: Collectible()

    - Meaning: Can be picked up by the agent standing on the same tile.

    - Used by: collectible_system

    - Authoring: Set on items (keys, coins, cores) and effect entities (speed/immunity/phasing) when you want them to be pickable.

- Collidable

    - Dataclass: Collidable()

    - Meaning: Involved in collision-based interactions and trail/portal logic; not blocking by itself.

    - Used by: portal_system (which teleports collidable entrants), damage_system (co-location/cross damage sets)

    - Authoring: Typically set on the agent and entities that should participate in overlap interactions (e.g., boxes, hazards, enemies).

- Cost

    - Dataclass: Cost(amount: int)

    - Meaning: Tile imposes a post-action score penalty when the agent stands on it at the end of a step.

    - Used by: tile_cost_system

    - Authoring: Put on floor tiles or special cells to model movement cost; applied once per action (not per submove).

- Damage

    - Dataclass: Damage(amount: int)

    - Meaning: Inflicts damage when a Health-bearing entity is co-located or cross-path contact occurs.

    - Used by: damage_system

    - Authoring: Hazards and enemies; can be combined with LethalDamage.

- Dead

    - Dataclass: Dead()

    - Meaning: Marks entity as dead.

    - Used by: lose_system (if agent has Dead), health logic; GC may prune if unused.

    - Authoring: Usually not authored directly; set by systems (e.g., lethal or 0 HP).

- Exit

    - Dataclass: Exit()

    - Meaning: A goal tile used by exit_objective_fn (and default objective via composite).

    - Used by: objectives, win_system.

    - Authoring: Place on tiles to mark the goal.

- Health

    - Dataclass: Health(health: int, max_health: int)

    - Meaning: HP pool; damage reduces health. When 0, Dead is set and health stays at 0.

    - Used by: damage_system, lose_system.

    - Authoring: Agent and optionally enemies.

- Inventory

    - Dataclass: Inventory(item_ids: PSet[EntityID])

    - Meaning: Items carried by the entity; keys, coins, cores, etc.

    - Used by: unlock_system (keys), user logic, UI.

    - Authoring: The agent starts with an empty or pre-loaded inventory; nested authoring list inventory_list is converted into separate entities.

- Key

    - Dataclass: Key(key_id: str)

    - Meaning: Identifies a key by id to match doors.

    - Used by: unlock_system (matching Locked(key_id)) and renderer grouping (keys/doors of same id recolored together).

    - Authoring: Keys are Collectible.

- LethalDamage

    - Dataclass: LethalDamage()

    - Meaning: Any contact with this damager kills the target regardless of damage amount.

    - Used by: damage_system (lethal flag)

    - Authoring: Dangerous hazards/enemies.

- Locked

    - Dataclass: Locked(key_id: str = "")

    - Meaning: Door is locked; requires a matching key_id in the agent’s Inventory. If key_id is empty, treat as “generic lock” (implementation-dependent).

    - Used by: unlock_system (removes Locked and Blocking if a key is consumed)

    - Authoring: Doors; usually also Blocking.

- Moving

    - Dataclass: Moving(axis: MovingAxis, direction: int, bounce: bool = True, speed: int = 1, prev_position: Optional[Position] = None)

    - Meaning: Autonomous movement component.

        - axis: HORIZONTAL or VERTICAL.

        - direction: +1 or -1.

        - bounce: reverse direction on collision if True; else stop.

        - speed: micro-steps per turn.

    - Used by: moving_system (updates position, flips direction on block if bounce).

    - Authoring: Add to boxes/enemies for patrolling; the maze example sets random axes/directions/speeds.

- Pathfinding

    - Dataclass: Pathfinding(target: Optional[EntityID] = None, type: PathfindingType = PATH)

    - Meaning: Entity pursues a target each turn.

    - Used by: pathfinding_system

    - Modes:

        - STRAIGHT_LINE: greedy Manhattan step.

        - PATH: A* shortest path on non-blocking tiles.

    - Authoring: Set via authoring ref pathfind_target_ref to target another EntitySpec (resolved to eid in to_state).

- Portal

    - Dataclass: Portal(pair_entity: int)

    - Meaning: Teleport paired cell.

    - Used by: portal_system; detects collidable entrants and moves them to the pair’s Position.

    - Authoring: Pair using portal_pair_ref (create_portal(pair=...)) so to_state wires both ends.

- Position

    - Dataclass: Position(x: int, y: int)

    - Meaning: In-world location.

    - Used by: almost every system; prev_position mirrors last turn’s positions.

    - Authoring: Not present on EntitySpec (authoring); to_state sets Position when placing on Level.

- Pushable

    - Dataclass: Pushable()

    - Meaning: Can be pushed by an agent stepping into it. Destination must be in-bounds and not blocked.

    - Used by: push_system (computes push_to using compute_destination and moves both agent and pushable)

    - Authoring: Boxes typically include Pushable (optional).

- Required

    - Dataclass: Required()

    - Meaning: Marks a collectible as “required” for the default objective.

    - Used by: collect_required_objective_fn and default_objective_fn.

    - Authoring: Often on “core” items.

- Rewardable

    - Dataclass: Rewardable(amount: int)

    - Meaning: Adds to score when collected (if also Collectible) or when standing on tile (non-collectible).

    - Used by: collectible_system (collection reward), tile_reward_system (on-tile reward).

    - Authoring: Use for coins, cores, or floor bonuses.

- Status

    - Dataclass: Status(effect_ids: PSet[EntityID])

    - Meaning: Holds references to effect entities (Immunity/Phasing/Speed, etc.).

    - Used by: movement_system (phasing), step._step_move (speed), damage_system (immunity/phasing), status_tick_system/status_gc_system.

    - Authoring: The agent often has an empty Status initially; authoring status_list adds effects at start.


## Authoring-time mapping (EntitySpec ↔ State)

- Authoring-time: EntitySpec holds optional fields for these components (None means absent), plus authoring-only lists:

    - inventory_list: nested EntitySpec items to create as separate entities and link in Inventory.item_ids.

    - status_list: nested EntitySpec effects to create as separate entities and link in Status.effect_ids.

    - pathfind_target_ref: reference to another EntitySpec; on to_state, becomes Pathfinding.target = eid.

    - portal_pair_ref: reference between two portal EntitySpec; on to_state, becomes reciprocal Portal(pair_entity=...).

- Conversion to State (to_state):

    - Copies component fields to the corresponding State PMaps.

    - If an entity is placed in the grid, a Position is assigned.

    - Nested items/effects are allocated new eids without Position and added to the holder’s Inventory/Status.

    - Wiring references are resolved to EIDs.

- Conversion from State (from_state):

    - Reconstructs a Level of EntitySpec from positioned entities.

    - Rebuilds inventory_list/status_list from Inventory/Status sets.

    - Restores authoring wiring references where both ends are placed.


## Rendering notes (Appearance and prioritization)

- Appearance controls selection and layering:

    - One background per cell: appearance.background=True; pick the “furthest back” by descending priority and take the lowest item (e.g., FLOOR priority 10).

    - Main object: highest priority (smallest number) among non-backgrounds.

    - Corner icons: appearance.icon=True; up to 4 highest-priority icons are drawn as subicons.

    - Others: non-background, non-icon items drawn between background and main.

- Group-based recoloring:

    - Keys and doors sharing key_id are recolored via a shared hue.

    - Paired portals are recolored via a shared hue.

    - You can add grouping rules for your own components.

- Moving overlay:

    - Entities with Moving draw direction triangles (count = speed) to indicate motion direction, aiding readability.


## Cross-component interactions

- Movement and blocking

    - Blocking prevents entry unless Phasing is active and consumed.

    - Collidable does not block movement; it marks entities for collision-based systems (portals/damage/trail).

- Damage and immunity

    - Damage and/or LethalDamage apply to entities with Health.

    - Immunity/Phasing (if present in Status and valid by limits) may negate damage and consume usage/time.

- Unlocking

    - Keys in Inventory matched to Locked doors remove Locked and Blocking (opens passage) and consume the key.

- Collecting

    - Collectible + effect components → add effect entity to holder’s Status (if valid by limits).

    - Collectible + Rewardable → add to score upon pickup.

    - Collectible (non-effect) → add to Inventory (keys, coins, cores).

- Objectives

    - default_objective_fn = collect_required AND exit (uses Required and Exit components).

    - all_unlocked_objective_fn checks that Locked store is empty.

- Garbage collection

    - run_garbage_collector prunes any entity not referenced by a live structure (Position map, Inventory sets, Status sets, etc.), keeping State compact.


## Component quick reference (cheat sheet)

- Effects:

    - Immunity: negates one damage event.

    - Phasing: ignore Blocking on movement; can negate damage.

    - Speed(multiplier): multiplies submoves for an action.

    - TimeLimit(amount): ticks down each turn.

    - UsageLimit(amount): decrements on effect use.

- Tiles and items:

    - Appearance(name, priority, icon, background): rendering and layering.

       - AppearanceName includes: HUMAN, WALL, FLOOR, COIN, CORE, DOOR, KEY, PORTAL, MONSTER, SHIELD, GHOST, BOOTS, SPIKE, LAVA, EXIT, BOX, etc.

    - Blocking: impassable.

    - Collidable: participates in overlap/trail interactions.

    - Collectible: can be picked up.

    - Cost(amount): per-action tile cost.

    - Rewardable(amount): scoring on pickup or per-tile.

- Gameplay mechanics:

    - Damage(amount), LethalDamage: hazards/enemies.

    - Health(health, max_health), Dead: survivability.

    - Locked(key_id), Key(key_id): doors and keys.

    - Portal(pair_entity): teleport pairs.

    - Pathfinding(target, type): autonomous chase.

    - Moving(axis, direction, bounce, speed): patrols/oscillators.

    - Pushable: push mechanics for boxes.

- Agent and state:

    - Agent(): controllable entity.

    - Position(x, y): location.

    - Inventory(item_ids): carried items.

    - Status(effect_ids): active effects.


## Code snippets

Create a collectible speed effect with time and usage limits:

```python
from grid_universe.levels.factories import create_speed_effect

speed_boots = create_speed_effect(multiplier=2, time=10, usage=5)
# Place it on a tile: level.add((x, y), speed_boots)
```

Create a locked door/key pair:

```python
from grid_universe.levels.factories import create_key, create_door

level.add((2, 2), create_key("red"))
level.add((4, 2), create_door("red"))
```

Mark an enemy that deals lethal damage and chases the agent via A*:

```python
from grid_universe.levels.factories import create_monster, create_agent
from grid_universe.components.properties import PathfindingType

agent = create_agent()
enemy = create_monster(damage=1, lethal=True, pathfind_target=agent, path_type=PathfindingType.PATH)
level.add((1, 1), agent)
level.add((5, 5), enemy)
```

Add a patrolling box that bounces horizontally:

```python
from grid_universe.levels.factories import create_box
from grid_universe.components.properties import Moving, MovingAxis

box = create_box(pushable=False)
box.moving = Moving(axis=MovingAxis.HORIZONTAL, direction=1, speed=1, bounce=True)
level.add((3, 3), box)
```