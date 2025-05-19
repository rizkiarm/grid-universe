from dataclasses import replace

from pyrsistent.typing import PMap
from grid_universe.components import Position, UsageLimit
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.status import get_status_effect, use_status_effect


def movement_system(state: State, entity_id: EntityID, next_pos: Position) -> State:
    if entity_id not in state.agent:
        return state

    if not (0 <= next_pos.x < state.width and 0 <= next_pos.y < state.height):
        return state  # Out of bounds: don't move

    # Check for phasing
    if entity_id in state.status:
        usage_limit: PMap[EntityID, UsageLimit] = state.usage_limit
        effect_id = get_status_effect(
            state.status[entity_id].effect_ids,
            state.phasing,
            state.time_limit,
            usage_limit,
        )
        if effect_id is not None:
            # Ignore all blocking, just move
            new_position = state.position.set(entity_id, next_pos)
            usage_limit = use_status_effect(effect_id, usage_limit)
            return replace(state, position=new_position, usage_limit=usage_limit)

    # ... regular blocking check ...
    blocked = False
    for other_id, other_pos in state.position.items():
        if other_pos == next_pos and (
            other_id in state.blocking or other_id in state.pushable
        ):
            blocked = True
            break

    if blocked:
        return state

    new_position = state.position.set(entity_id, next_pos)
    return replace(state, position=new_position)
