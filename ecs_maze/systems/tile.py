from dataclasses import replace
from typing import Set
from ecs_maze.state import State
from ecs_maze.types import EntityID
from ecs_maze.components import Position
from ecs_maze.utils.ecs import entities_at


def get_rewardable_noncollectible_entities(
    state: State, pos: Position
) -> Set[EntityID]:
    """
    Returns all entity IDs at the given position that are rewardable and not collectible.
    """
    at_pos = entities_at(state, pos)
    rewardable_ids = set(state.rewardable.keys())
    collectible_ids = set(state.collectible.keys())
    return (at_pos & rewardable_ids) - collectible_ids


def tile_reward_system(state: State, eid: EntityID) -> State:
    """
    Grants a reward if the entity is on a tile with a rewardable, non-collectible entity.
    """
    pos = state.position.get(eid)
    if pos is None or eid in state.dead or eid not in state.agent:
        return state

    reward_ids = get_rewardable_noncollectible_entities(state, pos)
    if not reward_ids:
        return state

    score = state.score + sum(state.rewardable[rid].reward for rid in reward_ids)
    return replace(state, score=score)


def get_cost_noncollectible_entities(state: State, pos: Position) -> Set[EntityID]:
    """
    Returns all entity IDs at the given position that are cost and not collectible.
    """
    at_pos = entities_at(state, pos)
    cost_ids = set(state.cost.keys())
    collectible_ids = set(state.collectible.keys())
    return (at_pos & cost_ids) - collectible_ids


def tile_cost_system(state: State, eid: EntityID) -> State:
    """
    Grants a cost if the entity is on a tile with a cost, non-collectible entity.
    """
    pos = state.position.get(eid)
    if pos is None or eid in state.dead or eid not in state.agent:
        return state

    cost_ids = get_cost_noncollectible_entities(state, pos)
    if not cost_ids:
        return state

    score = state.score - sum(state.cost[cid].amount for cid in cost_ids)
    return replace(state, score=score)
