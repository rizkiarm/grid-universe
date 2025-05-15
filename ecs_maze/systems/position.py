from dataclasses import replace
from typing import Dict

from pyrsistent import pmap
from ecs_maze.components import Position
from ecs_maze.state import State
from ecs_maze.types import EntityID


def position_system(state: State) -> State:
    prev_position: Dict[EntityID, Position] = {}
    for eid, pos in state.position.items():
        prev_position[eid] = pos
    return replace(state, prev_position=pmap(prev_position))
