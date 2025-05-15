from dataclasses import replace
from ecs_maze.state import State
from ecs_maze.types import EntityID
from ecs_maze.utils.ecs import entities_with_components_at


def portal_system_entity(state: State, eid: EntityID) -> State:
    # The entity must exist and have a position
    entity_pos = state.position.get(eid)
    if entity_pos is None:
        return state

    # Don't teleport non-entering entities
    entity_prevpos = state.prev_position.get(eid)
    if entity_pos == entity_prevpos:
        return state

    # Find portals at this position
    portal_ids = entities_with_components_at(state, entity_pos, state.portal)
    if not portal_ids:
        return state  # Entity not on a portal

    # Use the first portal found
    portal_id = portal_ids[0]
    portal = state.portal[portal_id]

    # Find the paired portal's position
    pair_id = portal.pair_entity
    pair_pos = state.position.get(pair_id)
    if pair_pos is None:
        return state  # Pair portal entity missing or not placed

    # Teleport entity to the paired portal's position
    new_position = state.position.set(eid, pair_pos)
    return replace(state, position=new_position)


def portal_system(state: State) -> State:
    for eid in state.collidable:
        state = portal_system_entity(state, eid)
    return state
