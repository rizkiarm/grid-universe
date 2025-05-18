from dataclasses import replace
from typing import Optional
from grid_universe.systems.hazard import hazard_system
from grid_universe.components import (
    Agent,
    Inventory,
    Health,
    PowerUp,
    PowerUpType,
    Position,
    Hazard,
    HazardType,
    Damage,
    Dead,
    LethalDamage,
    PowerUpLimit,
)
from grid_universe.state import State
from grid_universe.types import EntityID
from pyrsistent import PMap, pmap, pset


def make_hazard_state(
    powerup_on: Optional[PowerUpType] = None,
    shield_uses: Optional[int] = None,
    lethal: bool = False,
    hazard_damage: int = 2,
    agent_health: int = 5,
) -> tuple[State, EntityID, EntityID]:
    """
    Build a minimal state with one agent on a hazard.
    Optionally:
    - Give agent a powerup or shield.
    - Set hazard to lethal or not.
    Returns (state, agent_id, hazard_id)
    """
    agent_id: EntityID = 1
    hazard_id: EntityID = 2

    pos = {agent_id: Position(0, 0), hazard_id: Position(0, 0)}
    agent = pmap({agent_id: Agent()})
    inventory = pmap({agent_id: Inventory(pset())})
    health = pmap({agent_id: Health(health=agent_health, max_health=agent_health)})
    hazard = pmap({hazard_id: Hazard(type=HazardType.LAVA)})
    lethal_damage: PMap[EntityID, LethalDamage] = (
        pmap({hazard_id: LethalDamage()}) if lethal else pmap()
    )

    powerup_status: PMap[EntityID, PMap[PowerUpType, PowerUp]] = pmap()
    if powerup_on is not None:
        if powerup_on == PowerUpType.SHIELD:
            agent_pu_map = pmap(
                {
                    PowerUpType.SHIELD: PowerUp(
                        type=PowerUpType.SHIELD,
                        limit=PowerUpLimit.USAGE,
                        remaining=shield_uses,
                    )
                }
            )
        else:
            agent_pu_map = pmap(
                {
                    powerup_on: PowerUp(
                        type=powerup_on, limit=PowerUpLimit.DURATION, remaining=3
                    )
                }
            )
        powerup_status = pmap({agent_id: agent_pu_map})

    state = State(
        width=1,
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
        damage=pmap({hazard_id: Damage(amount=hazard_damage)} if not lethal else {}),
        lethal_damage=lethal_damage,
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
    return state, agent_id, hazard_id


def test_agent_takes_damage_from_hazard() -> None:
    state, agent_id, hazard_id = make_hazard_state(lethal=False, hazard_damage=2)
    new_state = hazard_system(state, agent_id)
    assert new_state.health[agent_id].health == 3
    assert agent_id not in new_state.dead


def test_agent_dies_on_lethal_hazard() -> None:
    state, agent_id, hazard_id = make_hazard_state(lethal=True)
    new_state = hazard_system(state, agent_id)
    assert agent_id in new_state.dead


def test_agent_is_immune_with_powerup() -> None:
    state, agent_id, hazard_id = make_hazard_state(
        powerup_on=PowerUpType.HAZARD_IMMUNITY
    )
    new_state = hazard_system(state, agent_id)
    # Health unchanged, not dead
    assert new_state.health[agent_id].health == state.health[agent_id].health
    assert agent_id not in new_state.dead


def test_shield_powerup_blocks_hazard_and_is_consumed() -> None:
    state, agent_id, hazard_id = make_hazard_state(
        powerup_on=PowerUpType.SHIELD, shield_uses=1
    )
    new_state = hazard_system(state, agent_id)
    # Health unchanged, not dead
    assert new_state.health[agent_id].health == state.health[agent_id].health
    assert agent_id not in new_state.dead
    # Powerup uses decremented or shield removed if 1->0
    pu_status = new_state.powerup_status[agent_id]
    assert (
        PowerUpType.SHIELD not in pu_status
        or pu_status[PowerUpType.SHIELD].remaining == 0
    )


def test_no_hazard_means_no_effect() -> None:
    # Agent is not on a hazard
    agent_id = 1
    agent = pmap({agent_id: Agent()})
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
        inventory=pmap(),
        health=pmap({agent_id: Health(health=5, max_health=5)}),
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
    new_state = hazard_system(state, agent_id)
    # Nothing happens
    assert new_state == state


def test_no_effect_if_agent_already_dead():
    state, agent_id, _ = make_hazard_state()
    state = replace(state, dead=state.dead.set(agent_id, Dead()))
    new_state = hazard_system(state, agent_id)
    assert new_state == state


def test_no_effect_if_agent_not_in_position():
    state, agent_id, _ = make_hazard_state()
    state = replace(state, position=state.position.remove(agent_id))
    new_state = hazard_system(state, agent_id)
    assert new_state == state


def test_shield_non_usage_limit_does_not_block():
    state, agent_id, _ = make_hazard_state(powerup_on=PowerUpType.SHIELD, shield_uses=1)
    # Replace SHIELD with duration-limited (should NOT block hazard)
    pu = PowerUp(type=PowerUpType.SHIELD, limit=PowerUpLimit.DURATION, remaining=3)
    state = replace(
        state,
        powerup_status=state.powerup_status.set(
            agent_id, pmap({PowerUpType.SHIELD: pu})
        ),
    )
    new_state = hazard_system(state, agent_id)
    assert (
        new_state.health[agent_id].health < state.health[agent_id].health
    )  # Agent took damage


def test_hazard_no_damage_no_lethal():
    state, agent_id, hazard_id = make_hazard_state(lethal=False, hazard_damage=0)
    state = replace(state, damage=pmap())  # Remove damage
    new_state = hazard_system(state, agent_id)
    assert new_state.health[agent_id].health == state.health[agent_id].health
    assert agent_id not in new_state.dead


def test_lethal_hazard_even_with_no_damage():
    state, agent_id, hazard_id = make_hazard_state(lethal=True, hazard_damage=0)
    state = replace(state, damage=pmap())  # Remove damage
    new_state = hazard_system(state, agent_id)
    assert agent_id in new_state.dead


def test_multiple_hazards_at_tile():
    state, agent_id, hazard_id = make_hazard_state(lethal=False, hazard_damage=2)
    # Add a second hazard at the same position
    hazard_id2 = 99
    state = replace(
        state,
        hazard=state.hazard.set(hazard_id2, Hazard(type=HazardType.LAVA)),
        damage=state.damage.set(hazard_id2, Damage(amount=2)),
        position=state.position.set(hazard_id2, state.position[hazard_id]),
        health=state.health.set(agent_id, Health(health=5, max_health=5)),
    )
    new_state = hazard_system(state, agent_id)
    # Should have taken 2+2=4 damage if no shield etc.
    assert new_state.health[agent_id].health == 1


def test_shield_powerup_removed_after_final_use():
    state, agent_id, hazard_id = make_hazard_state(
        powerup_on=PowerUpType.SHIELD, shield_uses=1
    )
    new_state = hazard_system(state, agent_id)
    pu_status = new_state.powerup_status[agent_id]
    assert PowerUpType.SHIELD not in pu_status


def test_multiple_hazards_shield_partially_blocks():
    state, agent_id, hazard_id = make_hazard_state(
        powerup_on=PowerUpType.SHIELD, shield_uses=1, hazard_damage=2
    )
    # Add a second hazard at the same position
    hazard_id2 = 99
    state = replace(
        state,
        hazard=state.hazard.set(hazard_id2, Hazard(type=HazardType.LAVA)),
        damage=state.damage.set(hazard_id2, Damage(amount=2)),
        position=state.position.set(hazard_id2, state.position[hazard_id]),
        health=state.health.set(agent_id, Health(health=5, max_health=5)),
    )
    new_state = hazard_system(state, agent_id)
    # Shield blocks first, second causes 2 damage
    assert new_state.health[agent_id].health == 3
    pu_status = new_state.powerup_status[agent_id]
    assert PowerUpType.SHIELD not in pu_status  # Shield was depleted


def test_multiple_hazards_one_lethal_one_nonlethal():
    state, agent_id, hazard_id = make_hazard_state(lethal=False, hazard_damage=2)
    # Add a lethal hazard
    hazard_id2 = 100
    state = replace(
        state,
        hazard=state.hazard.set(hazard_id2, Hazard(type=HazardType.LAVA)),
        damage=state.damage.set(hazard_id2, Damage(amount=1)),
        lethal_damage=state.lethal_damage.set(hazard_id2, LethalDamage()),
        position=state.position.set(hazard_id2, state.position[hazard_id]),
    )
    new_state = hazard_system(state, agent_id)
    assert agent_id in new_state.dead
