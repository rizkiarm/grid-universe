from dataclasses import replace

from ecs_maze.components import (
    Damage,
    Position,
    PowerUp,
    PowerUpType,
    PowerUpLimit,
    Hazard,
    HazardType,
    Enemy,
    Health,
    Portal,
    Dead,
    Rewardable,
    Cost,
    Collectible,
)
from ecs_maze.step import step
from ecs_maze.state import State
from ecs_maze.actions import MoveAction, Direction, Action
from pyrsistent import pmap
from tests.test_utils import (
    make_agent_box_wall_state,
    make_exit_entity,
    assert_entity_positions,
)


def add_to_state(state: State, **kwargs) -> State:
    """Utility to update state fields immutably (for DRYness)."""
    return replace(state, **kwargs)


def test_move_valid() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    action: Action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(new_state, {agent_id: (1, 0)})


def test_move_blocked_by_wall() -> None:
    state, agent_id, _, wall_ids = make_agent_box_wall_state(
        agent_pos=(0, 0), wall_positions=[(1, 0)]
    )
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(new_state, {agent_id: (0, 0), wall_ids[0]: (1, 0)})


def test_move_pushes_box() -> None:
    state, agent_id, box_ids, _ = make_agent_box_wall_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(new_state, {agent_id: (1, 0), box_ids[0]: (2, 0)})


def test_move_push_blocked_by_wall_after_box() -> None:
    state, agent_id, box_ids, wall_ids = make_agent_box_wall_state(
        agent_pos=(0, 0), box_positions=[(1, 0)], wall_positions=[(2, 0)]
    )
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(
        new_state,
        {
            agent_id: (0, 0),  # Should still be at start if push fails
            box_ids[0]: (1, 0),
            wall_ids[0]: (2, 0),
        },
    )


def test_move_pushes_box_out_of_bounds() -> None:
    state, agent_id, box_ids, _ = make_agent_box_wall_state(
        agent_pos=(3, 0), box_positions=[(4, 0)], width=5, height=1
    )
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(new_state, {agent_id: (3, 0), box_ids[0]: (4, 0)})


def test_move_wrapping_enabled() -> None:
    from ecs_maze.moves import wrap_around_move_fn

    state, agent_id, _, _ = make_agent_box_wall_state(
        agent_pos=(4, 0), width=5, height=1
    )
    state = add_to_state(state, move_fn=wrap_around_move_fn)
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(new_state, {agent_id: (0, 0)})


def test_move_ghost_powerup_ignores_wall_box() -> None:
    state, agent_id, box_ids, wall_ids = make_agent_box_wall_state(
        agent_pos=(0, 0), box_positions=[(2, 0)], wall_positions=[(1, 0)]
    )
    powerup_status = pmap(
        {
            agent_id: pmap(
                {
                    PowerUpType.GHOST: PowerUp(
                        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=2
                    )
                }
            )
        }
    )
    state = add_to_state(state, powerup_status=powerup_status)
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    # Agent should move to (1,0) (if ghost only removes blocking, not multi-step phase)
    assert_entity_positions(
        new_state, {agent_id: (1, 0), wall_ids[0]: (1, 0), box_ids[0]: (2, 0)}
    )


def test_move_onto_portal_teleports_agent() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    portal1_id, portal2_id = 999, 1000
    pos = state.position.set(portal1_id, Position(1, 0)).set(portal2_id, Position(3, 0))
    portal = pmap(
        {
            portal1_id: Portal(pair_entity=portal2_id),
            portal2_id: Portal(pair_entity=portal1_id),
        }
    )
    state = add_to_state(state, position=pos, portal=portal)
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(new_state, {agent_id: (3, 0)})


def test_move_onto_hazard_takes_damage() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    hazard_id = 200
    pos = state.position.set(hazard_id, Position(1, 0))
    hazard = pmap({hazard_id: Hazard(type=HazardType.LAVA)})
    health = pmap({agent_id: Health(health=5, max_health=5)})
    damage = pmap({hazard_id: Damage(amount=1)})
    state = add_to_state(
        state, position=pos, hazard=hazard, health=health, damage=damage
    )
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    assert new_state.health[agent_id].health == 4


def test_move_onto_enemy_takes_damage() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    enemy_id = 300
    pos = state.position.set(enemy_id, Position(1, 0))
    enemy = pmap({enemy_id: Enemy()})
    health = pmap({agent_id: Health(health=5, max_health=5)})
    damage = pmap({enemy_id: Damage(amount=2)})
    state = add_to_state(state, position=pos, enemy=enemy, health=health, damage=damage)
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    assert new_state.health[agent_id].health == 3


