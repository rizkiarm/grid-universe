from dataclasses import replace
from itertools import count
from queue import PriorityQueue

from pyrsistent import pvector
from pyrsistent.typing import PMap

from grid_universe.components import PathfindingType, Position, UsageLimit
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.grid import is_blocked_at, is_in_bounds
from grid_universe.utils.math import (
    argmax,
    position_to_vector,
    vector_dot_product,
    vector_substract,
)
from grid_universe.utils.status import use_status_effect_if_present


def get_astar_next_position(
    state: State, entity_id: EntityID, target_id: EntityID,
) -> Position:
    """Returns the next position along the shortest A* path from entity_id to target_id.
    If already at the goal or no path, returns current position.
    Only considers blocking as obstacles (not collidable or pushable, consistent with movement_system).
    """
    start = state.position[entity_id]
    goal = state.position[target_id]

    if start == goal:
        return start

    def in_bounds(pos: Position) -> bool:
        return is_in_bounds(state, pos)

    def is_blocked(pos: Position) -> bool:
        return is_blocked_at(state, pos, check_collidable=False)

    def heuristic(a: Position, b: Position) -> int:
        return abs(a.x - b.x) + abs(a.y - b.y)

    neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    def get_valid_next_positions(position: Position) -> list[Position]:
        neighbor_positions = [
            Position(position.x + dx, position.y + dy) for dx, dy in neighbors
        ]
        return [
            pos for pos in neighbor_positions if in_bounds(pos) and not is_blocked(pos)
        ]

    frontier: PriorityQueue[tuple[int, int, Position]] = PriorityQueue()
    prev_pos: dict[Position, Position] = {}
    cost_so_far: dict[Position, int] = {start: 0}

    tiebreaker = count()  # Unique sequence count
    frontier.put((0, next(tiebreaker), start))

    while not frontier.empty():
        _, __, current = frontier.get()
        if current == goal:
            break
        for next_pos in get_valid_next_positions(current):
            new_cost = cost_so_far[current] + 1
            if next_pos not in cost_so_far or new_cost < cost_so_far[next_pos]:
                cost_so_far[next_pos] = new_cost
                priority = new_cost + heuristic(next_pos, goal)
                frontier.put((priority, next(tiebreaker), next_pos))
                prev_pos[next_pos] = current

    # Reconstruct path
    if goal not in prev_pos:
        return start  # No path found

    # Walk backwards to get the path
    path = []
    current = goal
    while current != start:
        path.append(current)
        current = prev_pos[current]
    path.reverse()

    if not path:
        return start
    return path[0]


def get_straight_line_next_position(
    state: State, entity_id: EntityID, target_id: EntityID,
) -> Position:
    target_vec = position_to_vector(state.position[target_id])
    entity_vec = position_to_vector(state.position[entity_id])
    dvec = vector_substract(target_vec, entity_vec)
    actions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    values = [vector_dot_product(pvector(action), dvec) for action in actions]
    best_action = actions[argmax(values)]
    return Position(
        state.position[entity_id].x + best_action[0],
        state.position[entity_id].y + best_action[1],
    )


def entity_pathfinding(
    state: State, usage_limit: PMap[EntityID, UsageLimit], entity_id: EntityID,
) -> State:
    if entity_id not in state.position or entity_id not in state.pathfinding:
        return state

    pathfinding_type = state.pathfinding[entity_id].type
    pathfinding_target = state.pathfinding[entity_id].target

    if pathfinding_target is None:
        return state

    if pathfinding_target in state.status:
        usage_limit, effect_id = use_status_effect_if_present(
            state.status[pathfinding_target].effect_ids,
            state.phasing,
            state.time_limit,
            usage_limit,
        )
        if effect_id is not None:
            return state

    if pathfinding_type == PathfindingType.STRAIGHT_LINE:
        next_pos = get_straight_line_next_position(state, entity_id, pathfinding_target)
    elif pathfinding_type == PathfindingType.PATH:
        next_pos = get_astar_next_position(state, entity_id, pathfinding_target)
    else:
        raise NotImplementedError

    if is_blocked_at(state, next_pos, check_collidable=False) or not is_in_bounds(
        state, next_pos,
    ):
        return state

    return replace(state, position=state.position.set(entity_id, next_pos))


def pathfinding_system(state: State) -> State:
    usage_limit: PMap[EntityID, UsageLimit] = state.usage_limit
    for entity_id in state.pathfinding:
        state = entity_pathfinding(state, usage_limit, entity_id)
    return state
