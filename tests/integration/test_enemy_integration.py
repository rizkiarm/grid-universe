from typing import Tuple, Dict
from dataclasses import replace
from pyrsistent import pmap, pset, PMap
from ecs_maze.state import State
from ecs_maze.types import EntityID
from ecs_maze.components import (
    Agent,
    Enemy,
    Inventory,
    Health,
    PowerUp,
    PowerUpType,
    PowerUpLimit,
    Position,
    Rewardable,
    Cost,
    Dead,
    Damage,
    LethalDamage,
    Collectible,
    Item,
)
from ecs_maze.actions import MoveAction, PickUpAction, Direction
from ecs_maze.step import step


def make_agent_enemy_state(
    agent_pos: Tuple[int, int] = (0, 0),
    enemy_pos: Tuple[int, int] = (1, 0),
    agent_health: int = 10,
    enemy_damage: int = 3,
    lethal: bool = False,
    powerup: Dict[PowerUpType, PowerUp] = {},
) -> Tuple[State, EntityID, EntityID]:
    agent_id: EntityID = 1
    enemy_id: EntityID = 2
    pos: Dict[EntityID, Position] = {
        agent_id: Position(*agent_pos),
        enemy_id: Position(*enemy_pos),
    }
    agent: PMap[EntityID, Agent] = pmap({agent_id: Agent()})
    inventory: PMap[EntityID, Inventory] = pmap({agent_id: Inventory(pset())})
    health: PMap[EntityID, Health] = pmap(
        {agent_id: Health(health=agent_health, max_health=agent_health)}
    )
    enemy: PMap[EntityID, Enemy] = pmap({enemy_id: Enemy()})
    damage: PMap[EntityID, Damage] = (
        pmap({enemy_id: Damage(amount=enemy_damage)}) if not lethal else pmap()
    )
    lethal_damage: PMap[EntityID, LethalDamage] = (
        pmap({enemy_id: LethalDamage()}) if lethal else pmap()
    )
    powerup_status: PMap[EntityID, PMap[PowerUpType, PowerUp]] = (
        pmap({agent_id: pmap(powerup)}) if powerup else pmap()
    )

    state: State = State(
        width=3,
        height=1,
        move_fn=lambda s, eid, dir: [Position(1, 0)],
        position=pmap(pos),
        agent=agent,
        enemy=enemy,
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
        health=health,
        powerup=pmap(),
        powerup_status=powerup_status,
        floor=pmap(),
        blocking=pmap(),
        dead=pmap(),
        moving=pmap(),
        hazard=pmap(),
        collidable=pmap(),
        damage=damage,
        lethal_damage=lethal_damage,
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
    return state, agent_id, enemy_id


def test_agent_takes_damage_from_enemy() -> None:
    state, agent_id, _ = make_agent_enemy_state()
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 7


def test_agent_dies_from_lethal_enemy() -> None:
    state, agent_id, _ = make_agent_enemy_state(lethal=True)
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert agent_id in state.dead


def test_agent_with_shield_blocks_enemy() -> None:
    powerup: Dict[PowerUpType, PowerUp] = {
        PowerUpType.SHIELD: PowerUp(
            type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=1
        )
    }
    state, agent_id, _ = make_agent_enemy_state(powerup=powerup)
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 10
    assert PowerUpType.SHIELD not in state.powerup_status[agent_id]


def test_agent_with_ghost_immune_to_enemy() -> None:
    powerup: Dict[PowerUpType, PowerUp] = {
        PowerUpType.GHOST: PowerUp(
            type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=2
        )
    }
    state, agent_id, _ = make_agent_enemy_state(powerup=powerup)
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 10
    assert PowerUpType.GHOST in state.powerup_status[agent_id]


def test_multiple_enemies_damage_accumulates() -> None:
    state, agent_id, enemy1_id = make_agent_enemy_state()
    enemy2_id: EntityID = 3
    state2 = replace(
        state,
        enemy=state.enemy.set(enemy2_id, Enemy()),
        position=state.position.set(enemy2_id, Position(1, 0)),
        damage=state.damage.set(enemy2_id, Damage(amount=5)),
    )
    state2 = step(
        state2,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state2.health[agent_id].health == 2


def test_shield_blocks_only_one_enemy() -> None:
    powerup: Dict[PowerUpType, PowerUp] = {
        PowerUpType.SHIELD: PowerUp(
            type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=1
        )
    }
    state, agent_id, enemy1_id = make_agent_enemy_state(powerup=powerup)
    enemy2_id: EntityID = 3
    state2 = replace(
        state,
        enemy=state.enemy.set(enemy2_id, Enemy()),
        position=state.position.set(enemy2_id, Position(1, 0)),
        damage=state.damage.set(enemy2_id, Damage(amount=5)),
    )
    state2 = step(
        state2,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    rem_health: int = state2.health[agent_id].health
    assert rem_health in (7, 5)


def test_enemy_has_both_damage_and_lethal() -> None:
    state, agent_id, enemy_id = make_agent_enemy_state()
    state2 = replace(
        state, lethal_damage=state.lethal_damage.set(enemy_id, LethalDamage())
    )
    state2 = step(
        state2,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert agent_id in state2.dead


def test_lethal_and_nonlethal_enemy_mix() -> None:
    state, agent_id, enemy1_id = make_agent_enemy_state()
    enemy2_id: EntityID = 3
    state2 = replace(
        state,
        enemy=state.enemy.set(enemy2_id, Enemy()),
        position=state.position.set(enemy2_id, Position(1, 0)),
        damage=state.damage.set(enemy2_id, Damage(amount=5)),
        lethal_damage=state.lethal_damage.set(enemy1_id, LethalDamage()),
    )
    state2 = step(
        state2,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert agent_id in state2.dead


def test_enemy_collision_with_powerup_stack() -> None:
    powerup: Dict[PowerUpType, PowerUp] = {
        PowerUpType.GHOST: PowerUp(
            type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=2
        ),
        PowerUpType.SHIELD: PowerUp(
            type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=1
        ),
    }
    state, agent_id, _ = make_agent_enemy_state(powerup=powerup)
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 10
    assert PowerUpType.SHIELD in state.powerup_status[agent_id]


def test_no_enemy_no_effect() -> None:
    agent_id: EntityID = 1
    agent: PMap[EntityID, Agent] = pmap({agent_id: Agent()})
    health: PMap[EntityID, Health] = pmap({agent_id: Health(health=10, max_health=10)})
    state: State = State(
        width=2,
        height=1,
        move_fn=lambda s, eid, dir: [Position(1, 0)],
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
        inventory=pmap(),
        health=health,
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
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 10


def test_agent_dead_no_further_enemy_effect() -> None:
    state, agent_id, _ = make_agent_enemy_state()
    dead: PMap[EntityID, Dead] = pmap({agent_id: Dead()})
    state2 = replace(state, dead=dead)
    state2 = step(
        state2,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state2.dead[agent_id]
    assert state2.health[agent_id].health == 10


def test_agent_enemy_no_health_component() -> None:
    state, agent_id, _ = make_agent_enemy_state()
    state2 = replace(state, health=pmap())
    state2 = step(
        state2,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert agent_id not in state2.health


def test_enemy_with_zero_damage() -> None:
    state, agent_id, enemy_id = make_agent_enemy_state(enemy_damage=0)
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 10


def test_enemy_with_negative_damage() -> None:
    import pytest

    with pytest.raises(ValueError):
        state, agent_id, enemy_id = make_agent_enemy_state(enemy_damage=-5)
        state = step(
            state,
            MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
            agent_id=agent_id,
        )


def test_agent_collides_with_enemy_and_hazard() -> None:
    from ecs_maze.components import Hazard, HazardType

    state, agent_id, enemy_id = make_agent_enemy_state()
    hazard_id: EntityID = 5
    state2 = replace(
        state,
        hazard=state.hazard.set(hazard_id, Hazard(type=HazardType.LAVA)),
        position=state.position.set(hazard_id, Position(1, 0)),
    )
    state2 = step(
        state2,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert agent_id in state2.dead or state2.health[agent_id].health < 10


def test_agent_collides_with_enemy_and_collectible() -> None:
    state, agent_id, enemy_id = make_agent_enemy_state()
    collectible_id: EntityID = 4
    state2 = replace(
        state,
        collectible=state.collectible.set(collectible_id, Collectible()),
        item=state.item.set(collectible_id, Item()),
        rewardable=state.rewardable.set(collectible_id, Rewardable(reward=7)),
        position=state.position.set(collectible_id, Position(1, 0)),
    )
    # Move agent onto tile
    state2 = step(
        state2,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    # Pick up collectible
    state2 = step(state2, PickUpAction(entity_id=agent_id), agent_id=agent_id)
    assert collectible_id in state2.inventory[agent_id].item_ids
    # Check health after move step (enemy effect)
    assert state2.health[agent_id].health == 4


def test_agent_moves_onto_enemy_with_cost() -> None:
    state, agent_id, enemy_id = make_agent_enemy_state()
    cost_id: EntityID = 6
    state2 = replace(
        state,
        cost=state.cost.set(cost_id, Cost(amount=2)),
        position=state.position.set(cost_id, Position(1, 0)),
    )
    state2 = step(
        state2,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state2.health[agent_id].health == 7
    assert state2.score == -2
