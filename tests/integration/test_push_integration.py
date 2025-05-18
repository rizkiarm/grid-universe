from dataclasses import replace
from typing import Tuple, List, Dict
from pyrsistent import pmap, pset

from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.components import (
    Agent,
    Inventory,
    Box,
    Pushable,
    Collidable,
    Wall,
    Position,
    Collectible,
    Exit,
)
from grid_universe.actions import MoveAction, Direction
from grid_universe.step import step


def make_push_state(
    agent_pos: Tuple[int, int],
    box_positions: List[Tuple[int, int]] = [],
    wall_positions: List[Tuple[int, int]] = [],
    width: int = 5,
    height: int = 5,
) -> Tuple[State, EntityID, List[EntityID], List[EntityID]]:
    pos: Dict[EntityID, Position] = {}
    agent: Dict[EntityID, Agent] = {}
    inventory: Dict[EntityID, Inventory] = {}
    box: Dict[EntityID, Box] = {}
    pushable: Dict[EntityID, Pushable] = {}
    wall: Dict[EntityID, Wall] = {}
    collidable: Dict[EntityID, Collidable] = {}

    agent_id: EntityID = 1
    pos[agent_id] = Position(*agent_pos)
    agent[agent_id] = Agent()
    inventory[agent_id] = Inventory(pset())
    collidable[agent_id] = Collidable()

    box_ids: List[EntityID] = []
    for bpos in box_positions:
        bid: EntityID = len(pos) + 1
        pos[bid] = Position(*bpos)
        box[bid] = Box()
        pushable[bid] = Pushable()
        collidable[bid] = Collidable()
        box_ids.append(bid)

    wall_ids: List[EntityID] = []
    for wpos in wall_positions:
        wid: EntityID = len(pos) + 1
        pos[wid] = Position(*wpos)
        wall[wid] = Wall()
        collidable[wid] = Collidable()
        wall_ids.append(wid)

    state: State = State(
        width=width,
        height=height,
        move_fn=lambda s, eid, dir: [
            Position(
                s.position[eid].x
                + (1 if dir == Direction.RIGHT else -1 if dir == Direction.LEFT else 0),
                s.position[eid].y
                + (1 if dir == Direction.DOWN else -1 if dir == Direction.UP else 0),
            )
        ],
        position=pmap(pos),
        agent=pmap(agent),
        enemy=pmap(),
        box=pmap(box),
        pushable=pmap(pushable),
        wall=pmap(wall),
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
        inventory=pmap(inventory),
        health=pmap(),
        powerup=pmap(),
        powerup_status=pmap(),
        floor=pmap(),
        blocking=pmap(),
        dead=pmap(),
        moving=pmap(),
        hazard=pmap(),
        collidable=pmap(collidable),
        damage=pmap(),
        lethal_damage=pmap(),
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
    return state, agent_id, box_ids, wall_ids


def check_positions(state: State, expected: Dict[EntityID, Position]) -> None:
    for eid, pos in expected.items():
        assert state.position[eid] == pos


def test_agent_pushes_box_successfully() -> None:
    # Agent at (0,0), box at (1,0), open cell at (2,0)
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(1, 0),
            box_ids[0]: Position(2, 0),
        },
    )


def test_push_blocked_by_wall() -> None:
    # Agent at (0,0), box at (1,0), wall at (2,0)
    state, agent_id, box_ids, wall_ids = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)], wall_positions=[(2, 0)]
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(1, 0),
            wall_ids[0]: Position(2, 0),
        },
    )


def test_push_blocked_by_another_box() -> None:
    # Agent at (0,0), box1 at (1,0), box2 at (2,0)
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0), (2, 0)]
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(1, 0),
            box_ids[1]: Position(2, 0),
        },
    )


def test_push_box_out_of_bounds() -> None:
    # Agent at (3,0), box at (4,0), grid is 5x1
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(3, 0), box_positions=[(4, 0)], width=5, height=1
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(3, 0),
            box_ids[0]: Position(4, 0),
        },
    )


def test_push_box_onto_collectible() -> None:
    # Agent at (0,0), box at (1,0), collectible at (2,0)
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    collectible_id: EntityID = 100
    state = replace(
        state,
        collectible=state.collectible.set(collectible_id, Collectible()),
        position=state.position.set(collectible_id, Position(2, 0)),
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(1, 0),
            box_ids[0]: Position(2, 0),
            collectible_id: Position(2, 0),
        },
    )


