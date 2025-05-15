from dataclasses import replace
from typing import Optional
from ecs_maze.systems.powerup import powerup_tick_system
from ecs_maze.components import Agent, PowerUp, PowerUpType, PowerUpLimit, Inventory
from ecs_maze.types import EntityID
from pyrsistent import PMap, pmap, pset
from ecs_maze.state import State
from ecs_maze.utils.powerup import use_powerup_if_present, is_powerup_active
from ecs_maze.utils.collectible import grant_powerups_on_collect


def make_powerup_state(
    powerups_by_type: dict[PowerUpType, tuple[PowerUpLimit, Optional[int]]],
    agent_id: EntityID = 1,
) -> tuple[State, EntityID]:
    """Helper: Build a state with a dict of {PowerUpType: (limit, remaining)} for one agent."""
    pu_dict = {
        pu_type: PowerUp(type=pu_type, limit=limit, remaining=remaining)
        for pu_type, (limit, remaining) in powerups_by_type.items()
    }
    agent = pmap({agent_id: Agent()})
    powerup_status = pmap({agent_id: pmap(pu_dict)})
    state = State(
        width=1,
        height=1,
        move_fn=lambda s, eid, dir: [],
        position=pmap(),
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
        inventory=pmap(),
        health=pmap(),
        powerup=pmap(),
        powerup_status=powerup_status,
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


def test_duration_powerup_ticks_down_and_expires() -> None:
    state, agent_id = make_powerup_state(
        {PowerUpType.SHIELD: (PowerUpLimit.DURATION, 2)}
    )
    new_state = powerup_tick_system(state)
    pu_status = new_state.powerup_status[agent_id]
    assert pu_status[PowerUpType.SHIELD].remaining == 1
    new_state2 = powerup_tick_system(new_state)
    pu_status2 = new_state2.powerup_status[agent_id]
    assert PowerUpType.SHIELD not in pu_status2


def test_usage_powerup_does_not_tick() -> None:
    state, agent_id = make_powerup_state({PowerUpType.SHIELD: (PowerUpLimit.USAGE, 2)})
    new_state = powerup_tick_system(state)
    pu_status = new_state.powerup_status[agent_id]
    assert pu_status[PowerUpType.SHIELD].remaining == 2  # Unchanged


def test_powerup_with_unlimited_duration_does_not_expire() -> None:
    state, agent_id = make_powerup_state(
        {PowerUpType.DOUBLE_SPEED: (PowerUpLimit.DURATION, None)}
    )
    new_state = powerup_tick_system(state)
    pu_status = new_state.powerup_status[agent_id]
    assert pu_status[PowerUpType.DOUBLE_SPEED].remaining is None


def test_powerup_with_unlimited_usage_does_not_expire() -> None:
    state, agent_id = make_powerup_state(
        {PowerUpType.GHOST: (PowerUpLimit.USAGE, None)}
    )
    new_state = powerup_tick_system(state)
    pu_status = new_state.powerup_status[agent_id]
    assert pu_status[PowerUpType.GHOST].remaining is None


def test_zero_and_negative_duration_powerup_expires_immediately() -> None:
    # Zero remaining
    state, agent_id = make_powerup_state(
        {PowerUpType.HAZARD_IMMUNITY: (PowerUpLimit.DURATION, 0)}
    )
    new_state = powerup_tick_system(state)
    pu_status = new_state.powerup_status[agent_id]
    assert PowerUpType.HAZARD_IMMUNITY not in pu_status

    # Negative remaining
    state, agent_id = make_powerup_state(
        {PowerUpType.HAZARD_IMMUNITY: (PowerUpLimit.DURATION, -1)}
    )
    new_state = powerup_tick_system(state)
    pu_status = new_state.powerup_status[agent_id]
    assert PowerUpType.HAZARD_IMMUNITY not in pu_status


def test_multiple_powerups_tick_independently() -> None:
    state, agent_id = make_powerup_state(
        {
            PowerUpType.SHIELD: (PowerUpLimit.DURATION, 1),
            PowerUpType.GHOST: (PowerUpLimit.DURATION, 3),
            PowerUpType.DOUBLE_SPEED: (PowerUpLimit.USAGE, 2),
        }
    )
    new_state = powerup_tick_system(state)
    pu_status = new_state.powerup_status[agent_id]
    assert PowerUpType.SHIELD not in pu_status  # SHIELD should have expired
    assert pu_status[PowerUpType.GHOST].remaining == 2  # GHOST should tick down
    assert pu_status[PowerUpType.DOUBLE_SPEED].remaining == 2  # DOUBLE_SPEED unchanged


def test_no_powerups_no_error() -> None:
    agent = pmap({1: Agent()})
    powerup_status: PMap[EntityID, PMap[PowerUpType, PowerUp]] = pmap({1: pmap({})})
    state = State(
        width=1,
        height=1,
        move_fn=lambda s, eid, dir: [],
        position=pmap(),
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
        inventory=pmap(),
        health=pmap(),
        powerup=pmap(),
        powerup_status=powerup_status,
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
    new_state = powerup_tick_system(state)
    assert new_state.powerup_status[1] == pmap({})


def test_multiple_agents_powerup_tick() -> None:
    # Agent 1 with SHIELD, Agent 2 with GHOST
    state1, agent1 = make_powerup_state(
        {PowerUpType.SHIELD: (PowerUpLimit.DURATION, 2)}, agent_id=1
    )
    agent2 = 2
    agent_map = state1.agent.set(agent2, Agent())
    pu_map2 = {
        PowerUpType.GHOST: PowerUp(
            type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=3
        )
    }
    powerup_status2 = state1.powerup_status.set(agent2, pmap(pu_map2))
    state = State(
        width=1,
        height=1,
        move_fn=state1.move_fn,
        position=state1.position,
        agent=agent_map,
        enemy=state1.enemy,
        box=state1.box,
        pushable=state1.pushable,
        wall=state1.wall,
        door=state1.door,
        locked=state1.locked,
        portal=state1.portal,
        exit=state1.exit,
        key=state1.key,
        collectible=state1.collectible,
        rewardable=state1.rewardable,
        cost=state1.cost,
        item=state1.item,
        required=state1.required,
        inventory=state1.inventory,
        health=state1.health,
        powerup=state1.powerup,
        powerup_status=powerup_status2,
        floor=state1.floor,
        blocking=state1.blocking,
        dead=state1.dead,
        moving=state1.moving,
        hazard=state1.hazard,
        collidable=state1.collidable,
        damage=state1.damage,
        lethal_damage=state1.lethal_damage,
        turn=state1.turn,
        score=state1.score,
        win=state1.win,
        lose=state1.lose,
        message=state1.message,
    )
    new_state = powerup_tick_system(state)
    assert new_state.powerup_status[1][PowerUpType.SHIELD].remaining == 1
    assert new_state.powerup_status[2][PowerUpType.GHOST].remaining == 2


def test_powerup_tick_no_agents():
    # Empty state, no agents or powerup_status at all
    state = State(
        width=1,
        height=1,
        move_fn=lambda s, eid, dir: [],
        position=pmap(),
        agent=pmap(),
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
        inventory=pmap(),
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
    new_state = powerup_tick_system(state)
    assert new_state.powerup_status == pmap()


def test_stack_usage_powerup():
    # Agent has SHIELD powerup in status with 3 uses (simulate already has)
    state, agent_id = make_powerup_state({})
    # Agent already has SHIELD with 3
    status_map = state.powerup_status[agent_id].set(
        PowerUpType.SHIELD,
        PowerUp(type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=3),
    )

    # Collected powerup entity
    collected_eid = 99
    powerup_store = pmap(
        {
            collected_eid: PowerUp(
                type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=2
            )
        }
    )
    inv = Inventory(item_ids=pset([collected_eid]))

    # Run stacking logic
    new_inv, new_powerup_store, new_status = grant_powerups_on_collect(
        [collected_eid], agent_id, inv, powerup_store, pmap({agent_id: status_map})
    )

    assert new_status[agent_id][PowerUpType.SHIELD].remaining == 5  # 3+2
    assert collected_eid not in new_powerup_store
    assert collected_eid not in new_inv.item_ids


def test_unlimited_usage_not_removed():
    state, agent_id = make_powerup_state(
        {PowerUpType.GHOST: (PowerUpLimit.USAGE, None)}
    )
    pu_status = state.powerup_status
    for _ in range(5):
        used, pu_status = use_powerup_if_present(pu_status, agent_id, PowerUpType.GHOST)
        assert used
        assert PowerUpType.GHOST in pu_status[agent_id]


def test_usage_powerup_removed_on_exhaust():
    state, agent_id = make_powerup_state({PowerUpType.SHIELD: (PowerUpLimit.USAGE, 1)})
    pu_status = state.powerup_status
    used, pu_status = use_powerup_if_present(pu_status, agent_id, PowerUpType.SHIELD)
    assert used
    assert PowerUpType.SHIELD not in pu_status[agent_id]


def test_is_powerup_active():
    state, agent_id = make_powerup_state({PowerUpType.SHIELD: (PowerUpLimit.USAGE, 3)})
    assert is_powerup_active(state, agent_id, PowerUpType.SHIELD)
    # Remove shield
    new_state = replace(
        state, powerup_status=state.powerup_status.set(agent_id, pmap({}))
    )
    assert not is_powerup_active(new_state, agent_id, PowerUpType.SHIELD)
