from dataclasses import replace
from grid_universe.systems.tile import tile_reward_system, tile_cost_system
from grid_universe.components import (
    Agent,
    Rewardable,
    Cost,
    Collectible,
    Inventory,
    Dead,
    Position,
)
from grid_universe.state import State
from grid_universe.types import EntityID
from pyrsistent import pmap, pset


def make_tile_state(
    rewardable_ids: list[EntityID] = [],
    cost_ids: list[EntityID] = [],
    collectible_ids: list[EntityID] = [],
    agent_pos: tuple[int, int] = (0, 0),
    reward_amount: int = 10,
    cost_amount: int = 2,
) -> tuple[State, EntityID]:
    agent_id = 1
    pos = {agent_id: Position(*agent_pos)}
    agent = pmap({agent_id: Agent()})
    rewardable = {}
    cost = {}
    collectible = {}
    inventory = pmap({agent_id: Inventory(pset())})

    for rid in rewardable_ids:
        pos[rid] = Position(*agent_pos)
        rewardable[rid] = Rewardable(reward=reward_amount)
    for cid in cost_ids:
        pos[cid] = Position(*agent_pos)
        cost[cid] = Cost(amount=cost_amount)
    for cid in collectible_ids:
        pos[cid] = Position(*agent_pos)
        collectible[cid] = Collectible()

    state = State(
        width=3,
        height=1,
        move_fn=lambda s, eid, dir: [],
        position=pmap(pos),
        agent=agent,
        enemy=pmap(),
        box=pmap(),
        pushable=pmap(),
        wall=pmap(),
        door=pmap(),
        locked=pmap(),
        portal=pmap(),
        exit=pmap(),
        key=pmap(),
        collectible=pmap(collectible),
        rewardable=pmap(rewardable),
        cost=pmap(cost),
        item=pmap(),
        required=pmap(),
        inventory=inventory,
        health=pmap(),
        powerup=pmap(),
        powerup_status=pmap(),
        floor=pmap(),
        blocking=pmap(),
        dead=pmap(),
        moving=pmap(),
        hazard=pmap(),
        collidable=pmap(),
        damage=pmap(),
        lethal_damage=pmap(),
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
    return state, agent_id


def test_tile_reward_system_grants_score() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2])
    new_state = tile_reward_system(state, agent_id)
    assert new_state.score == 10


def test_tile_cost_system_removes_score() -> None:
    state, agent_id = make_tile_state(cost_ids=[3])
    new_state = tile_cost_system(state, agent_id)
    assert new_state.score == -2


def test_tile_reward_system_ignores_collectible() -> None:
    # If there's both a rewardable and a collectible at the same pos, must NOT grant reward
    state, agent_id = make_tile_state(rewardable_ids=[2], collectible_ids=[2])
    new_state = tile_reward_system(state, agent_id)
    assert new_state.score == 0


def test_tile_cost_system_ignores_collectible() -> None:
    # If there's both a cost and a collectible at the same pos, must NOT apply cost
    state, agent_id = make_tile_state(cost_ids=[3], collectible_ids=[3])
    new_state = tile_cost_system(state, agent_id)
    assert new_state.score == 0


def test_tile_reward_system_multiple_rewards() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2, 3])
    new_state = tile_reward_system(state, agent_id)
    assert new_state.score == 20


def test_tile_cost_system_multiple_costs() -> None:
    state, agent_id = make_tile_state(cost_ids=[4, 5])
    new_state = tile_cost_system(state, agent_id)
    assert new_state.score == -4


def test_tile_reward_system_agent_dead() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2])
    state = replace(state, dead=state.dead.set(agent_id, Dead()))
    new_state = tile_reward_system(state, agent_id)
    assert new_state.score == 0


def test_tile_cost_system_agent_dead() -> None:
    state, agent_id = make_tile_state(cost_ids=[3])
    state = replace(state, dead=state.dead.set(agent_id, Dead()))
    new_state = tile_cost_system(state, agent_id)
    assert new_state.score == 0


def test_tile_reward_system_agent_position_missing() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2])
    state = replace(state, position=state.position.remove(agent_id))
    new_state = tile_reward_system(state, agent_id)
    assert new_state.score == 0


def test_tile_cost_system_agent_position_missing() -> None:
    state, agent_id = make_tile_state(cost_ids=[3])
    state = replace(state, position=state.position.remove(agent_id))
    new_state = tile_cost_system(state, agent_id)
    assert new_state.score == 0


