from dataclasses import replace
from typing import Optional
from grid_universe.actions import Action, MOVE_ACTIONS
from grid_universe.systems.damage import damage_system
from grid_universe.systems.pathfinding import pathfinding_system
from grid_universe.systems.status import status_system
from grid_universe.systems.trail import trail_system
from grid_universe.types import MoveFn
from grid_universe.state import State
from grid_universe.systems.movement import movement_system
from grid_universe.systems.moving import moving_system
from grid_universe.systems.position import position_system
from grid_universe.systems.push import push_system
from grid_universe.systems.portal import portal_system
from grid_universe.systems.collectible import collectible_system
from grid_universe.systems.locked import unlock_system
from grid_universe.systems.terminal import win_system, lose_system
from grid_universe.systems.tile import tile_reward_system, tile_cost_system
from grid_universe.types import EntityID
from grid_universe.utils.gc import run_garbage_collector
from grid_universe.utils.status import use_status_effect_if_present
from grid_universe.utils.terminal import is_terminal_state, is_valid_state


def step(state: State, action: Action, agent_id: Optional[EntityID] = None) -> State:
    """
    Main ECS reducer: applies one action, all relevant systems, and returns new state.
    Exits early if state is terminal.
    """
    if agent_id is None and (agent_id := next(iter(state.agent.keys()), None)) is None:
        raise ValueError("State contains no agent")

    if agent_id in state.dead:
        return replace(state, lose=True)

    if not is_valid_state(state, agent_id) or is_terminal_state(state, agent_id):
        return state

    state = position_system(state)  # before movements
    state = moving_system(state)
    state = pathfinding_system(state)
    state = status_system(state)
    state = trail_system(state)  # after movements

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
        for next_pos in move_fn(state, agent_id, action):
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
    state = unlock_system(state, agent_id)
    return state


def _step_pickup(state: State, action: Action, agent_id: EntityID) -> State:
    state = collectible_system(state, agent_id)
    return state


def _step_wait(state: State, action: Action, agent_id: EntityID) -> State:
    return state


def _after_substep(state: State, action: Action, agent_id: EntityID) -> State:
    state = portal_system(state)
    state = damage_system(state)
    state = tile_reward_system(state, agent_id)
    return state


def _after_step(state: State, agent_id: EntityID) -> State:
    state = tile_cost_system(
        state, agent_id
    )  # doesn't penalize faster move (move with submoves)
    state = win_system(state, agent_id)
    state = lose_system(state, agent_id)
    state = replace(state, turn=state.turn + 1)
    state = run_garbage_collector(state)
    return state
