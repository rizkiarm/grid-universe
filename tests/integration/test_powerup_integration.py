from dataclasses import replace
from typing import Dict, Tuple, Optional
from pyrsistent import pmap, pset, PMap

from grid_universe.moves import default_move_fn
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.components import (
    Agent,
    Inventory,
    PowerUp,
    PowerUpType,
    PowerUpLimit,
    Position,
    Collectible,
    Item,
    Health,
    Wall,
    Hazard,
    HazardType,
    Dead,
    Damage,
)
from grid_universe.actions import PickUpAction, MoveAction, Direction, WaitAction
from grid_universe.step import step


def make_agent_with_powerup_collectible(
    agent_pos: Tuple[int, int],
    collectible_pos: Tuple[int, int],
    powerup: PowerUp,
    agent_id: EntityID = 1,
    collectible_id: EntityID = 2,
    agent_health: int = 10,
) -> Tuple[State, EntityID, EntityID]:
    pos: Dict[EntityID, Position] = {
        agent_id: Position(*agent_pos),
        collectible_id: Position(*collectible_pos),
    }
    agent: PMap[EntityID, Agent] = pmap({agent_id: Agent()})
    inventory: PMap[EntityID, Inventory] = pmap({agent_id: Inventory(pset())})
    health: PMap[EntityID, Health] = pmap(
        {agent_id: Health(health=agent_health, max_health=agent_health)}
    )
    collectible: PMap[EntityID, Collectible] = pmap({collectible_id: Collectible()})
    item: PMap[EntityID, Item] = pmap({collectible_id: Item()})
    powerup_map: PMap[EntityID, PowerUp] = pmap({collectible_id: powerup})

    state: State = State(
        width=4,
        height=1,
        move_fn=default_move_fn,
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
        inventory=inventory,
        health=health,
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


def get_agent_powerup(
    state: State, agent_id: EntityID, pu_type: PowerUpType
) -> Optional[PowerUp]:
    if agent_id in state.powerup_status:
        pu_map: PMap[PowerUpType, PowerUp] = state.powerup_status[agent_id]
        return pu_map.get(pu_type, None)
    return None


def wait(state: State, agent_id: EntityID, n: int = 1) -> State:
    for _ in range(n):
        state = step(state, WaitAction(entity_id=agent_id), agent_id=agent_id)
    return state


def test_agent_picks_up_usage_limited_powerup() -> None:
    powerup: PowerUp = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=2
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), powerup)
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    pu = get_agent_powerup(state, agent_id, PowerUpType.SHIELD)
    assert pu is not None
    assert pu.remaining == 2
    assert len(state.powerup) == 0


def test_agent_picks_up_duration_limited_powerup() -> None:
    powerup: PowerUp = PowerUp(
        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=3
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), powerup)
    state = move_and_pickup(
        state, agent_id, Direction.RIGHT
    )  # first pickup, no decrement
    state = move_and_pickup(state, agent_id, Direction.RIGHT)  # 2 turns
    pu = get_agent_powerup(state, agent_id, PowerUpType.GHOST)
    assert pu is not None
    assert pu.remaining == 1


def test_agent_collects_and_stacks_same_powerup() -> None:
    pu1: PowerUp = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=2
    )
    pu2: PowerUp = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=3
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu1)
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    collectible_id2: EntityID = 99
    state = replace(
        state,
        position=state.position.set(collectible_id2, Position(2, 0)),
        collectible=state.collectible.set(collectible_id2, Collectible()),
        item=state.item.set(collectible_id2, Item()),
        powerup=state.powerup.set(collectible_id2, pu2),
    )
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    pu = get_agent_powerup(state, agent_id, PowerUpType.SHIELD)
    assert pu is not None
    assert pu.remaining == 5


def test_agent_collects_different_powerups() -> None:
    pu1: PowerUp = PowerUp(
        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=4
    )
    pu2: PowerUp = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=2
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu1)
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    collectible_id2: EntityID = 42
    state = replace(
        state,
        position=state.position.set(collectible_id2, Position(2, 0)),
        collectible=state.collectible.set(collectible_id2, Collectible()),
        item=state.item.set(collectible_id2, Item()),
        powerup=state.powerup.set(collectible_id2, pu2),
    )
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    pu_ghost = get_agent_powerup(state, agent_id, PowerUpType.GHOST)
    pu_shield = get_agent_powerup(state, agent_id, PowerUpType.SHIELD)
    assert pu_ghost is not None and pu_ghost.remaining == 2
    assert pu_shield is not None and pu_shield.remaining == 2


def test_powerup_entity_removed_on_pickup() -> None:
    powerup: PowerUp = PowerUp(
        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=1
    )
    state, agent_id, collectible_id = make_agent_with_powerup_collectible(
        (0, 0), (1, 0), powerup
    )
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    assert collectible_id not in state.powerup


def test_duration_powerup_ticks_and_expires() -> None:
    powerup: PowerUp = PowerUp(
        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=2
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), powerup)
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    state = wait(state, agent_id)
    pu = get_agent_powerup(state, agent_id, PowerUpType.GHOST)
    assert pu is not None and pu.remaining == 1
    state = wait(state, agent_id)
    pu = get_agent_powerup(state, agent_id, PowerUpType.GHOST)
    assert pu is None


