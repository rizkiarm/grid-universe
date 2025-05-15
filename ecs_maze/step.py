from dataclasses import replace
from ecs_maze.actions import Action, MoveAction, UseKeyAction, PickUpAction, WaitAction
from ecs_maze.types import MoveFn
from ecs_maze.state import State
from ecs_maze.systems.movement import movement_system
from ecs_maze.systems.moving import moving_system
from ecs_maze.systems.position import position_system
from ecs_maze.systems.push import push_system
from ecs_maze.systems.portal import portal_system
from ecs_maze.systems.collectible import collectible_system
from ecs_maze.systems.hazard import hazard_system
from ecs_maze.systems.enemy import enemy_collision_system
from ecs_maze.systems.locked import unlock_system
from ecs_maze.systems.powerup import powerup_tick_system
from ecs_maze.systems.terminal import win_system, lose_system
from ecs_maze.components import PowerUpType, Position
from ecs_maze.systems.tile import tile_reward_system, tile_cost_system
from ecs_maze.types import EntityID
from ecs_maze.utils.gc import run_garbage_collector
from ecs_maze.utils.powerup import is_powerup_active


def step(state: State, action: Action, *, agent_id: EntityID) -> State:
    """
    Main ECS reducer: applies one action, all relevant systems, and returns new state.
    Exits early if state is terminal.
    """
    if state.win or state.lose or agent_id not in state.agent:
        return state

    if agent_id in state.dead:
        return replace(state, lose=True)

    state = moving_system(state)  # move NPCs, etc.
    state = powerup_tick_system(state)

    if isinstance(action, MoveAction):
        state = _step_move(state, action, agent_id)
    elif isinstance(action, UseKeyAction):
        state = _step_usekey(state, action, agent_id)
    elif isinstance(action, PickUpAction):
        state = _step_pickup(state, action, agent_id)
    elif isinstance(action, WaitAction):
        state = _step_wait(state, action, agent_id)
    else:
        raise ValueError("Action is not valid")

    if not isinstance(action, MoveAction):
        state = _after_substep(state, action, agent_id)

    return _after_step(state, agent_id)


def _step_move(state: State, action: MoveAction, agent_id: EntityID) -> State:
    move_fn: MoveFn = state.move_fn
    current_pos = state.position.get(action.entity_id)
    if not current_pos:
        return state

    move_count = (
        2 if is_powerup_active(state, action.entity_id, PowerUpType.DOUBLE_SPEED) else 1
    )

    blocked: bool = False

    for _ in range(move_count):
        for next_pos in move_fn(state, action.entity_id, action.direction):
            # Try to push
            pushed_state = push_system(state, action.entity_id, next_pos)
            if pushed_state != state:
                state = pushed_state
            else:
                moved_state = movement_system(state, action.entity_id, next_pos)
                if moved_state == state:
                    # Blocked; post-move systems, then break
                    blocked = True
                state = moved_state

            # Post-move systems for this step
            state = _after_substep(state, action, agent_id)

            if state.win or state.lose or action.entity_id in state.dead or blocked:
                return state

    return state


def _step_usekey(state: State, action: UseKeyAction, agent_id: EntityID) -> State:
    pos = state.position.get(action.entity_id)
    if pos is not None:
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            adjacent = Position(pos.x + dx, pos.y + dy)
            state = unlock_system(state, action.entity_id, adjacent)
    return state


def _step_pickup(state: State, action: PickUpAction, agent_id: EntityID) -> State:
    state = collectible_system(state, action.entity_id)
    return state


def _step_wait(state: State, action: WaitAction, agent_id: EntityID) -> State:
    return state


def _after_substep(state: State, action: Action, agent_id: EntityID) -> State:
    state = portal_system(state)
    state = hazard_system(state, action.entity_id)
    state = enemy_collision_system(state, action.entity_id)
    state = tile_reward_system(state, agent_id)
    return state


def _after_step(state: State, agent_id: EntityID) -> State:
    state = tile_cost_system(
        state, agent_id
    )  # doesn't penalize faster move (move with submoves)
    state = win_system(state, agent_id)
    state = lose_system(state, agent_id)
    state = replace(state, turn=state.turn + 1)
    state = position_system(state)
    state = run_garbage_collector(state)
    return state
