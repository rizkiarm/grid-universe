from dataclasses import replace
from ecs_maze.state import State
from ecs_maze.components import Moving, Position
from ecs_maze.utils.ecs import entities_at


def moving_system(state: State) -> State:
    new_position = state.position
    new_moving = state.moving

    for eid, moving in state.moving.items():
        pos = state.position.get(eid)
        if pos is None:
            continue
        # Compute intended move
        dx, dy = (
            (moving.direction, 0)
            if moving.axis == "horizontal"
            else (0, moving.direction)
        )
        next_pos = Position(pos.x + dx, pos.y + dy)
        # Check blocking
        blocked = False

        if not (0 <= next_pos.x < state.width and 0 <= next_pos.y < state.height):
            blocked = True  # Out of bounds: don't move

        for oid in entities_at(state, next_pos):
            if (
                oid in state.wall
                or oid in state.blocking
                or oid in state.pushable
                or oid in state.collidable
            ):
                blocked = True
                break

        if blocked:
            # Reverse direction for next tick ("bounce")
            new_moving = new_moving.set(
                eid,
                Moving(
                    axis=moving.axis, direction=-moving.direction, prev_position=pos
                ),
            )
        else:
            # Move entity
            new_position = new_position.set(eid, next_pos)
            new_moving = new_moving.set(
                eid,
                Moving(axis=moving.axis, direction=moving.direction, prev_position=pos),
            )

    return replace(state, position=new_position, moving=new_moving)
