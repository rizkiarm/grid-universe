"""Trail history system.

Builds/updates a mapping from traversed positions to the set of entities that
passed through during the latest movement step. Used by portal and potential
future systems (e.g., footprints, lingering effects, collision trails).
"""

from dataclasses import replace
from typing import Generator

from pyrsistent import pset
from grid_universe.components import Position
from grid_universe.state import State


def between(pos1: Position, pos2: Position) -> Generator[Position, None, None]:
    """Yield intermediate Manhattan grid points from ``pos1`` to ``pos2``.

    Traverses along the x-axis first, then along the y-axis, excluding the
    starting coordinate and including the final y-adjustment intermediate
    cells (exclusive of ``pos2`` itself during x traversal).
    """
    x, y = pos1.x, pos1.y
    step_x = (pos2.x > x) - (pos2.x < x)
    while x != pos2.x:
        x += step_x
        if (x, y) == (pos2.x, pos2.y):
            break
        yield Position(x, y)
    step_y = (pos2.y > y) - (pos2.y < y)
    while y != pos2.y:
        y += step_y
        yield Position(x, y)


def trail_system(state: State) -> State:
    """Accumulate traversed positions into the state's trail map."""
    state_trail = state.trail
    for entity_id, curr_pos in state.position.items():
        prev_pos = state.prev_position.get(entity_id)
        if prev_pos is None:
            continue
        for pos in between(curr_pos, prev_pos):
            state_trail = state_trail.set(
                pos, state_trail.get(pos, pset()).add(entity_id)
            )
    return replace(state, trail=state_trail)