def test_move_onto_reward_cost_collectible_tile() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    reward_id, cost_id, collectible_id = 2, 3, 4
    pos = (
        state.position.set(reward_id, Position(1, 0))
        .set(cost_id, Position(1, 0))
        .set(collectible_id, Position(1, 0))
    )
    rewardable = pmap({reward_id: Rewardable(reward=14)})
    cost = pmap({cost_id: Cost(amount=6)})
    collectible = pmap({collectible_id: Collectible()})
    state = add_to_state(
        state, position=pos, rewardable=rewardable, cost=cost, collectible=collectible
    )
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    # Should grant reward and cost, but not collect (unless pickup is separate)
    assert new_state.score == 8  # 14 - 6


def test_move_double_speed_powerup_moves_twice_and_blocks_at_wall() -> None:
    state, agent_id, _, wall_ids = make_agent_box_wall_state(
        agent_pos=(0, 0), wall_positions=[(2, 0)], width=4, height=1
    )
    powerup_status = pmap(
        {
            agent_id: pmap(
                {
                    PowerUpType.DOUBLE_SPEED: PowerUp(
                        type=PowerUpType.DOUBLE_SPEED,
                        limit=PowerUpLimit.DURATION,
                        remaining=2,
                    )
                }
            )
        }
    )
    state = add_to_state(state, powerup_status=powerup_status)
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    # Agent moves from (0,0) to (1,0), then blocked by wall at (2,0)
    assert_entity_positions(new_state, {agent_id: (1, 0), wall_ids[0]: (2, 0)})


def test_move_onto_exit_triggers_win() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    exit_id, exit_map, exit_pos = make_exit_entity((1, 0))
    pos = state.position.update(exit_pos)
    state = add_to_state(state, exit=pmap(exit_map), position=pos)
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    assert new_state.win


def test_move_dead_agent_does_nothing() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    state = add_to_state(state, dead=pmap({agent_id: Dead()}))
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    # Agent should not have moved
    assert_entity_positions(new_state, {agent_id: (0, 0)})


def test_move_after_win_or_lose_does_nothing() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    state_win = add_to_state(state, win=True)
    state_lose = add_to_state(state, lose=True)
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state_win = step(state_win, action, agent_id=agent_id)
    new_state_lose = step(state_lose, action, agent_id=agent_id)
    assert_entity_positions(new_state_win, {agent_id: (0, 0)})
    assert_entity_positions(new_state_lose, {agent_id: (0, 0)})


def test_move_chained_portal_no_loop() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    # Portals: 101->102, 102->103, 103->101 (should not loop infinitely)
    portal_a, portal_b, portal_c = 101, 102, 103
    pos = (
        state.position.set(portal_a, Position(1, 0))
        .set(portal_b, Position(2, 0))
        .set(portal_c, Position(3, 0))
    )
    portal = pmap(
        {
            portal_a: Portal(pair_entity=portal_b),
            portal_b: Portal(pair_entity=portal_c),
            portal_c: Portal(pair_entity=portal_a),
        }
    )
    state = add_to_state(state, position=pos, portal=portal)
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    # Accept agent at (2,0) or (3,0) depending on portal logic, but should not crash/loop
    assert new_state.position[agent_id] in [Position(2, 0), Position(3, 0)]


def test_move_push_box_onto_portal_box_teleported() -> None:
    state, agent_id, box_ids, _ = make_agent_box_wall_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    portal_a, portal_b = 110, 111
    pos = state.position.set(portal_a, Position(2, 0)).set(portal_b, Position(4, 0))
    portal = pmap(
        {portal_a: Portal(pair_entity=portal_b), portal_b: Portal(pair_entity=portal_a)}
    )
    state = add_to_state(state, position=pos, portal=portal)
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    # Depending on pushable-portal logic, box may be at (2, 0) (not teleported) or (4, 0) (teleported)
    box_pos = new_state.position[box_ids[0]]
    assert new_state.position[agent_id] == Position(1, 0)
    assert box_pos in [Position(2, 0), Position(4, 0)]


def test_move_box_chain_blocked() -> None:
    # Agent at (0,0), boxes at (1,0) and (2,0): cannot push chain
    state, agent_id, box_ids, _ = make_agent_box_wall_state(
        agent_pos=(0, 0), box_positions=[(1, 0), (2, 0)]
    )
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    # Neither box nor agent moves
    assert_entity_positions(
        new_state, {agent_id: (0, 0), box_ids[0]: (1, 0), box_ids[1]: (2, 0)}
    )