def test_tile_reward_cost_same_tile() -> None:
    # Agent on tile with rewardable 2 and cost 3
    state, agent_id = make_tile_state(rewardable_ids=[2], cost_ids=[3])
    new_state = tile_reward_system(state, agent_id)
    new_state = tile_cost_system(new_state, agent_id)
    assert new_state.score == 8  # +10, then -2


def test_tile_reward_zero_negative() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2], reward_amount=0)
    new_state = tile_reward_system(state, agent_id)
    assert new_state.score == 0
    state_neg, agent_id = make_tile_state(rewardable_ids=[2], reward_amount=-5)
    new_state_neg = tile_reward_system(state_neg, agent_id)
    assert new_state_neg.score == -5


def test_tile_cost_zero_negative() -> None:
    state, agent_id = make_tile_state(cost_ids=[3], cost_amount=0)
    new_state = tile_cost_system(state, agent_id)
    assert new_state.score == 0
    state_neg, agent_id = make_tile_state(cost_ids=[3], cost_amount=-6)
    new_state_neg = tile_cost_system(state_neg, agent_id)
    assert new_state_neg.score == 6


def test_tile_reward_system_no_rewardable() -> None:
    state, agent_id = make_tile_state()
    new_state = tile_reward_system(state, agent_id)
    assert new_state.score == 0


def test_tile_cost_system_no_cost() -> None:
    state, agent_id = make_tile_state()
    new_state = tile_cost_system(state, agent_id)
    assert new_state.score == 0


def test_tile_reward_system_no_agent_in_state() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2])
    state = replace(state, agent=state.agent.remove(agent_id))
    new_state = tile_reward_system(state, agent_id)
    assert new_state.score == 0


def test_tile_cost_system_no_agent_in_state() -> None:
    state, agent_id = make_tile_state(cost_ids=[3])
    state = replace(state, agent=state.agent.remove(agent_id))
    new_state = tile_cost_system(state, agent_id)
    assert new_state.score == 0


def test_tile_rewardable_at_other_pos() -> None:
    state, agent_id = make_tile_state()
    # Add rewardable at (2,0), agent at (0,0)
    rewardable_id = 42
    state = replace(
        state,
        rewardable=state.rewardable.set(rewardable_id, Rewardable(reward=15)),
        position=state.position.set(rewardable_id, Position(2, 0)),
    )
    new_state = tile_reward_system(state, agent_id)
    assert new_state.score == 0


def test_tile_cost_at_other_pos() -> None:
    state, agent_id = make_tile_state()
    cost_id = 99
    state = replace(
        state,
        cost=state.cost.set(cost_id, Cost(amount=7)),
        position=state.position.set(cost_id, Position(2, 0)),
    )
    new_state = tile_cost_system(state, agent_id)
    assert new_state.score == 0


def test_tile_reward_system_multiple_agents() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2])
    agent2_id = 99
    # Add a second agent at a different pos (no rewardable there)
    state = replace(
        state,
        agent=state.agent.set(agent2_id, Agent()),
        position=state.position.set(agent2_id, Position(2, 0)),
    )
    # Agent2 should get no score, only agent1 should
    state1 = tile_reward_system(state, agent_id)
    state2 = tile_reward_system(state, agent2_id)
    assert state1.score == 10
    assert state2.score == 0


def test_tile_cost_system_multiple_agents() -> None:
    state, agent_id = make_tile_state(cost_ids=[3])
    agent2_id = 99
    state = replace(
        state,
        agent=state.agent.set(agent2_id, Agent()),
        position=state.position.set(agent2_id, Position(2, 0)),
    )
    state1 = tile_cost_system(state, agent_id)
    state2 = tile_cost_system(state, agent2_id)
    assert state1.score == -2
    assert state2.score == 0


def test_tile_reward_system_dead_and_missing_position() -> None:
    state, agent_id = make_tile_state(rewardable_ids=[2])
    state = replace(
        state,
        dead=state.dead.set(agent_id, Dead()),
        position=state.position.remove(agent_id),
    )
    new_state = tile_reward_system(state, agent_id)
    assert new_state.score == 0


def test_tile_cost_system_dead_and_missing_position() -> None:
    state, agent_id = make_tile_state(cost_ids=[3])
    state = replace(
        state,
        dead=state.dead.set(agent_id, Dead()),
        position=state.position.remove(agent_id),
    )
    new_state = tile_cost_system(state, agent_id)
    assert new_state.score == 0