def test_unlimited_powerup_does_not_expire() -> None:
    pu1: PowerUp = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=None
    )
    pu2: PowerUp = PowerUp(
        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=None
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu1)
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    collectible_id2: EntityID = 99
    state = replace(
        state,
        position=state.position.set(collectible_id2, Position(2, 0)),
        collectible=state.collectible.set(collectible_id2, Collectible()),
        item=state.item.set(collectible_id2, Item()),
        powerup=state.powerup.set(collectible_id2, pu2),
    )
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    state = wait(state, agent_id, n=5)
    assert get_agent_powerup(state, agent_id, PowerUpType.SHIELD) is not None
    assert get_agent_powerup(state, agent_id, PowerUpType.GHOST) is not None


def test_powerup_removed_after_expiry() -> None:
    pu: PowerUp = PowerUp(
        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=1
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu)
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    state = wait(state, agent_id)
    assert get_agent_powerup(state, agent_id, PowerUpType.GHOST) is None


def test_multiple_powerups_tick_independently() -> None:
    pu1: PowerUp = PowerUp(
        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=4
    )
    pu2: PowerUp = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.DURATION, remaining=3
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu1)
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    collectible_id2: EntityID = 998
    state = replace(
        state,
        position=state.position.set(collectible_id2, Position(2, 0)),
        collectible=state.collectible.set(collectible_id2, Collectible()),
        item=state.item.set(collectible_id2, Item()),
        powerup=state.powerup.set(collectible_id2, pu2),
    )
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    state = wait(state, agent_id)
    pu1_current = get_agent_powerup(state, agent_id, PowerUpType.GHOST)
    pu2_current = get_agent_powerup(state, agent_id, PowerUpType.SHIELD)
    assert pu1_current is not None and pu1_current.remaining == 1
    assert pu2_current is not None and pu2_current.remaining == 2


def test_powerup_with_zero_negative_duration_or_uses_not_added() -> None:
    pu: PowerUp = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=0
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu)
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    state = wait(state, agent_id)
    res = get_agent_powerup(state, agent_id, PowerUpType.SHIELD)
    assert res is None

    pu_neg: PowerUp = PowerUp(
        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=-2
    )
    state2, agent_id2, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu_neg)
    state2 = move_and_pickup(state2, agent_id2, Direction.RIGHT)
    state2 = wait(state2, agent_id2)
    res2 = get_agent_powerup(state2, agent_id2, PowerUpType.GHOST)
    assert res2 is None


def test_powerup_effect_on_pickup_turn() -> None:
    pu: PowerUp = PowerUp(
        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=2
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu)
    wall_id: EntityID = 50
    state = replace(
        state,
        wall=state.wall.set(wall_id, Wall()),
        position=state.position.set(wall_id, Position(2, 0)),
    )
    # Pick up powerup at (1, 0)
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    # Now agent tries to move through wall at (2,0)
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.position[agent_id] == Position(2, 0)


def test_powerup_effect_removes_after_expiry() -> None:
    pu: PowerUp = PowerUp(
        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=1
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu)
    wall_id: EntityID = 101
    state = replace(
        state,
        wall=state.wall.set(wall_id, Wall()),
        position=state.position.set(wall_id, Position(2, 0)),
    )
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    # Wait for expiry
    state = wait(state, agent_id)
    # Now agent tries to move through wall at (2,0) (should be blocked)
    prev_pos = state.position[agent_id]
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.position[agent_id] == prev_pos


def test_powerup_entity_not_collectible_not_picked_up() -> None:
    pu: PowerUp = PowerUp(
        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=2
    )
    state, agent_id, collectible_id = make_agent_with_powerup_collectible(
        (0, 0), (1, 0), pu
    )
    # Remove collectible marker before pickup
    state = replace(state, collectible=state.collectible.remove(collectible_id))
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    state = step(state, PickUpAction(entity_id=agent_id), agent_id=agent_id)
    # Agent should not have the powerup
    assert get_agent_powerup(state, agent_id, PowerUpType.GHOST) is None
    # Powerup should still exist in the world
    assert collectible_id in state.powerup


