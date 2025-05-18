from typing import Optional, Dict, Tuple
from dataclasses import replace
from grid_universe.systems.push import push_system
from grid_universe.components import (
    Agent,
    Box,
    Pushable,
    Blocking,
    Collidable,
    Wall,
    Position,
    Portal,
    Exit,
    Collectible,
)
from grid_universe.state import State
from grid_universe.types import EntityID
from pyrsistent import PMap, pmap


def with_positions(state: State, positions: Dict[EntityID, Position]) -> State:
    pos = state.position
    for eid, newpos in positions.items():
        pos = pos.set(eid, newpos)
    return replace(state, position=pos)


def check_positions(state: State, expected: Dict[EntityID, Position]) -> None:
    for eid, pos in expected.items():
        assert state.position[eid] == pos


def make_push_state(
    box_blocked: bool = False, blocker_is_box: bool = False
) -> Tuple[State, EntityID, EntityID, Optional[EntityID]]:
    agent_id: EntityID = 1
    box_id: EntityID = 2
    pos = {agent_id: Position(0, 0), box_id: Position(1, 0)}
    wall: PMap[EntityID, Wall] = pmap()
    blocker_id: Optional[EntityID] = None

    agent = pmap({agent_id: Agent()})
    box_map = pmap({box_id: Box()})
    pushable = pmap({box_id: Pushable()})
    blocking = pmap({box_id: Blocking()})
    collidable = pmap({agent_id: Collidable(), box_id: Collidable()})

    if box_blocked:
        blocker_id = 3
        pos[blocker_id] = Position(2, 0)
        if blocker_is_box:
            box_map = box_map.set(blocker_id, Box())
            pushable = pushable.set(blocker_id, Pushable())
            blocking = blocking.set(blocker_id, Blocking())
            collidable = collidable.set(blocker_id, Collidable())
        else:
            wall = wall.set(blocker_id, Wall())
            collidable = collidable.set(blocker_id, Collidable())

    state = State(
        width=3,
        height=1,
        move_fn=lambda s, eid, dir: [Position(s.position[eid].x + 1, 0)],
        position=pmap(pos),
        agent=agent,
        enemy=pmap(),
        box=box_map,
        pushable=pushable,
        wall=wall,
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
        blocking=blocking,
        dead=pmap(),
        moving=pmap(),
        hazard=pmap(),
        collidable=collidable,
        damage=pmap(),
        lethal_damage=pmap(),
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
    return state, agent_id, box_id, blocker_id


def test_push_box_success() -> None:
    state, agent_id, box_id, _ = make_push_state()
    new_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        new_state,
        {
            box_id: Position(2, 0),
            agent_id: Position(1, 0),
        },
    )


def test_push_box_blocked_by_wall() -> None:
    state, agent_id, box_id, _ = make_push_state(box_blocked=True, blocker_is_box=False)
    new_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        new_state,
        {
            box_id: Position(1, 0),
            agent_id: Position(0, 0),
        },
    )


def test_push_box_blocked_by_another_box() -> None:
    state, agent_id, box_id, _ = make_push_state(box_blocked=True, blocker_is_box=True)
    new_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        new_state,
        {
            box_id: Position(1, 0),
            agent_id: Position(0, 0),
        },
    )


def test_push_out_of_bounds() -> None:
    state, agent_id, box_id, _ = make_push_state()
    state = with_positions(
        state,
        {
            agent_id: Position(1, 0),
            box_id: Position(2, 0),
        },
    )
    new_state = push_system(state, agent_id, Position(2, 0))
    check_positions(
        new_state,
        {
            box_id: Position(2, 0),
            agent_id: Position(1, 0),
        },
    )


def test_push_not_adjacent() -> None:
    state, agent_id, box_id, _ = make_push_state()
    state = with_positions(
        state,
        {
            agent_id: Position(0, 0),
            box_id: Position(2, 0),
        },
    )
    new_state = push_system(state, agent_id, Position(2, 0))
    check_positions(
        new_state,
        {
            box_id: Position(2, 0),
            agent_id: Position(0, 0),
        },
    )


def test_push_non_pushable() -> None:
    agent_id: EntityID = 1
    wall_id: EntityID = 2
    agent = pmap({agent_id: Agent()})
    wall = pmap({wall_id: Wall()})
    collidable = pmap({agent_id: Collidable(), wall_id: Collidable()})
    position = pmap({agent_id: Position(0, 0), wall_id: Position(1, 0)})

    state: State = State(
        width=3,
        height=1,
        move_fn=lambda s, eid, dir: [Position(1, 0)],
        position=position,
        agent=agent,
        enemy=pmap(),
        box=pmap(),
        pushable=pmap(),
        wall=wall,
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
        collidable=collidable,
        damage=pmap(),
        lethal_damage=pmap(),
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
    new_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        new_state,
        {
            wall_id: Position(1, 0),
            agent_id: Position(0, 0),
        },
    )


