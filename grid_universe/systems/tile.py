from dataclasses import replace

from pyrsistent.typing import PMap

from grid_universe.components import Cost, Position, Rewardable
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.ecs import entities_at
from grid_universe.utils.terminal import is_terminal_state, is_valid_state


def get_noncollectible_entities(
    state: State,
    pos: Position,
    component_map: PMap[EntityID, Rewardable] | PMap[EntityID, Cost],
) -> set[EntityID]:
    at_pos = entities_at(state, pos)
    ids = set(component_map.keys())
    collectible_ids = set(state.collectible.keys())
    return (at_pos & ids) - collectible_ids


def tile_reward_system(state: State, eid: EntityID) -> State:
    pos = state.position.get(eid)
    if not is_valid_state(state, eid) or is_terminal_state(state, eid) or pos is None:
        return state

    reward_ids = get_noncollectible_entities(state, pos, state.rewardable)
    if not reward_ids:
        return state

    score = state.score + sum(state.rewardable[rid].amount for rid in reward_ids)
    return replace(state, score=score)


def tile_cost_system(state: State, eid: EntityID) -> State:
    pos = state.position.get(eid)
    if not is_valid_state(state, eid) or is_terminal_state(state, eid) or pos is None:
        return state

    cost_ids = get_noncollectible_entities(state, pos, state.cost)
    if not cost_ids:
        return state

    score = state.score - sum(state.cost[cid].amount for cid in cost_ids)
    return replace(state, score=score)
