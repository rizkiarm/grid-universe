"""State reducer and step orchestration.

This module wires together all systems in the correct order to implement a
single *turn* transition given an ``Action``. The exported :func:`step` is the
only public mutation entry point for gameplay progression and is intentionally
pure: it returns a *new* :class:`grid_universe.state.State`.

Ordering rationale (high level):

1. ``position_system`` snapshots previous positions (enables trail / cross checks).
2. Autonomous movers & pathfinding update entities (``moving_system`` / ``pathfinding_system``).
3. ``status_tick_system`` decrements effect limits before applying player action.
4. Player action sub‑steps (movement may produce multiple sub‑moves via speed effects).
5. After each sub‑move we run interaction systems (portal, damage, rewards) to
    allow chained behaviors (e.g. portal then damage at destination).
6. After the *entire* action we apply GC, tile costs, terminal checks, and bump turn.

All helper ``_step_*`` functions are internal and assume validation of inputs.
"""

from dataclasses import replace
from typing import Optional
from pyrsistent import pset, pmap
from grid_universe.actions import Action, MOVE_ACTIONS
from grid_universe.systems.damage import damage_system
from grid_universe.systems.pathfinding import pathfinding_system
from grid_universe.systems.status import status_gc_system, status_tick_system
from grid_universe.types import MoveFn
from grid_universe.state import State
from grid_universe.systems.movement import movement_system
from grid_universe.systems.moving import moving_system
from grid_universe.systems.position import position_system
from grid_universe.systems.push import push_system
from grid_universe.systems.portal import portal_system
from grid_universe.systems.collectible import collectible_system
from grid_universe.systems.locked import unlock_system
from grid_universe.systems.terminal import turn_system, win_system, lose_system
from grid_universe.systems.tile import tile_reward_system, tile_cost_system
from grid_universe.types import EntityID
from grid_universe.utils.gc import run_garbage_collector
from grid_universe.utils.status import use_status_effect_if_present
from grid_universe.utils.terminal import is_terminal_state, is_valid_state
from grid_universe.utils.trail import add_trail_position


def step(state: State, action: Action, agent_id: Optional[EntityID] = None) -> State:
    """Advance the simulation by one logical action.

    Resolves autonomous movement, applies the player's chosen ``Action`` (which
    may translate to multiple movement sub‑steps for speed effects), runs
    interaction / status systems, and returns a new ``State``.

    Args:
        state (State): Previous immutable world state.
        action (Action): Player action enum value to apply.
        agent_id (EntityID | None): Explicit agent entity id. If ``None`` the first
            entity in ``state.agent`` is used. Raises if no agent exists.

    Returns:
        State: Next state snapshot. If the input state is already terminal (win/lose)
            or invalid the same object may be returned unchanged.

    Raises:
        ValueError: If there is no agent or the action is not recognized.
    """
    if agent_id is None and (agent_id := next(iter(state.agent.keys()), None)) is None:
        raise ValueError("State contains no agent")

    if agent_id in state.dead:
        return replace(state, lose=True)

    if not is_valid_state(state, agent_id) or is_terminal_state(state, agent_id):
        return state

    # Reset per-action damage hit tracking and trail at the very start of a new step
    state = replace(state, damage_hits=pset(), trail=pmap())

    state = position_system(state)  # before movements
    state = moving_system(state)
    state = pathfinding_system(state)
    state = status_tick_system(state)

    if action in MOVE_ACTIONS:
        state = _step_move(state, action, agent_id)
    elif action == Action.USE_KEY:
        state = _step_usekey(state, action, agent_id)
    elif action == Action.PICK_UP:
        state = _step_pickup(state, action, agent_id)
    elif action == Action.WAIT:
        state = _step_wait(state, action, agent_id)
    else:
        raise ValueError("Action is not valid")

    if action not in MOVE_ACTIONS:
        state = _after_substep(state, action, agent_id)

    return _after_step(state, agent_id)