def test_push_box_onto_exit() -> None:
    # Agent at (0,0), box at (1,0), exit at (2,0)
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    exit_id: EntityID = 101
    state = replace(
        state,
        exit=state.exit.set(exit_id, Exit()),
        position=state.position.set(exit_id, Position(2, 0)),
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(1, 0),
            box_ids[0]: Position(2, 0),
            exit_id: Position(2, 0),
        },
    )


def test_push_box_left_right_up_down() -> None:
    # Parametric test for four directions
    for direction, agent_pos, box_pos, dest_pos in [
        (Direction.RIGHT, (0, 0), (1, 0), (2, 0)),
        (Direction.LEFT, (2, 0), (1, 0), (0, 0)),
        (Direction.DOWN, (0, 0), (0, 1), (0, 2)),
        (Direction.UP, (0, 2), (0, 1), (0, 0)),
    ]:
        state, agent_id, box_ids, _ = make_push_state(
            agent_pos=agent_pos, box_positions=[box_pos], width=3, height=3
        )
        state = step(
            state,
            MoveAction(entity_id=agent_id, direction=direction),
            agent_id=agent_id,
        )
        check_positions(
            state,
            {
                agent_id: Position(*box_pos),
                box_ids[0]: Position(*dest_pos),
            },
        )


def test_push_box_on_narrow_grid_edge() -> None:
    # Agent at (0,0), box at (0,1), grid is 1x2
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(0, 1)], width=1, height=2
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.DOWN),
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(0, 1),
        },
    )


def test_push_chain_of_boxes_blocked() -> None:
    # Agent at (0,0), box1 at (1,0), box2 at (2,0): should not move
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0), (2, 0)]
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(1, 0),
            box_ids[1]: Position(2, 0),
        },
    )


def test_push_not_adjacent() -> None:
    # Agent at (0,0), box at (2,0): not adjacent, agent can move right into (1,0)
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(2, 0)]
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert state.position[agent_id] == Position(1, 0)
    assert state.position[box_ids[0]] == Position(2, 0)


def test_push_no_pushable_at_destination() -> None:
    # Agent at (0,0), empty at (1,0)
    state, agent_id, _, _ = make_push_state(agent_pos=(0, 0))
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    # Agent moves into empty space, nothing to push
    check_positions(
        state,
        {
            agent_id: Position(1, 0),
        },
    )


def test_push_box_blocked_by_agent() -> None:
    # Agent1 at (0,0), box at (1,0), agent2 at (2,0)
    state, agent1_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    agent2_id: EntityID = 99
    state = replace(
        state,
        agent=state.agent.set(agent2_id, Agent()),
        collidable=state.collidable.set(agent2_id, Collidable()),
        position=state.position.set(agent2_id, Position(2, 0)),
        inventory=state.inventory.set(agent2_id, Inventory(pset())),
    )
    state = step(
        state,
        MoveAction(entity_id=agent1_id, direction=Direction.RIGHT),
        agent_id=agent1_id,
    )
    check_positions(
        state,
        {
            agent1_id: Position(0, 0),
            box_ids[0]: Position(1, 0),
            agent2_id: Position(2, 0),
        },
    )


def test_push_box_missing_position_component() -> None:
    # Agent at (0,0), box in pushable but not in position
    state, agent_id, box_ids, _ = make_push_state(agent_pos=(0, 0))
    missing_box_id: EntityID = 42
    state = replace(
        state,
        box=state.box.set(missing_box_id, Box()),
        pushable=state.pushable.set(missing_box_id, Pushable()),
        # No position for box 42
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    # Should not crash or affect positions
    assert missing_box_id not in state.position


def test_push_box_after_agent_moves_multiple_times() -> None:
    # Agent at (0,0), box at (1,0)
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)]
    )
    # Move agent left (should be blocked by edge), then right (pushes box)
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.LEFT),
        agent_id=agent_id,
    )
    state = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    check_positions(
        state,
        {
            agent_id: Position(1, 0),
            box_ids[0]: Position(2, 0),
        },
    )