def test_move_on_hazard_and_enemy_both_damage() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    hazard_id, enemy_id = 201, 202
    pos = state.position.set(hazard_id, Position(1, 0)).set(enemy_id, Position(1, 0))
    hazard = pmap({hazard_id: Hazard(type=HazardType.LAVA)})
    enemy = pmap({enemy_id: Enemy()})
    health = pmap({agent_id: Health(health=10, max_health=10)})
    damage = pmap({hazard_id: Damage(amount=2), enemy_id: Damage(amount=3)})
    state = add_to_state(
        state, position=pos, hazard=hazard, enemy=enemy, health=health, damage=damage
    )
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    # Agent takes both damages: 10 - 2 - 3 = 5
    assert new_state.health[agent_id].health == 5


def test_move_out_of_bounds_direction_negative_index() -> None:
    # Try to move agent at (0,0) left (to (-1,0))
    state, agent_id, _, _ = make_agent_box_wall_state(
        agent_pos=(0, 0), width=1, height=1
    )
    action = MoveAction(entity_id=agent_id, direction=Direction.LEFT)
    new_state = step(state, action, agent_id=agent_id)
    assert_entity_positions(new_state, {agent_id: (0, 0)})


def test_move_agent_not_in_agent_map() -> None:
    state, agent_id, _, _ = make_agent_box_wall_state(agent_pos=(0, 0))
    state = add_to_state(state, agent=state.agent.remove(agent_id))
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    # Agent still in position map, but did not move
    assert agent_id in new_state.position
    assert new_state.position[agent_id] == Position(0, 0)
    # Agent is still not in agent map
    assert agent_id not in new_state.agent


def test_move_with_minimal_state() -> None:
    # Defensive: state with only map fields, no agents
    from ecs_maze.state import State
    from pyrsistent import pmap

    state = State(
        width=2,
        height=2,
        move_fn=lambda s, eid, d: [],
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
    action = MoveAction(entity_id=9999, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=9999)
    # No crash, no positions present
    assert isinstance(new_state, State)
    assert len(new_state.position) == 0


def test_move_double_speed_powerup_both_steps_blocked() -> None:
    state, agent_id, _, wall_ids = make_agent_box_wall_state(
        agent_pos=(0, 0), wall_positions=[(1, 0), (2, 0)], width=4, height=1
    )
    powerup_status = pmap(
        {
            agent_id: pmap(
                {
                    PowerUpType.DOUBLE_SPEED: PowerUp(
                        type=PowerUpType.DOUBLE_SPEED,
                        limit=PowerUpLimit.DURATION,
                        remaining=2,
                    )
                }
            )
        }
    )
    state = add_to_state(state, powerup_status=powerup_status)
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    # Agent cannot move at all if both steps blocked
    assert_entity_positions(
        new_state, {agent_id: (0, 0), wall_ids[0]: (1, 0), wall_ids[1]: (2, 0)}
    )


def test_move_ghost_and_double_speed_combo() -> None:
    state, agent_id, _, wall_ids = make_agent_box_wall_state(
        agent_pos=(0, 0), wall_positions=[(1, 0), (2, 0)], width=4, height=1
    )
    powerup_status = pmap(
        {
            agent_id: pmap(
                {
                    PowerUpType.GHOST: PowerUp(
                        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=2
                    ),
                    PowerUpType.DOUBLE_SPEED: PowerUp(
                        type=PowerUpType.DOUBLE_SPEED,
                        limit=PowerUpLimit.DURATION,
                        remaining=2,
                    ),
                }
            )
        }
    )
    state = add_to_state(state, powerup_status=powerup_status)
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    assert new_state.position[agent_id] == Position(2, 0)


def test_push_box_onto_exit_agent_doesnt_win() -> None:
    state, agent_id, box_ids, _ = make_agent_box_wall_state(
        agent_pos=(0, 0), box_positions=[(1, 0)], width=5, height=1
    )
    exit_id, exit_map, exit_pos = make_exit_entity((2, 0))
    pos = state.position.update(exit_pos)
    state = add_to_state(state, exit=pmap(exit_map), position=pos)
    action = MoveAction(entity_id=agent_id, direction=Direction.RIGHT)
    new_state = step(state, action, agent_id=agent_id)
    # Agent should not win
    assert not new_state.win
    assert_entity_positions(new_state, {agent_id: (1, 0), box_ids[0]: (2, 0)})