def test_usage_powerup_consumed_on_hazard() -> None:
    # Agent with usage-limited shield encounters hazard, shield is consumed
    pu: PowerUp = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=1
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu)
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    hazard_id: EntityID = 99
    state = replace(
        state,
        hazard=state.hazard.set(hazard_id, Hazard(type=HazardType.LAVA)),
        position=state.position.set(hazard_id, Position(2, 0)),
        damage=state.damage.set(hazard_id, Damage(amount=5)),
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    # Shield should be gone after use
    assert get_agent_powerup(state, agent_id, PowerUpType.SHIELD) is None


def test_hazard_immunity_blocks_hazard() -> None:
    pu: PowerUp = PowerUp(
        type=PowerUpType.HAZARD_IMMUNITY, limit=PowerUpLimit.DURATION, remaining=2
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu)
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    hazard_id: EntityID = 77
    state = replace(
        state,
        hazard=state.hazard.set(hazard_id, Hazard(type=HazardType.LAVA)),
        position=state.position.set(hazard_id, Position(2, 0)),
        damage=state.damage.set(hazard_id, Damage(amount=5)),
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 10


def test_ghost_powerup_ignores_blocking() -> None:
    pu: PowerUp = PowerUp(
        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=2
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu)
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    wall_id: EntityID = 88
    state = replace(
        state,
        wall=state.wall.set(wall_id, Wall()),
        position=state.position.set(wall_id, Position(2, 0)),
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.position[agent_id] == Position(2, 0)


def test_double_speed_powerup_moves_agent_twice() -> None:
    pu: PowerUp = PowerUp(
        type=PowerUpType.DOUBLE_SPEED, limit=PowerUpLimit.DURATION, remaining=3
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu)
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    assert state.position[agent_id] == Position(1, 0)
    # The next move should move agent two steps right
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.position[agent_id] == Position(3, 0)


def test_powerup_status_on_agent_death() -> None:
    pu: PowerUp = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=2
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu)
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    state = replace(state, dead=state.dead.set(agent_id, Dead()))
    assert get_agent_powerup(state, agent_id, PowerUpType.SHIELD) is not None


def test_powerup_stack_with_unlimited_and_limited() -> None:
    pu_unlimited: PowerUp = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=None
    )
    pu_limited: PowerUp = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=2
    )
    state, agent_id, _ = make_agent_with_powerup_collectible(
        (0, 0), (1, 0), pu_unlimited
    )
    state = move_and_pickup(state, agent_id, Direction.RIGHT)  # 2 steps
    collectible_id2: EntityID = 600
    state = replace(
        state,
        position=state.position.set(collectible_id2, Position(2, 0)),
        collectible=state.collectible.set(collectible_id2, Collectible()),
        item=state.item.set(collectible_id2, Item()),
        powerup=state.powerup.set(collectible_id2, pu_limited),
    )
    state = move_and_pickup(state, agent_id, Direction.RIGHT)  # 2 steps
    pu_status = get_agent_powerup(state, agent_id, PowerUpType.SHIELD)
    assert pu_status is not None and pu_status.remaining is None


def test_powerup_effect_order_with_multiple_powerups() -> None:
    # GHOST should take precedence over SHIELD for hazard
    pu_ghost: PowerUp = PowerUp(
        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=2
    )
    pu_shield: PowerUp = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=2
    )
    state, agent_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu_ghost)
    state = move_and_pickup(state, agent_id, Direction.RIGHT)
    # Add shield directly to agent's powerup_status
    pu_map: PMap[PowerUpType, PowerUp] = state.powerup_status[agent_id].set(
        PowerUpType.SHIELD, pu_shield
    )
    state = replace(state, powerup_status=state.powerup_status.set(agent_id, pu_map))
    hazard_id: EntityID = 400
    state = replace(
        state,
        hazard=state.hazard.set(hazard_id, Hazard(type=HazardType.LAVA)),
        position=state.position.set(hazard_id, Position(2, 0)),
        damage=state.damage.set(hazard_id, Damage(amount=3)),
        health=state.health.set(agent_id, Health(health=5, max_health=5)),
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    # GHOST blocks hazard, shield should not be consumed
    assert get_agent_powerup(state, agent_id, PowerUpType.SHIELD) is not None
    assert state.health[agent_id].health == 5


def test_multiple_agents_powerup_is_independent() -> None:
    pu1: PowerUp = PowerUp(
        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=3
    )
    pu2: PowerUp = PowerUp(
        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=1
    )
    # Agent 1
    state, agent1_id, _ = make_agent_with_powerup_collectible((0, 0), (1, 0), pu1)
    state = move_and_pickup(
        state, agent1_id, Direction.RIGHT
    )  # 2 steps, pu1 just added in second step
    # Agent 2
    agent2_id: EntityID = 22
    state = replace(
        state,
        agent=state.agent.set(agent2_id, Agent()),
        inventory=state.inventory.set(agent2_id, Inventory(pset())),
        health=state.health.set(agent2_id, Health(health=10, max_health=10)),
        position=state.position.set(agent2_id, Position(2, 0)),
    )
    collectible_id2: EntityID = 23
    state = replace(
        state,
        position=state.position.set(collectible_id2, Position(3, 0)),
        collectible=state.collectible.set(collectible_id2, Collectible()),
        item=state.item.set(collectible_id2, Item()),
        powerup=state.powerup.set(collectible_id2, pu2),
    )
    state = move_and_pickup(
        state, agent2_id, Direction.RIGHT
    )  # 2 steps, pu2 just added in second step
    pu_agent1 = get_agent_powerup(state, agent1_id, PowerUpType.GHOST)
    pu_agent2 = get_agent_powerup(state, agent2_id, PowerUpType.SHIELD)
    assert pu_agent1 is not None and pu_agent1.remaining == 1
    assert pu_agent2 is not None and pu_agent2.remaining == 1