def test_push_box_all_directions() -> None:
    # Right: agent (0,0), box (1,0), empty (2,0)
    state_r, agent_id_r, box_id_r, _ = make_push_state()
    state_r = with_positions(
        state_r, {agent_id_r: Position(0, 0), box_id_r: Position(1, 0)}
    )
    new_state_r = push_system(state_r, agent_id_r, Position(1, 0))
    check_positions(
        new_state_r,
        {
            agent_id_r: Position(1, 0),
            box_id_r: Position(2, 0),
        },
    )
    # Left: agent (2,0), box (1,0), empty (0,0)
    state_l, agent_id_l, box_id_l, _ = make_push_state()
    state_l = with_positions(
        state_l, {agent_id_l: Position(2, 0), box_id_l: Position(1, 0)}
    )
    new_state_l = push_system(state_l, agent_id_l, Position(1, 0))
    check_positions(
        new_state_l,
        {
            agent_id_l: Position(1, 0),
            box_id_l: Position(0, 0),
        },
    )
    # Down: agent (0,0), box (0,1), empty (0,2)
    state_d, agent_id_d, box_id_d, _ = make_push_state()
    state_d = replace(state_d, width=1, height=3)
    state_d = with_positions(
        state_d, {agent_id_d: Position(0, 0), box_id_d: Position(0, 1)}
    )
    new_state_d = push_system(state_d, agent_id_d, Position(0, 1))
    check_positions(
        new_state_d,
        {
            agent_id_d: Position(0, 1),
            box_id_d: Position(0, 2),
        },
    )
    # Up: agent (0,2), box (0,1), empty (0,0)
    state_u, agent_id_u, box_id_u, _ = make_push_state()
    state_u = replace(state_u, width=1, height=3)
    state_u = with_positions(
        state_u, {agent_id_u: Position(0, 2), box_id_u: Position(0, 1)}
    )
    new_state_u = push_system(state_u, agent_id_u, Position(0, 1))
    check_positions(
        new_state_u,
        {
            agent_id_u: Position(0, 1),
            box_id_u: Position(0, 0),
        },
    )


def test_push_box_onto_collectible() -> None:
    state, agent_id, box_id, _ = make_push_state()
    collectible_id = 42
    state = with_positions(state, {agent_id: Position(0, 0), box_id: Position(1, 0)})
    state = replace(
        state,
        collectible=pmap({collectible_id: Collectible()}),
        position=state.position.set(collectible_id, Position(2, 0)),
    )
    new_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        new_state,
        {
            box_id: Position(2, 0),
            agent_id: Position(1, 0),
            collectible_id: Position(2, 0),
        },
    )


def test_push_box_onto_exit() -> None:
    state, agent_id, box_id, _ = make_push_state()
    exit_id = 99
    state = with_positions(state, {agent_id: Position(0, 0), box_id: Position(1, 0)})
    state = replace(
        state,
        exit=pmap({exit_id: Exit()}),
        position=state.position.set(exit_id, Position(2, 0)),
    )
    new_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        new_state,
        {
            box_id: Position(2, 0),
            agent_id: Position(1, 0),
            exit_id: Position(2, 0),
        },
    )


def test_push_blocked_by_agent() -> None:
    blocking_agent_id: EntityID = 99
    state, agent_id, box_id, _ = make_push_state()
    state = with_positions(
        state,
        {
            agent_id: Position(0, 0),
            box_id: Position(1, 0),
            blocking_agent_id: Position(2, 0),
        },
    )
    agent_map = state.agent.set(blocking_agent_id, Agent())
    collidable_map = state.collidable.set(blocking_agent_id, Collidable())
    state = replace(state, agent=agent_map, collidable=collidable_map)
    new_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        new_state,
        {
            box_id: Position(1, 0),
            agent_id: Position(0, 0),
            blocking_agent_id: Position(2, 0),
        },
    )


def test_push_blocked_by_multi_component_blocker() -> None:
    blocker_id: EntityID = 77
    state, agent_id, box_id, _ = make_push_state()
    state = with_positions(
        state,
        {agent_id: Position(0, 0), box_id: Position(1, 0), blocker_id: Position(2, 0)},
    )
    state = replace(
        state,
        box=state.box.set(blocker_id, Box()),
        pushable=state.pushable.set(blocker_id, Pushable()),
        blocking=state.blocking.set(blocker_id, Blocking()),
        collidable=state.collidable.set(blocker_id, Collidable()),
    )
    new_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        new_state,
        {
            box_id: Position(1, 0),
            agent_id: Position(0, 0),
            blocker_id: Position(2, 0),
        },
    )


def test_push_missing_box_position() -> None:
    state, agent_id, box_id, _ = make_push_state()
    state = replace(state, position=state.position.remove(box_id))
    new_state = push_system(state, agent_id, Position(1, 0))
    assert agent_id in new_state.position
    assert box_id not in new_state.position


def test_push_missing_agent_position() -> None:
    state, agent_id, box_id, _ = make_push_state()
    state = replace(state, position=state.position.remove(agent_id))
    new_state = push_system(state, agent_id, Position(1, 0))
    assert box_id in new_state.position
    assert agent_id not in new_state.position


def test_push_box_at_narrow_grid_edge() -> None:
    state, agent_id, box_id, _ = make_push_state()
    state = replace(state, width=1, height=2)
    state = with_positions(state, {agent_id: Position(0, 0), box_id: Position(0, 1)})
    new_state = push_system(state, agent_id, Position(0, 1))
    check_positions(
        new_state,
        {
            box_id: Position(0, 1),
            agent_id: Position(0, 0),
        },
    )


def test_push_box_onto_portal() -> None:
    state, agent_id, box_id, _ = make_push_state()
    portal_id = 77
    state = with_positions(state, {agent_id: Position(0, 0), box_id: Position(1, 0)})
    state = replace(
        state,
        portal=pmap({portal_id: Portal(pair_entity=88)}),
        position=state.position.set(portal_id, Position(2, 0)),
    )
    new_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        new_state,
        {
            agent_id: Position(1, 0),
            box_id: Position(2, 0),
            portal_id: Position(2, 0),
        },
    )
