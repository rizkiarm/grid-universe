from typing import Optional
from grid_universe.systems.enemy import enemy_collision_system
from grid_universe.components import (
    Agent,
    Enemy,
    Inventory,
    Health,
    PowerUp,
    PowerUpType,
    PowerUpLimit,
    Damage,
    LethalDamage,
    Position,
    Dead,
)
from grid_universe.state import State
from grid_universe.types import EntityID
from pyrsistent import PMap, pmap, pset


def make_enemy_collision_state(
    powerup_on: Optional[PowerUpType] = None,
    shield_uses: Optional[int] = None,
    lethal: bool = False,
    enemy_damage: int = 2,
    agent_health: int = 5,
) -> tuple[State, EntityID, EntityID]:
    """
    Build a minimal state with one agent and one enemy at the same position.
    Optionally:
    - Give agent a powerup or shield.
    - Set enemy to lethal or not.
    Returns (state, agent_id, enemy_id)
    """
    agent_id = 1
    enemy_id = 2

    pos = {agent_id: Position(0, 0), enemy_id: Position(0, 0)}
    agent = pmap({agent_id: Agent()})
    enemy = pmap({enemy_id: Enemy()})
    inventory = pmap({agent_id: Inventory(pset())})
    health = pmap({agent_id: Health(health=agent_health, max_health=agent_health)})
    damage = pmap({enemy_id: Damage(amount=enemy_damage)} if not lethal else {})
    lethal_damage: PMap[EntityID, LethalDamage] = (
        pmap({enemy_id: LethalDamage()}) if lethal else pmap()
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
    state, agent_id, enemy_id = make_enemy_collision_state(lethal=False, enemy_damage=2)
    new_state = enemy_collision_system(state, agent_id)
    assert new_state.health[agent_id].health == 3
    assert agent_id not in new_state.dead


def test_agent_dies_from_lethal_enemy() -> None:
    state, agent_id, enemy_id = make_enemy_collision_state(lethal=True)
    new_state = enemy_collision_system(state, agent_id)
    assert agent_id in new_state.dead


def test_agent_is_immune_with_ghost_powerup() -> None:
    state, agent_id, enemy_id = make_enemy_collision_state(powerup_on=PowerUpType.GHOST)
    new_state = enemy_collision_system(state, agent_id)
    # Health unchanged, not dead
    assert new_state.health[agent_id].health == state.health[agent_id].health
    assert agent_id not in new_state.dead


def test_shield_powerup_blocks_enemy_and_is_consumed() -> None:
    state, agent_id, enemy_id = make_enemy_collision_state(
        powerup_on=PowerUpType.SHIELD, shield_uses=1
    )
    new_state = enemy_collision_system(state, agent_id)
    # Health unchanged, not dead
    assert new_state.health[agent_id].health == state.health[agent_id].health
    assert agent_id not in new_state.dead
    # Powerup uses decremented or shield removed if 1->0
    pu_status = new_state.powerup_status[agent_id]
    assert (
        PowerUpType.SHIELD not in pu_status
        or pu_status[PowerUpType.SHIELD].remaining == 0
    )


def test_no_enemy_means_no_effect() -> None:
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
    new_state = enemy_collision_system(state, agent_id)
    # Nothing happens
    assert new_state == state


def test_ghost_powerup_prevents_shield_use_on_enemy() -> None:
    agent_id = 1
    enemy_id = 2
    agent = pmap({agent_id: Agent()})
    enemy = pmap({enemy_id: Enemy()})
    position = pmap({agent_id: Position(0, 0), enemy_id: Position(0, 0)})
    health = pmap({agent_id: Health(health=5, max_health=5)})
    powerup_status = pmap(
        {
            agent_id: pmap(
                {
                    PowerUpType.SHIELD: PowerUp(
                        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=1
                    ),
                    PowerUpType.GHOST: PowerUp(
                        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=2
                    ),
                }
            )
        }
    )
    damage = pmap({enemy_id: Damage(amount=3)})

    state = State(
        width=1,
        height=1,
        move_fn=lambda s, eid, dir: [],
        position=position,
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
        inventory=pmap(),
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
        lethal_damage=pmap(),
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
    new_state = enemy_collision_system(state, agent_id)
    # No health lost; ghost blocks, shield unused
    assert new_state.health[agent_id].health == 5
    pu = new_state.powerup_status[agent_id]
    assert PowerUpType.SHIELD in pu
    assert PowerUpType.GHOST in pu


def test_multiple_enemies_one_shield_only_blocks_first() -> None:
    agent_id = 1
    enemy1_id = 2
    enemy2_id = 3
    agent = pmap({agent_id: Agent()})
    enemy = pmap({enemy1_id: Enemy(), enemy2_id: Enemy()})
    position = pmap(
        {agent_id: Position(0, 0), enemy1_id: Position(0, 0), enemy2_id: Position(0, 0)}
    )
    health = pmap({agent_id: Health(health=5, max_health=5)})
    powerup_status = pmap(
        {
            agent_id: pmap(
                {
                    PowerUpType.SHIELD: PowerUp(
                        type=PowerUpType.SHIELD, limit=PowerUpLimit.USAGE, remaining=1
                    )
                }
            )
        }
    )
    damage = pmap({enemy1_id: Damage(amount=2), enemy2_id: Damage(amount=4)})

    state = State(
        width=1,
        height=1,
        move_fn=lambda s, eid, dir: [],
        position=position,
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
        inventory=pmap(),
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
        lethal_damage=pmap(),
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
    new_state = enemy_collision_system(state, agent_id)
    # Shield blocks one attack, agent takes the other (order may depend on dict ordering)
    # At least, shield is gone and health is either 3 or 1
    hp = new_state.health[agent_id].health
    assert hp in (1, 3)
    assert PowerUpType.SHIELD not in new_state.powerup_status[agent_id]


def test_lethal_takes_precedence_over_damage() -> None:
    agent_id = 1
    enemy_id = 2
    agent = pmap({agent_id: Agent()})
    enemy = pmap({enemy_id: Enemy()})
    position = pmap({agent_id: Position(0, 0), enemy_id: Position(0, 0)})
    health = pmap({agent_id: Health(health=5, max_health=5)})
    damage = pmap({enemy_id: Damage(amount=1)})
    lethal_damage = pmap({enemy_id: LethalDamage()})  # Both present

    state = State(
        width=1,
        height=1,
        move_fn=lambda s, eid, dir: [],
        position=position,
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
        damage=damage,
        lethal_damage=lethal_damage,
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
    new_state = enemy_collision_system(state, agent_id)
    assert agent_id in new_state.dead


def test_enemy_with_no_damage_or_lethal_does_nothing() -> None:
    agent_id = 1
    enemy_id = 2
    agent = pmap({agent_id: Agent()})
    enemy = pmap({enemy_id: Enemy()})
    position = pmap({agent_id: Position(0, 0), enemy_id: Position(0, 0)})
    health = pmap({agent_id: Health(health=5, max_health=5)})

    state = State(
        width=1,
        height=1,
        move_fn=lambda s, eid, dir: [],
        position=position,
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
    new_state = enemy_collision_system(state, agent_id)
    assert new_state.health[agent_id].health == 5
    assert agent_id not in new_state.dead


def test_enemy_collision_on_dead_agent_does_nothing() -> None:
    agent_id = 1
    enemy_id = 2
    agent = pmap({agent_id: Agent()})
    enemy = pmap({enemy_id: Enemy()})
    position = pmap({agent_id: Position(0, 0), enemy_id: Position(0, 0)})
    health = pmap({agent_id: Health(health=2, max_health=5)})
    dead = pmap({agent_id: Dead()})
    damage = pmap({enemy_id: Damage(amount=2)})

    state = State(
        width=1,
        height=1,
        move_fn=lambda s, eid, dir: [],
        position=position,
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
        inventory=pmap(),
        health=health,
        powerup=pmap(),
        powerup_status=pmap(),
        floor=pmap(),
        blocking=pmap(),
        dead=dead,
        moving=pmap(),
        hazard=pmap(),
        collidable=pmap(),
        damage=damage,
        lethal_damage=pmap(),
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
    new_state = enemy_collision_system(state, agent_id)
    # State unchanged
    assert new_state == state
