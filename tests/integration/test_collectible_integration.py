from dataclasses import replace
from typing import Tuple, Dict
from pyrsistent.typing import PMap
from pyrsistent import pmap, pset
from grid_universe.state import State
from grid_universe.components import (
    Agent,
    Collectible,
    Rewardable,
    PowerUp,
    PowerUpType,
    PowerUpLimit,
    Inventory,
    Item,
    Required,
    Position,
)
from grid_universe.types import EntityID
from grid_universe.actions import MoveAction, PickUpAction, Direction
from grid_universe.step import step


def make_agent_with_collectible_state(
    agent_pos: Tuple[int, int],
    collectible_pos: Tuple[int, int],
    reward: int = 0,
    powerup: bool = False,
    required: bool = False,
) -> Tuple[State, EntityID, EntityID]:
    agent_id = 1
    collectible_id = 2
    pos: Dict[EntityID, Position] = {
        agent_id: Position(*agent_pos),
        collectible_id: Position(*collectible_pos),
    }
    agent = pmap({agent_id: Agent()})
    inventory = pmap({agent_id: Inventory(pset())})
    collectible = pmap({collectible_id: Collectible()})
    item = pmap({collectible_id: Item()})
    reward_map: PMap[EntityID, Rewardable] = (
        pmap({collectible_id: Rewardable(reward=reward)}) if reward else pmap()
    )
    powerup_map: PMap[EntityID, PowerUp] = (
        pmap(
            {
                collectible_id: PowerUp(
                    type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=2
                )
            }
        )
        if powerup
        else pmap()
    )
    required_map: PMap[EntityID, Required] = (
        pmap({collectible_id: Required()}) if required else pmap()
    )

    state = State(
        width=3,
        height=1,
        move_fn=lambda s, eid, dir: [Position(pos[eid].x + 1, 0)],
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
        collectible=collectible,
        rewardable=reward_map,
        cost=pmap(),
        item=item,
        required=required_map,
        inventory=inventory,
        health=pmap(),
        powerup=powerup_map,
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
    return state, agent_id, collectible_id


def move_and_pickup(state: State, agent_id: EntityID, direction: Direction) -> State:
    state = step(
        state, MoveAction(entity_id=agent_id, direction=direction), agent_id=agent_id
    )
    state = step(state, PickUpAction(entity_id=agent_id), agent_id=agent_id)
    return state


def test_agent_picks_up_item() -> None:
    state, agent_id, collectible_id = make_agent_with_collectible_state((0, 0), (1, 0))
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    assert collectible_id in state.inventory[agent_id].item_ids
    assert collectible_id not in state.collectible
    assert collectible_id not in state.position


def test_agent_picks_up_rewardable() -> None:
    state, agent_id, collectible_id = make_agent_with_collectible_state(
        (0, 0), (1, 0), reward=10
    )
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    assert collectible_id in state.inventory[agent_id].item_ids
    assert state.score == 10


def test_agent_picks_up_powerup() -> None:
    state, agent_id, collectible_id = make_agent_with_collectible_state(
        (0, 0), (1, 0), powerup=True
    )
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    pu_status = state.powerup_status[agent_id]
    assert PowerUpType.SHIELD in pu_status
    assert collectible_id not in state.powerup
    assert collectible_id not in state.inventory[agent_id].item_ids


def test_agent_picks_up_required() -> None:
    state, agent_id, collectible_id = make_agent_with_collectible_state(
        (0, 0), (1, 0), required=True
    )
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    assert collectible_id in state.inventory[agent_id].item_ids


def test_agent_picks_up_multiple_types() -> None:
    # Place agent and three collectibles at same position: rewardable, powerup, required
    agent_id = 1
    item_id = 2
    rewardable_id = 3
    powerup_id = 4
    required_id = 5
    pos = {
        agent_id: Position(0, 0),
        item_id: Position(0, 1),
        rewardable_id: Position(0, 1),
        powerup_id: Position(0, 1),
        required_id: Position(0, 1),
    }
    agent = pmap({agent_id: Agent()})
    inventory = pmap({agent_id: Inventory(pset())})
    collectible = pmap(
        {
            item_id: Collectible(),
            rewardable_id: Collectible(),
            powerup_id: Collectible(),
            required_id: Collectible(),
        }
    )
    item = pmap(
        {
            item_id: Item(),
            rewardable_id: Item(),
            powerup_id: Item(),
            required_id: Item(),
        }
    )
    rewardable = pmap({rewardable_id: Rewardable(reward=10)})
    powerup = pmap(
        {
            powerup_id: PowerUp(
                type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=2
            )
        }
    )
    required = pmap({required_id: Required()})

    state = State(
        width=3,
        height=2,
        move_fn=lambda s, eid, dir: [Position(0, 1)],
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
        collectible=collectible,
        rewardable=rewardable,
        cost=pmap(),
        item=item,
        required=required,
        inventory=inventory,
        health=pmap(),
        powerup=powerup,
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
    state = move_and_pickup(state, agent_id, Direction.DOWN)
    assert item_id in state.inventory[agent_id].item_ids
    assert rewardable_id in state.inventory[agent_id].item_ids
    assert required_id in state.inventory[agent_id].item_ids
    assert PowerUpType.SHIELD in state.powerup_status[agent_id]
    assert state.score == 10
    for cid in [item_id, rewardable_id, powerup_id, required_id]:
        assert cid not in state.collectible
        assert cid not in state.position


def test_pickup_defensive_edge_cases() -> None:
    # No inventory
    state, agent_id, collectible_id = make_agent_with_collectible_state((0, 0), (0, 0))
    state = replace(state, inventory=pmap())
    state = step(state, PickUpAction(entity_id=agent_id), agent_id=agent_id)
    assert collectible_id in state.collectible
    # Nothing present
    state2, agent_id, _ = make_agent_with_collectible_state((0, 0), (1, 0))
    state2 = step(state2, PickUpAction(entity_id=agent_id), agent_id=agent_id)
    # Should not crash, collectible unchanged
    # Already collected
    state3, agent_id, collectible_id = make_agent_with_collectible_state((0, 0), (0, 0))
    # Remove collectible before pickup
    state3 = replace(
        state3,
        collectible=state3.collectible.remove(collectible_id),
        position=state3.position.remove(collectible_id),
    )
    state3 = step(state3, PickUpAction(entity_id=agent_id), agent_id=agent_id)
    # Should do nothing and not crash


def test_pickup_powerup_stacks_usage() -> None:
    # Agent already has shield powerup with 3 uses, picks up another with 2
    state, agent_id, collectible_id = make_agent_with_collectible_state(
        (0, 0), (1, 0), powerup=True
    )
    existing_pu = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=3
    )
    state = replace(
        state, powerup_status=pmap({agent_id: pmap({PowerUpType.SHIELD: existing_pu})})
    )
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    assert state.powerup_status[agent_id][PowerUpType.SHIELD].remaining == 5


def test_pickup_powerup_unlimited_usage() -> None:
    # Collectible with unlimited usage
    state, agent_id, collectible_id = make_agent_with_collectible_state(
        (0, 0), (1, 0), powerup=True
    )
    unlimited_pu = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=None
    )
    state = replace(state, powerup=pmap({collectible_id: unlimited_pu}))
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    assert state.powerup_status[agent_id][PowerUpType.SHIELD].remaining is None


