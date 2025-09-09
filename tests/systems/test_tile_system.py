from dataclasses import replace

from pyrsistent import PMap, pmap, pset

from grid_universe.components import (
    Agent,
    Appearance,
    AppearanceName,
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
from grid_universe.systems.tile import tile_cost_system, tile_reward_system
from grid_universe.types import EntityID


def make_tile_state(
    rewardable_ids: list[EntityID] | None = None,
    cost_ids: list[EntityID] | None = None,
    collectible_ids: list[EntityID] | None = None,
    agent_pos: tuple[int, int] = (0, 0),
    reward_amount: int = 10,
    cost_amount: int = 2,
    agent_dead: bool = False,
    agent_in_state: bool = True,
) -> tuple[State, EntityID]:
    entity: dict[EntityID, Entity] = {}
    agent_id: EntityID = 1
    pos: dict[EntityID, Position] = {agent_id: Position(*agent_pos)}
    agent_map: dict[EntityID, Agent] = {agent_id: Agent()} if agent_in_state else {}
    reward_map: dict[EntityID, Rewardable] = {}
    cost_map: dict[EntityID, Cost] = {}
    collectible_map: dict[EntityID, Collectible] = {}
    inventory: dict[EntityID, Inventory] = {agent_id: Inventory(pset())}
    appearance: dict[EntityID, Appearance] = {
        agent_id: Appearance(name=AppearanceName.HUMAN),
    }
    dead: PMap[EntityID, Dead] = pmap({agent_id: Dead()}) if agent_dead else pmap()

    rewardable_ids = rewardable_ids or []
    cost_ids = cost_ids or []
    collectible_ids = collectible_ids or []

    for rid in rewardable_ids:
        entity[rid] = Entity()
        pos[rid] = Position(*agent_pos)
        reward_map[rid] = Rewardable(amount=reward_amount)
        appearance[rid] = Appearance(name=AppearanceName.COIN)
    for cid in cost_ids:
        entity[cid] = Entity()
        pos[cid] = Position(*agent_pos)
        cost_map[cid] = Cost(amount=cost_amount)
        appearance[cid] = Appearance(name=AppearanceName.COIN)
    for colid in collectible_ids:
        entity[colid] = Entity()
        pos[colid] = Position(*agent_pos)
        collectible_map[colid] = Collectible()
        appearance[colid] = Appearance(name=AppearanceName.CORE)

    entity[agent_id] = Entity()

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
        appearance=pmap(appearance),
        dead=dead,
    )
    return state, agent_id


def agent_step_and_score(state: State, agent_id: EntityID) -> int:
    next_state: State = tile_reward_system(state, agent_id)
    next_state = tile_cost_system(next_state, agent_id)
    return next_state.score


def test_rewardable_tile_grants_score() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2])
    assert agent_step_and_score(state, agent_id) == 10


def test_cost_tile_removes_score() -> None:
    state, agent_id = make_tile_state(cost_ids=[3])
    assert agent_step_and_score(state, agent_id) == -2


def test_rewardable_ignored_if_collectible() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2], collectible_ids=[2])
    assert agent_step_and_score(state, agent_id) == 0


def test_cost_ignored_if_collectible() -> None:
    state, agent_id = make_tile_state(cost_ids=[3], collectible_ids=[3])
    assert agent_step_and_score(state, agent_id) == 0


def test_multiple_rewardables_and_costs() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2, 3], cost_ids=[4, 5])
    assert agent_step_and_score(state, agent_id) == 10 + 10 - 2 - 2


def test_reward_and_cost_both_collectible_ignored() -> None:
    state, agent_id = make_tile_state(
        rewardable_ids=[2], cost_ids=[3], collectible_ids=[2, 3],
    )
    assert agent_step_and_score(state, agent_id) == 0


def test_reward_cost_same_tile() -> None:
    # Both rewardable and cost at same position, not collectible
    state, agent_id = make_tile_state(rewardable_ids=[2], cost_ids=[2])
    assert agent_step_and_score(state, agent_id) == 10 - 2


def test_zero_and_negative_rewards_costs() -> None:
    state, agent_id = make_tile_state(
        rewardable_ids=[2, 3], cost_ids=[4, 5], reward_amount=0, cost_amount=-6,
    )
    assert agent_step_and_score(state, agent_id) == 0 + 0 - (-6) - (-6)


def test_rewardable_with_some_collectible() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2, 3], collectible_ids=[3])
    assert agent_step_and_score(state, agent_id) == 10


def test_cost_with_some_collectible() -> None:
    state, agent_id = make_tile_state(cost_ids=[2, 3], collectible_ids=[2])
    assert agent_step_and_score(state, agent_id) == -2


def test_rewardable_at_another_position() -> None:
    state, agent_id = make_tile_state()
    rewardable_id = 99
    reward_map = state.rewardable.set(rewardable_id, Rewardable(amount=11))
    pos_map = state.position.set(rewardable_id, Position(1, 0))
    state = replace(
        state,
        rewardable=reward_map,
        position=pos_map,
        entity=state.entity.set(rewardable_id, Entity()),
    )
    assert agent_step_and_score(state, agent_id) == 0


def test_cost_at_another_position() -> None:
    state, agent_id = make_tile_state()
    cost_id = 77
    cost_map = state.cost.set(cost_id, Cost(amount=6))
    pos_map = state.position.set(cost_id, Position(1, 0))
    state = replace(
        state,
        cost=cost_map,
        position=pos_map,
        entity=state.entity.set(cost_id, Entity()),
    )
    assert agent_step_and_score(state, agent_id) == 0


def test_agent_dead_no_score_change() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2], cost_ids=[3], agent_dead=True)
    assert agent_step_and_score(state, agent_id) == 0


def test_agent_missing_from_state() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2], cost_ids=[3])
    state = replace(state, agent=state.agent.remove(agent_id))
    assert agent_step_and_score(state, agent_id) == 0


def test_agent_missing_position() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2], cost_ids=[3])
    state = replace(state, position=state.position.remove(agent_id))
    assert agent_step_and_score(state, agent_id) == 0


def test_multiple_agents_separate_scores() -> None:
    agent1_id = 1
    agent2_id = 2
    entity: dict[EntityID, Entity] = {
        agent1_id: Entity(),
        agent2_id: Entity(),
        3: Entity(),
        4: Entity(),
    }
    pos = {
        agent1_id: Position(0, 0),
        agent2_id: Position(1, 0),
        3: Position(0, 0),  # rewardable for agent1
        4: Position(1, 0),  # cost for agent2
    }
    agent_map: dict[EntityID, Agent] = {agent1_id: Agent(), agent2_id: Agent()}
    rewardable = {3: Rewardable(amount=12)}
    cost = {4: Cost(amount=7)}
    inventory = {agent1_id: Inventory(pset()), agent2_id: Inventory(pset())}
    appearance: dict[EntityID, Appearance] = {
        agent1_id: Appearance(name=AppearanceName.HUMAN),
        agent2_id: Appearance(name=AppearanceName.HUMAN),
        3: Appearance(name=AppearanceName.COIN),
        4: Appearance(name=AppearanceName.COIN),
    }
    state = State(
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
        appearance=pmap(appearance),
    )
    score1 = agent_step_and_score(state, agent1_id)
    score2 = agent_step_and_score(state, agent2_id)
    assert score1 == 12
    assert score2 == -7
