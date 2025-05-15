from typing import Tuple
from pyrsistent.typing import PMap
from ecs_maze.systems.collectible import collectible_system
from ecs_maze.components import (
    Agent,
    Inventory,
    Collectible,
    Item,
    Rewardable,
    PowerUp,
    PowerUpType,
    PowerUpLimit,
    Position,
    Required,
)
from ecs_maze.types import EntityID
from pyrsistent import pmap, pset
from ecs_maze.state import State


def make_collectible_state(
    agent_pos: Tuple[int, int],
    collectible_pos: Tuple[int, int],
    collectible_id: EntityID,
    collect_type: str = "item",
) -> Tuple[State, EntityID]:
    """
    Build a minimal state with an agent and one collectible of given type at the same position.
    `collect_type` can be "item", "rewardable", or "powerup".
    Returns (state, agent_id)
    """
    agent_id = 1
    pos = {
        agent_id: Position(*agent_pos),
        collectible_id: Position(*collectible_pos),
    }
    agent = pmap({agent_id: Agent()})
    inventory = pmap({agent_id: Inventory(pset())})
    collectible = pmap({collectible_id: Collectible()})
    item = pmap({collectible_id: Item()})

    rewardable: PMap[EntityID, Rewardable] = pmap()
    powerup: PMap[EntityID, PowerUp] = pmap()

    score = 0

    if collect_type == "rewardable":
        rewardable = pmap({collectible_id: Rewardable(reward=10)})
    if collect_type == "powerup":
        powerup = pmap(
            {
                collectible_id: PowerUp(
                    type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=2
                )
            }
        )

    state = State(
        width=3,
        height=1,
        move_fn=lambda s, eid, dir: [Position(s.position[eid].x + 1, 0)],
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
        required=pmap(),
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
        score=score,
        win=False,
        lose=False,
        message=None,
    )
    return state, agent_id


def test_pickup_normal_item() -> None:
    item_id = 2
    state, agent_id = make_collectible_state((0, 0), (0, 0), item_id, "item")
    new_state = collectible_system(state, agent_id)
    # Item should be in inventory
    assert item_id in new_state.inventory[agent_id].item_ids
    # Collectible should be removed from world
    assert item_id not in new_state.collectible
    assert item_id not in new_state.position


def test_pickup_rewardable_increases_score() -> None:
    item_id = 3
    state, agent_id = make_collectible_state((0, 0), (0, 0), item_id, "rewardable")
    new_state = collectible_system(state, agent_id)
    # Score should have increased
    assert new_state.score == 10
    # Item should be in inventory
    assert item_id in new_state.inventory[agent_id].item_ids


def test_pickup_powerup_grants_powerup_status() -> None:
    item_id = 4
    state, agent_id = make_collectible_state((0, 0), (0, 0), item_id, "powerup")
    new_state = collectible_system(state, agent_id)
    # Powerup should be granted to agent in powerup_status
    powerup_status = new_state.powerup_status[agent_id]
    assert PowerUpType.SHIELD in powerup_status
    powerup = powerup_status[PowerUpType.SHIELD]
    assert powerup.remaining == 2
    # Powerup entity is removed from the world
    assert item_id not in new_state.powerup
    # Item removed from inventory (since it's a powerup)


def test_pickup_multiple_collectibles_all_types() -> None:
    agent_id = 1
    item_id = 2
    rewardable_id = 3
    powerup_id = 4
    required_id = 5

    pos = {agent_id: Position(0, 0)}
    agent = pmap({agent_id: Agent()})
    inventory = pmap({agent_id: Inventory(pset())})
    collectible = {}
    item = {}
    rewardable = {}
    powerup = {}
    required = {}

    for cid in [item_id, rewardable_id, powerup_id, required_id]:
        pos[cid] = Position(0, 0)
        collectible[cid] = Collectible()
        item[cid] = Item()
    rewardable[rewardable_id] = Rewardable(reward=10)
    powerup[powerup_id] = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=2
    )
    required[required_id] = Required()

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
        cost=pmap(),
        item=pmap(item),
        required=pmap(required),
        inventory=inventory,
        health=pmap(),
        powerup=pmap(powerup),
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
    new_state = collectible_system(state, agent_id)
    # All should be out of world maps
    for i in [item_id, rewardable_id, powerup_id, required_id]:
        assert i not in new_state.collectible
        assert i not in new_state.position
    # Inventory contains items (except powerups)
    assert item_id in new_state.inventory[agent_id].item_ids
    assert rewardable_id in new_state.inventory[agent_id].item_ids
    assert required_id in new_state.inventory[agent_id].item_ids
    # Powerup is granted
    assert PowerUpType.SHIELD in new_state.powerup_status[agent_id]
    # Score increased
    assert new_state.score == 10


def test_pickup_no_inventory_does_nothing() -> None:
    agent_id = 1
    item_id = 2
    pos = {agent_id: Position(0, 0), item_id: Position(0, 0)}
    agent = pmap({agent_id: Agent()})
    collectible = pmap({item_id: Collectible()})
    item = pmap({item_id: Item()})

    state = State(
        width=2,
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
        collectible=collectible,
        rewardable=pmap(),
        cost=pmap(),
        item=item,
        required=pmap(),
        inventory=pmap(),  # No inventory for agent
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
    new_state = collectible_system(state, agent_id)
    # Collectible and item should be unchanged
    assert item_id in new_state.collectible
    assert item_id in new_state.item
    # No crash, inventory still missing
    assert agent_id not in new_state.inventory


def test_pickup_nothing_present_does_nothing() -> None:
    agent_id = 1
    agent = pmap({agent_id: Agent()})
    inventory = pmap({agent_id: Inventory(pset())})

    state = State(
        width=1,
        height=1,
        move_fn=lambda s, eid, dir: [],
        position=pmap({agent_id: Position(0, 0)}),
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
        collectible=pmap(),
        rewardable=pmap(),
        cost=pmap(),
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
    new_state = collectible_system(state, agent_id)
    assert new_state == state  # No change


def test_pickup_required_collectible() -> None:
    agent_id = 1
    req_id = 2
    pos = {agent_id: Position(0, 0), req_id: Position(0, 0)}
    agent = pmap({agent_id: Agent()})
    inventory = pmap({agent_id: Inventory(pset())})
    collectible = pmap({req_id: Collectible()})
    item = pmap({req_id: Item()})
    required = pmap({req_id: Required()})

    state = State(
        width=2,
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
        collectible=collectible,
        rewardable=pmap(),
        cost=pmap(),
        item=item,
        required=required,
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
    new_state = collectible_system(state, agent_id)
    assert req_id not in new_state.collectible
    assert req_id in new_state.inventory[agent_id].item_ids
    assert req_id not in new_state.position


def test_pickup_after_collectible_already_removed() -> None:
    agent_id = 1
    agent = pmap({agent_id: Agent()})
    inventory = pmap({agent_id: Inventory(pset([42]))})  # Already collected
    state = State(
        width=1,
        height=1,
        move_fn=lambda s, eid, dir: [],
        position=pmap({agent_id: Position(0, 0)}),
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
        collectible=pmap(),  # 42 already gone
        rewardable=pmap(),
        cost=pmap(),
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
    new_state = collectible_system(state, agent_id)
    # Should not crash or change the inventory
    assert new_state.inventory[agent_id].item_ids == pset([42])
