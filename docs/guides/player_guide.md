# Player Guide

Welcome to Grid Universe! This page explains how to play, what your goals are, and how common mechanics behave in every level (portals, enemy damage, pushing, keys/doors, scoring, and more).

If a level adds special rules (like sliding ice or wrap-around edges), it will usually be mentioned in the level description. Otherwise, the rules below apply.


## Your goal

- Default objective: collect all required items (often called “cores”) and then stand on an Exit tile to win.
- Some levels use a different objective (e.g., unlock all doors). When this happens, the level will tell you. Either way, the game will mark Win as soon as the objective is met, and Lose if your agent dies.


## Controls

- Move: Arrow keys or directional inputs (UP, DOWN, LEFT, RIGHT)
- Pick up: collects items on your tile (coins, cores, keys)
- Use key: unlocks matching doors on your tile if you carry the key
- Wait: pass a turn without moving (useful to tick timers or let enemies move)

Note: Some frontends map these to buttons; the underlying actions are the same.


## Turn flow at a glance

Each turn is processed in a strict order so interactions feel predictable:

1. Effects tick first: time-based status effects (like speed or immunity) decrement timers before your action.
2. Enemies and movers may act: autonomous entities can move toward targets or follow paths.
3. Your action runs. For movement actions:
    - Pushing happens before walking. If you walk into a pushable box and the space behind it is free, you push the box and move into its old tile. If the push can’t happen, you try to walk normally.
    - If you can’t move (blocked by walls, closed doors, or other blockers), your movement for this sub-step ends.
    - After each small step, interactions are resolved immediately: portals teleport you, hazards/enemies can damage you, and standing on reward tiles grants points. If you die or win, the turn ends.
    - Speed effects can grant multiple small steps in one action. Interactions run after each step.
4. End of turn: tile costs (like floor upkeep) are applied once per action, then the turn counter increases.

Key consequences:

- Interactions chain. Example: step onto a portal, get teleported, then take damage at the destination—all in the same turn.
- Costs only once per action. Even with speed boosts, you won’t pay tile costs multiple times in the same turn.


## Movement and blocking

- You generally move one tile per action.
- Blocked tiles: walls, locked doors, and some objects prevent movement. Boxes that can be pushed still block normal walking if they can’t be pushed.
- Phasing effect: lets you walk through blocking tiles while the effect lasts (it consumes uses/time when it helps you pass through blockers).
- Level variants you might encounter:
    - Sliding/ice: you keep moving in the same direction until something stops you.
    - Wrap-around edges: stepping off the edge puts you on the opposite side.
    - Gravity/windy: some levels add a fall after moving, or a chance to be blown by wind.


## Pushing boxes (and other pushables)

- Walk into a pushable to try to shove it one tile forward in your movement direction.
- A push only succeeds if the destination space for the box is free of blockers.
- If multiple pushables are stacked on your target tile, they move together when possible.
- You move into the box’s former tile as part of the push.
- You cannot push into walls, locked doors, other blockers, or out-of-bounds.


## Portals

- Stepping onto a portal teleports you to its paired portal immediately (within the same turn) after your step.
- If the destination portal tile is blocked, the teleport won’t happen and you’ll remain where you are.
- Because interactions chain, you can take damage or trigger rewards/costs at the destination in the same turn you teleport.


## Enemies and hazards (damage rules)

You have health. Taking damage reduces it; lethal hazards kill instantly regardless of health. You lose if you die.

You can be hit by an enemy or hazard this turn if any of these happen:
- Overlap: you and the damager end on the same tile.
- Swap: you move into each other’s starting tiles (cross paths head‑on).
- Trail crossing: your paths cross anywhere during the turn.
- Endpoint cross: you end on the damager’s previous tile and the movement paths intersected.

Important exceptions and limits:
- Pure origin step: simply stepping onto the enemy’s just‑vacated tile without any path crossing doesn’t hurt you.
- One hit per damager per turn: each enemy/hazard can affect you at most once each turn.
- Immunity and Phasing effects can prevent damage; using them to block a hit consumes effect time/uses.
- Lethal damage ignores health and kills instantly.

Tip: Because interactions run after each small step, be careful when moving multiple tiles with speed or sliding—you can get hit mid‑chain.


## Collectibles and inventory

- Pick Up collects items on your tile:
    - Coins (or non‑required items): add to your score.
    - Cores (required items): needed to meet the default objective; may also grant score.
    - Keys: stored in your inventory for unlocking doors.
- Some rewards are “on the ground” and not picked up—standing on them grants points automatically after your step (see Tile rewards below).


## Keys and doors

- Locked doors block movement until unlocked with a matching key.
- Use Key while standing on the door to unlock it if you carry the right key.
- Doors usually stay unlocked once opened.


## Tile rewards and costs (score)

- Tile rewards: standing on certain tiles grants points immediately after your step (they are not picked up).
- Tile costs: some floors charge a cost once per action at the end of your turn.
- Collecting items may also change your score depending on the level.


## Effects and powerups

- Speed: grants extra small steps when you take a move action. Effects tick down each turn; uses/time may be limited. You still pay tile costs only once per action.
- Immunity: prevents incoming damage while active (consuming uses/time when it blocks a hit).
- Phasing: lets you pass through blockers and can also negate damage similar to immunity; using it consumes uses/time.


## Win and lose conditions

- Win: the game checks your level’s objective after each step; for the default objective you must collect all required items and then stand on an Exit.
- Lose: if your health reaches zero or you touch a lethal hazard, you die and the game ends.


## Enemy timing and fairness

- Enemies/pathfinders move before your action each turn. Then your action and its interactions play out.
- Damage is calculated with strict rules (see above) and each damager can hit you only once per turn.


## Practical tips

- Don’t forget Pick Up. Many levels require picking up cores before heading to the Exit.
- Watch for chain reactions: portals can move you into danger or out of it within the same turn.
- Use Wait to let enemies step first if you want to avoid a swap/cross.
- Keys only work when you’re on the door tile—face‑checking from the side won’t unlock it.
- If a level mentions sliding or wrap‑around, plan your path with those rules in mind.


## Glossary

- Blocking: prevents entry unless you have Phasing or can push the object.
- Pushable: can be shoved one tile forward if the space beyond is free.
- Collidable: counts for collision/teleport checks and may block pushes.
- Portal: teleports you to its paired portal after stepping onto it, if the destination isn’t blocked.
- Damage: reduces health; Lethal damage kills instantly.
- Required: marks collectibles needed for the default win condition.
- Exit: tile that completes the level when your objective is met (or immediately for “reach exit” levels).

Enjoy exploring the Grid Universe!
