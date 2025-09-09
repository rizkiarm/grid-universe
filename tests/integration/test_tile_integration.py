from dataclasses import replace

from pyrsistent import pmap, pset

from grid_universe.actions import Action
from grid_universe.components import (
    Agent,
    Collectible,
    Cost,
    Dead,
    Inventory,
    Position,
    Rewardable,
)
from grid_universe.entity import Entity
from grid_universe.objectives import default_objective_fn
from grid_universe.state import State
from grid_universe.step import step
from grid_universe.types import EntityID


def make_agent_tile_state(
    *,
    agent_pos: tuple[int, int],
    rewardable: dict[EntityID, int] | None = None,
    cost: dict[EntityID, int] | None = None,
    collectible_ids: list[EntityID] | None = None,
    agent_dead: bool = False,
    agent_in_state: bool = True,
) -> tuple[State, EntityID]:
    agent_id: EntityID = 1
    pos: dict[EntityID, Position] = {agent_id: Position(*agent_pos)}
    agent_map: dict[EntityID, Agent] = {agent_id: Agent()} if agent_in_state else {}
    reward_map: dict[EntityID, Rewardable] = {}
    cost_map: dict[EntityID, Cost] = {}
    collectible_map: dict[EntityID, Collectible] = {}
    inventory: dict[EntityID, Inventory] = {agent_id: Inventory(pset())}

    entity: dict[EntityID, Entity] = {}
    entity[agent_id] = Entity()
    if rewardable:
        for rid, reward in rewardable.items():
            pos[rid] = Position(*agent_pos)
            reward_map[rid] = Rewardable(amount=reward)
            entity[rid] = Entity()
    if cost:
        for cid, cvalue in cost.items():
            pos[cid] = Position(*agent_pos)
            cost_map[cid] = Cost(amount=cvalue)
            entity[cid] = Entity()
    if collectible_ids:
        for cid in collectible_ids:
            pos[cid] = Position(*agent_pos)
            collectible_map[cid] = Collectible()
            entity[cid] = Entity()

    state: State = State(
        width=3,
        height=1,
        move_fn=lambda s, eid, d: [],
        objective_fn=default_objective_fn,
        entity=pmap(entity),
        position=pmap(pos),
        agent=pmap(agent_map),
        collectible=pmap(collectible_map),
        rewardable=pmap(reward_map),
        cost=pmap(cost_map),
        inventory=pmap(inventory),
        dead=pmap({agent_id: Dead()}) if agent_dead else pmap(),
    )
    return state, agent_id


def agent_step_and_score(state: State, agent_id: EntityID) -> int:
    next_state: State = step(state, Action.WAIT, agent_id=agent_id)
    return next_state.score


def test_rewardable_tile_grants_score() -> None:
    state, agent_id = make_agent_tile_state(agent_pos=(0, 0), rewardable={2: 10})
    assert agent_step_and_score(state, agent_id) == 10


def test_cost_tile_removes_score() -> None:
    state, agent_id = make_agent_tile_state(agent_pos=(0, 0), cost={3: 4})
    assert agent_step_and_score(state, agent_id) == -4


def test_rewardable_ignored_if_collectible() -> None:
    state, agent_id = make_agent_tile_state(
        agent_pos=(0, 0), rewardable={2: 10}, collectible_ids=[2],
    )
    assert agent_step_and_score(state, agent_id) == 0


def test_cost_ignored_if_collectible() -> None:
    state, agent_id = make_agent_tile_state(
        agent_pos=(0, 0), cost={3: 4}, collectible_ids=[3],
    )
    assert agent_step_and_score(state, agent_id) == 0


def test_multiple_rewardables_and_costs() -> None:
    state, agent_id = make_agent_tile_state(
        agent_pos=(0, 0), rewardable={2: 5, 3: 6}, cost={4: 2, 5: 3},
    )
    # +5 +6 -2 -3 = 6
    assert agent_step_and_score(state, agent_id) == 6


def test_reward_and_cost_both_collectible_ignored() -> None:
    state, agent_id = make_agent_tile_state(
        agent_pos=(0, 0), rewardable={2: 10}, cost={3: 4}, collectible_ids=[2, 3],
    )
    assert agent_step_and_score(state, agent_id) == 0


def test_reward_cost_same_tile() -> None:
    # Both rewardable and cost at same position, not collectible
    state, agent_id = make_agent_tile_state(
        agent_pos=(0, 0), rewardable={2: 10}, cost={2: 7},
    )
    # +10 -7 = 3
    assert agent_step_and_score(state, agent_id) == 3