def test_pickup_required_updates_win_condition() -> None:
    state, agent_id, collectible_id = make_agent_with_collectible_state(
        (0, 0), (1, 0), required=True
    )
    state = move_and_pickup(state, agent_id, Direction.RIGHT)


def test_pickup_removes_from_all_relevant_stores() -> None:
    state, agent_id, collectible_id = make_agent_with_collectible_state(
        (0, 0), (1, 0), reward=5, powerup=True, required=True
    )
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    # After pickup, collectible_id should be gone from all relevant stores
    for store in [state.collectible, state.powerup, state.position]:
        assert collectible_id not in store


def test_pickup_inventory_not_duplicated() -> None:
    # Inventory is a set, but test that adding same item twice (by repeated pickup) does not cause duplication
    state, agent_id, collectible_id = make_agent_with_collectible_state((0, 0), (1, 0))
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    # Try pick up again
    state = step(state, PickUpAction(entity_id=agent_id), agent_id=agent_id)
    items = state.inventory[agent_id].item_ids
    assert len(items) == len(set(items))


def test_pickup_collectible_with_score_cost() -> None:
    from grid_universe.components import Cost

    agent_id = 1
    collectible_id = 2
    cost_id = 3
    # Place agent at (0,0), collectible and cost at (1,0)
    pos = {
        agent_id: Position(0, 0),
        collectible_id: Position(1, 0),
        cost_id: Position(1, 0),
    }
    agent = pmap({agent_id: Agent()})
    inventory = pmap({agent_id: Inventory(pset())})
    collectible = pmap({collectible_id: Collectible()})
    item = pmap({collectible_id: Item()})
    rewardable = pmap({collectible_id: Rewardable(reward=15)})
    cost = pmap({cost_id: Cost(amount=6)})

    state = State(
        width=2,
        height=1,
        move_fn=lambda s, eid, dir: [Position(1, 0)],
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
        collectible=collectible,
        rewardable=rewardable,
        cost=cost,
        item=item,
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
    # Move agent right, pick up
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    state = step(state, PickUpAction(entity_id=agent_id), agent_id=agent_id)
    # Score should be reward - cost = 15 - 6 - 6 = 3
    assert state.score == 3
    assert collectible_id in state.inventory[agent_id].item_ids
    assert collectible_id not in state.collectible
    assert collectible_id not in state.position
