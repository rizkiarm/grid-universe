from dataclasses import replace
from typing import TYPE_CHECKING

from grid_universe.components import Position, UsageLimit
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.grid import is_blocked_at, is_in_bounds
from grid_universe.utils.status import use_status_effect_if_present

if TYPE_CHECKING:
    from pyrsistent.typing import PMap


def movement_system(state: State, entity_id: EntityID, next_pos: Position) -> State:
    if entity_id not in state.agent:
        return state

    if not is_in_bounds(state, next_pos):
        return state  # Out of bounds: don't move

    # Check for phasing
    if entity_id in state.status:
        usage_limit: PMap[EntityID, UsageLimit] = state.usage_limit
        usage_limit, effect_id = use_status_effect_if_present(
            state.status[entity_id].effect_ids,
            state.phasing,
            state.time_limit,
            usage_limit,
        )
        if effect_id is not None:
            # Ignore all blocking, just move
            return replace(
                state,
                position=state.position.set(entity_id, next_pos),
                usage_limit=usage_limit,
            )

    if is_blocked_at(state, next_pos, check_collidable=False):
        return state

    return replace(state, position=state.position.set(entity_id, next_pos))