def _step_move(state: State, action: Action, agent_id: EntityID) -> State:
    """Handle movement actions including speed effect chaining.

    The movement logic supports *sub‑moves*: if the agent has a SPEED effect
    active its multiplier increases the number of candidate move sequences.
    After each sub‑move we run post‑substep systems (portal, damage, reward).

    Blocking / pushing:
        * Attempt push first (``push_system``). If successful we adopt that state.
        * Otherwise try raw movement (``movement_system``). If unchanged the path
          is blocked and we stop processing further sub‑moves.

    Early exit if win/lose/agent death or movement blocked mid chain.

    Args:
        state (State): Current state prior to executing the movement action.
        action (Action): One of the directional ``Action`` enum members.
        agent_id (EntityID): Controlled agent entity id.

    Returns:
        State: Updated state after applying movement (and possible sub‑moves).
    """
    move_fn: MoveFn = state.move_fn
    current_pos = state.position.get(agent_id)
    if not current_pos:
        return state

    move_count = 1

    if agent_id in state.status:
        usage_limit, effect_id = use_status_effect_if_present(
            state.status[agent_id].effect_ids,
            state.speed,
            state.time_limit,
            state.usage_limit,
        )
        if effect_id is not None:
            move_count = state.speed[effect_id].multiplier * move_count
            state = replace(state, usage_limit=usage_limit)

    blocked: bool = False

    for _ in range(move_count):
        positions = move_fn(state, agent_id, action)
        if len(positions) == 0:
            positions = [current_pos]  # no move possible
        for next_pos in positions:
            # Try to push
            pushed_state = push_system(state, agent_id, next_pos)
            if pushed_state != state:
                state = pushed_state
            else:
                moved_state = movement_system(state, agent_id, next_pos)
                if moved_state == state:
                    # Blocked; post-move systems, then break
                    blocked = True
                state = moved_state

            # Post-move systems for this step
            state = _after_substep(state, action, agent_id)

            if state.win or state.lose or agent_id in state.dead or blocked:
                return state

    return state


def _step_usekey(state: State, action: Action, agent_id: EntityID) -> State:
    """Apply the use‑key action.

    Delegates to :func:`grid_universe.systems.locked.unlock_system` which will
    unlock any overlapping locked entities if the agent carries a required key.
    """
    state = unlock_system(state, agent_id)
    return state


def _step_pickup(state: State, action: Action, agent_id: EntityID) -> State:
    """Apply the pick‑up action.

    Invokes :func:`grid_universe.systems.collectible.collectible_system` to
    transfer any collectible entities at the agent's position into their
    inventory, updating score and required objectives as needed.
    """
    state = collectible_system(state, agent_id)
    return state


def _step_wait(state: State, action: Action, agent_id: EntityID) -> State:
    """No‑op action placeholder (useful for timing or effect ticking).

    Effects still tick earlier in the reducer; this simply consumes a turn.
    """
    return state


def _after_substep(state: State, action: Action, agent_id: EntityID) -> State:
    """Run interaction systems after each movement *sub‑step*.

    Applies teleportation, collision / damage resolution and immediate tile
    reward scoring before potentially performing further sub‑moves.

    Args:
        state (State): Current state after a movement attempt.
        action (Action): Action being processed.
        agent_id (EntityID): Acting agent.

    Returns:
        State: Updated state after interaction systems.
    """
    state = add_trail_position(state, agent_id, state.position[agent_id])
    state = portal_system(state)
    state = damage_system(state)
    state = tile_reward_system(state, agent_id)
    state = position_system(state)
    state = win_system(state, agent_id)
    state = lose_system(state, agent_id)
    return state


def _after_step(state: State, agent_id: EntityID) -> State:
    """Finalize a full action step.

    Performs status effect garbage collection, applies tile costs once per
    logical action (avoiding double penalization for sub‑moves), evaluates win
    / lose conditions, increments the turn counter and prunes unreachable
    entities.

    Args:
        state (State): State after all sub‑steps for the action.
        agent_id (EntityID): Acting agent id.

    Returns:
        State: Finalized state for the action step.
    """
    state = tile_cost_system(
        state, agent_id
    )  # doesn't penalize faster move (move with submoves)
    state = replace(state, turn=state.turn + 1)
    state = turn_system(state, agent_id)
    state = status_gc_system(state)
    state = run_garbage_collector(state)
    return state
