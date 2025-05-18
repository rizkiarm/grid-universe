from dataclasses import replace
from typing import Dict

from pyrsistent import pmap
from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID


def position_system(state: State) -> State:
    prev_position: Dict[EntityID, Position] = {}
    for eid, pos in state.position.items():
        prev_position[eid] = pos
    return replace(state, prev_position=pmap(prev_position))
