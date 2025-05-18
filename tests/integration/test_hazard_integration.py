from dataclasses import replace
from typing import Dict, Tuple, Optional
from pyrsistent import pmap, pset, PMap
import pytest

from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.components import (
    Agent,
    Inventory,
    Health,
    Position,
    Hazard,
    HazardType,
    PowerUp,
    PowerUpType,
    PowerUpLimit,
    Dead,
    Damage,
    LethalDamage,
)
from grid_universe.actions import MoveAction, Direction
from grid_universe.step import step


# --- Utility: Setup agent + hazard state ---
def make_agent_hazard_state(
    agent_pos: Tuple[int, int] = (0, 0),
    hazard_pos: Tuple[int, int] = (1, 0),
    agent_health: int = 10,
    hazard_damage: int = 3,
    hazard_type: HazardType = HazardType.LAVA,
    lethal: bool = False,
    powerup: Optional[Dict[PowerUpType, PowerUp]] = None,
    unlimited_powerup: bool = False,
) -> Tuple[State, EntityID, EntityID]:
    agent_id: EntityID = 1
    hazard_id: EntityID = 2
    pos: Dict[EntityID, Position] = {
        agent_id: Position(*agent_pos),
        hazard_id: Position(*hazard_pos),
    }
    agent: PMap[EntityID, Agent] = pmap({agent_id: Agent()})
    inventory: PMap[EntityID, Inventory] = pmap({agent_id: Inventory(pset())})
    health: PMap[EntityID, Health] = pmap(
        {agent_id: Health(health=agent_health, max_health=agent_health)}
    )
    hazard: PMap[EntityID, Hazard] = pmap({hazard_id: Hazard(type=hazard_type)})
    damage: PMap[EntityID, Damage] = (
        pmap({hazard_id: Damage(amount=hazard_damage)}) if not lethal else pmap()
    )
    lethal_damage: PMap[EntityID, LethalDamage] = (
        pmap({hazard_id: LethalDamage()}) if lethal else pmap()
    )
    powerup_status: PMap[EntityID, PMap[PowerUpType, PowerUp]] = (
        pmap({agent_id: pmap(powerup)}) if powerup is not None else pmap()
    )
    if unlimited_powerup and powerup is not None:
        # Set all powerups in dict to have remaining=None
        unlimited: Dict[PowerUpType, PowerUp] = {
            k: PowerUp(type=v.type, limit=v.limit, remaining=None)
            for k, v in powerup.items()
        }
        powerup_status = pmap({agent_id: pmap(unlimited)})

    state: State = State(
        width=3,
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
        hazard=hazard,
        collidable=pmap(),
        damage=damage,
        lethal_damage=lethal_damage,
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
    return state, agent_id, hazard_id


# --- Tests ---


def test_agent_takes_damage_from_hazard() -> None:
    state, agent_id, _ = make_agent_hazard_state()
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 7


def test_agent_dies_on_lethal_hazard() -> None:
    state, agent_id, _ = make_agent_hazard_state(lethal=True)
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert agent_id in state.dead


def test_agent_with_hazard_immunity_powerup_takes_no_damage() -> None:
    powerup: Dict[PowerUpType, PowerUp] = {
        PowerUpType.HAZARD_IMMUNITY: PowerUp(
            type=PowerUpType.HAZARD_IMMUNITY, limit=PowerUpLimit.DURATION, remaining=3
        )
    }
    state, agent_id, _ = make_agent_hazard_state(powerup=powerup)
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 10


def test_agent_with_ghost_powerup_takes_no_damage() -> None:
    powerup: Dict[PowerUpType, PowerUp] = {
        PowerUpType.GHOST: PowerUp(
            type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=3
        )
    }
    state, agent_id, _ = make_agent_hazard_state(powerup=powerup)
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 10


def test_shield_usage_blocks_hazard_and_is_consumed() -> None:
    powerup: Dict[PowerUpType, PowerUp] = {
        PowerUpType.SHIELD: PowerUp(
            type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=1
        )
    }
    state, agent_id, _ = make_agent_hazard_state(powerup=powerup)
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 10
    assert PowerUpType.SHIELD not in state.powerup_status[agent_id]


def test_shield_duration_limit_does_not_block_hazard() -> None:
    powerup: Dict[PowerUpType, PowerUp] = {
        PowerUpType.SHIELD: PowerUp(
            type=PowerUpType.SHIELD, limit=PowerUpLimit.DURATION, remaining=2
        )
    }
    state, agent_id, _ = make_agent_hazard_state(powerup=powerup)
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 7


def test_multiple_hazards_damage_accumulates() -> None:
    state, agent_id, hazard_id1 = make_agent_hazard_state(hazard_damage=2)
    hazard_id2: EntityID = 3
    state = replace(
        state,
        hazard=state.hazard.set(hazard_id2, Hazard(type=HazardType.LAVA)),
        damage=state.damage.set(hazard_id2, Damage(amount=3)),
        position=state.position.set(hazard_id2, Position(1, 0)),
        health=state.health.set(agent_id, Health(health=10, max_health=10)),
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 5


def test_multiple_hazards_one_lethal_one_nonlethal() -> None:
    state, agent_id, hazard_id1 = make_agent_hazard_state(hazard_damage=2)
    hazard_id2: EntityID = 4
    state = replace(
        state,
        hazard=state.hazard.set(hazard_id2, Hazard(type=HazardType.LAVA)),
        damage=state.damage.set(hazard_id2, Damage(amount=1)),
        lethal_damage=state.lethal_damage.set(hazard_id2, LethalDamage()),
        position=state.position.set(hazard_id2, Position(1, 0)),
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert agent_id in state.dead


def test_dead_agent_on_hazard_no_effect() -> None:
    state, agent_id, _ = make_agent_hazard_state()
    state = replace(state, dead=state.dead.set(agent_id, Dead()))
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.dead[agent_id]
    assert state.health[agent_id].health == 10


def test_agent_on_hazard_without_health_component() -> None:
    state, agent_id, _ = make_agent_hazard_state()
    state = replace(state, health=pmap())
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert agent_id not in state.health


def test_hazard_with_zero_damage() -> None:
    state, agent_id, hazard_id = make_agent_hazard_state(hazard_damage=0)
    state = replace(
        state, health=state.health.set(agent_id, Health(health=9, max_health=10))
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 9


def test_hazard_with_negative_damage_raises_error() -> None:
    state, agent_id, hazard_id = make_agent_hazard_state(hazard_damage=-2)
    with pytest.raises(ValueError):
        step(
            state,
            MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
            agent_id=agent_id,
        )


def test_hazard_and_enemy_on_same_tile() -> None:
    from grid_universe.components import Enemy

    state, agent_id, hazard_id = make_agent_hazard_state(hazard_damage=2)
    enemy_id: EntityID = 9
    state = replace(
        state,
        enemy=state.enemy.set(enemy_id, Enemy()),
        position=state.position.set(enemy_id, Position(1, 0)),
        damage=state.damage.set(enemy_id, Damage(amount=3)),
        health=state.health.set(agent_id, Health(health=10, max_health=10)),
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 5


def test_no_hazard_at_tile_no_health_change() -> None:
    state, agent_id, hazard_id = make_agent_hazard_state(
        hazard_pos=(2, 0)
    )  # hazard is not where agent moves
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 10


def test_multiple_agents_on_same_hazard() -> None:
    state1, agent1_id, hazard_id = make_agent_hazard_state(
        agent_health=7, hazard_damage=2
    )
    agent2_id: EntityID = 20
    pos2: Position = Position(0, 0)
    agent2: Agent = Agent()
    inventory2: Inventory = Inventory(pset())
    health2: Health = Health(health=6, max_health=6)
    state1 = replace(
        state1,
        agent=state1.agent.set(agent2_id, agent2),
        inventory=state1.inventory.set(agent2_id, inventory2),
        health=state1.health.set(agent2_id, health2),
        position=state1.position.set(agent2_id, pos2),
    )
    # Move both agents onto hazard
    state1 = step(
        state1,
        MoveAction(entity_id=agent1_id, direction=Direction.RIGHT),
        agent_id=agent1_id,
    )
    state1 = step(
        state1,
        MoveAction(entity_id=agent2_id, direction=Direction.RIGHT),
        agent_id=agent2_id,
    )
    assert state1.health[agent1_id].health == 5
    assert state1.health[agent2_id].health == 4


def test_agent_with_permanent_powerup_on_hazard() -> None:
    powerup: Dict[PowerUpType, PowerUp] = {
        PowerUpType.HAZARD_IMMUNITY: PowerUp(
            type=PowerUpType.HAZARD_IMMUNITY,
            limit=PowerUpLimit.DURATION,
            remaining=None,
        )
    }
    state, agent_id, _ = make_agent_hazard_state(
        powerup=powerup, unlimited_powerup=True
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 10


def test_agent_moves_off_and_back_on_hazard() -> None:
    # Setup with hazard at (1,0), agent at (0,0)
    state, agent_id, hazard_id = make_agent_hazard_state()
    # Move right onto hazard
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    # Move left (back to (0,0)), then right again (onto hazard)
    state = replace(state, position=state.position.set(agent_id, Position(0, 0)))
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert (
        state.health[agent_id].health == 4
    )  # 2 steps onto hazard (3 damage each time, start 10)


def test_agent_with_multiple_powerups_only_one_applies() -> None:
    powerup: Dict[PowerUpType, PowerUp] = {
        PowerUpType.GHOST: PowerUp(
            type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=2
        ),
        PowerUpType.SHIELD: PowerUp(
            type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=3
        ),
    }
    state, agent_id, _ = make_agent_hazard_state(powerup=powerup)
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    # Ghost blocks hazard, shield should not be consumed
    assert state.health[agent_id].health == 10
    assert PowerUpType.SHIELD in state.powerup_status[agent_id]


def test_hazard_effects_with_inventory_changes() -> None:
    # Agent picks up hazard immunity powerup, then moves onto hazard
    powerup: Dict[PowerUpType, PowerUp] = {
        PowerUpType.HAZARD_IMMUNITY: PowerUp(
            type=PowerUpType.HAZARD_IMMUNITY, limit=PowerUpLimit.DURATION, remaining=2
        )
    }
    # Setup without powerup, then add powerup just before the move
    state, agent_id, _ = make_agent_hazard_state()
    powerup_status: PMap[EntityID, PMap[PowerUpType, PowerUp]] = pmap(
        {agent_id: pmap(powerup)}
    )
    state = replace(state, powerup_status=powerup_status)
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.health[agent_id].health == 10
