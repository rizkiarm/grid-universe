from dataclasses import replace
from grid_universe.components import Position, PowerUpType
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.powerup import is_powerup_active


def movement_system(state: State, eid: EntityID, next_pos: Position) -> State:
    if eid not in state.agent:
        return state

    if not (0 <= next_pos.x < state.width and 0 <= next_pos.y < state.height):
        return state  # Out of bounds: don't move

    if is_powerup_active(state, eid, PowerUpType.GHOST):
        # Ignore all blocking, just move
        new_position = state.position.set(eid, next_pos)
        return replace(state, position=new_position)

    # ... regular blocking check ...
    blocked = False
    for other_id, other_pos in state.position.items():
        if other_pos == next_pos and (
            other_id in state.wall
            or other_id in state.blocking
            or other_id in state.pushable
        ):
            blocked = True
            break

    if blocked:
        return state

    new_position = state.position.set(eid, next_pos)
    return replace(state, position=new_position)
