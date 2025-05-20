from dataclasses import replace
from grid_universe.state import State
from grid_universe.components import Moving, MovingAxis, Position
from grid_universe.utils.grid import is_blocked_at, is_in_bounds


def moving_system(state: State) -> State:
    state_position = state.position
    state_moving = state.moving

    for entity_id, moving in state_moving.items():
        pos = state_position.get(entity_id)
        if pos is None:
            continue
        # Compute intended move
        dx, dy = (
            (moving.direction, 0)
            if moving.axis == MovingAxis.HORIZONTAL
            else (0, moving.direction)
        )
        next_pos = Position(pos.x + dx, pos.y + dy)

        if not is_in_bounds(state, next_pos) or is_blocked_at(
            state, next_pos, check_collidable=True
        ):
            # Reverse direction for next tick ("bounce")
            state_moving = state_moving.set(
                entity_id,
                Moving(
                    axis=moving.axis, direction=-moving.direction, prev_position=pos
                ),
            )
        else:
            # Move entity
            state_position = state_position.set(entity_id, next_pos)
            state_moving = state_moving.set(
                entity_id,
                Moving(axis=moving.axis, direction=moving.direction, prev_position=pos),
            )

    return replace(state, position=state_position, moving=state_moving)
