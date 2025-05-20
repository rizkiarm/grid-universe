from dataclasses import replace
from typing import Tuple
from pyrsistent.typing import PMap
from grid_universe.state import State
from grid_universe.components import Moving, MovingAxis, Position
from grid_universe.types import EntityID
from grid_universe.utils.grid import is_blocked_at, is_in_bounds


def move(
    state: State,
    entity_id: EntityID,
    pos: Position,
    next_pos: Position,
    state_moving: PMap[EntityID, Moving],
    state_position: PMap[EntityID, Position],
) -> Tuple[PMap[EntityID, Moving], PMap[EntityID, Position]]:
    moving = state.moving[entity_id]
    if not is_in_bounds(state, next_pos) or is_blocked_at(
        state, next_pos, check_collidable=entity_id in state.blocking
    ):
        state_moving = state_moving.set(
            entity_id,
            replace(
                moving,
                direction=moving.direction * (-1 if moving.bounce else 1),
                prev_position=pos,
            ),
        )
    else:
        state_position = state_position.set(entity_id, next_pos)
        state_moving = state_moving.set(
            entity_id,
            replace(moving, prev_position=pos),
        )
    return state_moving, state_position


def moving_system(state: State) -> State:
    state_position = state.position
    state_moving = state.moving

    for entity_id, moving in state_moving.items():
        pos = state_position.get(entity_id)
        if pos is None:
            continue

        if moving.direction not in [-1, 1]:
            raise ValueError("Invalid moving direction:", moving.direction)

        for delta in range(1, moving.speed + 1):
            pos = state_position[entity_id]
            dx, dy = (
                (moving.direction, 0)
                if moving.axis == MovingAxis.HORIZONTAL
                else (0, moving.direction)
            )
            next_pos = Position(pos.x + dx, pos.y + dy)
            state_moving, state_position = move(
                state, entity_id, pos, next_pos, state_moving, state_position
            )

    return replace(state, position=state_position, moving=state_moving)