def test_zero_and_negative_rewards_costs() -> None:
    state, agent_id = make_agent_tile_state(
        agent_pos=(0, 0), rewardable={2: 0, 3: -5}, cost={4: 0, 5: -6},
    )
    # 0 + (-5) - 0 - (-6) = 1
    assert agent_step_and_score(state, agent_id) == 1


def test_rewardable_with_some_collectible() -> None:
    # One rewardable is collectible, one is not
    state, agent_id = make_agent_tile_state(
        agent_pos=(0, 0), rewardable={2: 10, 3: 7}, collectible_ids=[3],
    )
    # Only 2 counts
    assert agent_step_and_score(state, agent_id) == 10


def test_cost_with_some_collectible() -> None:
    # One cost is collectible, one is not
    state, agent_id = make_agent_tile_state(
        agent_pos=(0, 0), cost={2: 5, 3: 8}, collectible_ids=[2],
    )
    # Only 3 counts
    assert agent_step_and_score(state, agent_id) == -8


def test_rewardable_at_another_position() -> None:
    # Rewardable at (1,0), agent at (0,0)
    state, agent_id = make_agent_tile_state(agent_pos=(0, 0))
    rewardable_id: EntityID = 99
    reward_map = state.rewardable.set(rewardable_id, Rewardable(amount=11))
    pos_map = state.position.set(rewardable_id, Position(1, 0))
    entity_map = state.entity.set(rewardable_id, Entity())
    state = replace(state, rewardable=reward_map, position=pos_map, entity=entity_map)
    assert agent_step_and_score(state, agent_id) == 0


def test_cost_at_another_position() -> None:
    # Cost at (1,0), agent at (0,0)
    state, agent_id = make_agent_tile_state(agent_pos=(0, 0))
    cost_id: EntityID = 77
    cost_map = state.cost.set(cost_id, Cost(amount=6))
    pos_map = state.position.set(cost_id, Position(1, 0))
    entity_map = state.entity.set(cost_id, Entity())
    state = replace(state, cost=cost_map, position=pos_map, entity=entity_map)
    assert agent_step_and_score(state, agent_id) == 0


def test_agent_dead_no_score_change() -> None:
    state, agent_id = make_agent_tile_state(
        agent_pos=(0, 0), rewardable={2: 9}, cost={3: 5}, agent_dead=True,
    )
    assert agent_step_and_score(state, agent_id) == 0


def test_agent_missing_from_state() -> None:
    # Remove agent from agent map
    state, agent_id = make_agent_tile_state(
        agent_pos=(0, 0), rewardable={2: 5}, cost={3: 2},
    )
    state = replace(state, agent=state.agent.remove(agent_id))
    assert agent_step_and_score(state, agent_id) == 0


def test_agent_missing_position() -> None:
    # Remove agent position
    state, agent_id = make_agent_tile_state(
        agent_pos=(0, 0), rewardable={2: 5}, cost={3: 2},
    )
    state = replace(state, position=state.position.remove(agent_id))
    assert agent_step_and_score(state, agent_id) == 0


def test_multiple_agents_separate_scores() -> None:
    # Each agent only gets score for their tile
    agent1_id: EntityID = 1
    agent2_id: EntityID = 2
    pos: dict[EntityID, Position] = {
        agent1_id: Position(0, 0),
        agent2_id: Position(1, 0),
        3: Position(0, 0),  # rewardable for agent1
        4: Position(1, 0),  # cost for agent2
    }
    agent_map: dict[EntityID, Agent] = {agent1_id: Agent(), agent2_id: Agent()}
    rewardable = {3: Rewardable(amount=12)}
    cost = {4: Cost(amount=7)}
    inventory = {agent1_id: Inventory(pset()), agent2_id: Inventory(pset())}
    entity: dict[EntityID, Entity] = {
        agent1_id: Entity(),
        agent2_id: Entity(),
        3: Entity(),
        4: Entity(),
    }
    state: State = State(
        width=2,
        height=1,
        move_fn=lambda s, eid, d: [],
        objective_fn=default_objective_fn,
        entity=pmap(entity),
        position=pmap(pos),
        agent=pmap(agent_map),
        rewardable=pmap(rewardable),
        cost=pmap(cost),
        inventory=pmap(inventory),
    )
    score1 = agent_step_and_score(state, agent1_id)
    score2 = agent_step_and_score(state, agent2_id)
    assert score1 == 12
    assert score2 == -7
