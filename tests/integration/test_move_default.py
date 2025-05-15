from typing import Tuple, Sequence
import pytest

from pyrsistent import pmap
from ecs_maze.actions import MoveAction, Direction
from ecs_maze.components import (
    Box,
    Pushable,
    Exit,
    PowerUp,
    PowerUpType,
    PowerUpLimit,
    Wall,
    Position,
    LethalDamage,
    Hazard,
    HazardType,
)
from ecs_maze.types import EntityID
from ecs_maze.step import step
from ecs_maze.moves import default_move_fn
from tests.test_utils import make_agent_state


def test_agent_moves_right() -> None:
    state, agent_id = make_agent_state(agent_pos=(1, 1), move_fn=default_move_fn)
    state2 = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (2, 1)


@pytest.mark.parametrize(
    "start, direction, expected",
    [
        ((1, 1), Direction.UP, (1, 0)),
        ((1, 1), Direction.DOWN, (1, 2)),
        ((1, 1), Direction.LEFT, (0, 1)),
        ((1, 1), Direction.RIGHT, (2, 1)),
    ],
)
def test_agent_moves_in_all_directions(
    start: Tuple[int, int], direction: Direction, expected: Tuple[int, int]
) -> None:
    state, agent_id = make_agent_state(agent_pos=start, move_fn=default_move_fn)
    state2 = step(
        state, MoveAction(entity_id=agent_id, direction=direction), agent_id=agent_id
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == expected


@pytest.mark.parametrize(
    "start, direction",
    [
        ((0, 0), Direction.LEFT),
        ((0, 0), Direction.UP),
        ((4, 4), Direction.RIGHT),
        ((4, 4), Direction.DOWN),
    ],
)
def test_agent_blocked_by_edge(start: Tuple[int, int], direction: Direction) -> None:
    state, agent_id = make_agent_state(agent_pos=start, move_fn=default_move_fn)
    state2 = step(
        state, MoveAction(entity_id=agent_id, direction=direction), agent_id=agent_id
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == start


def test_agent_blocked_by_wall() -> None:
    wall_id: EntityID = 2
    extra = {"position": {wall_id: Position(2, 1)}, "wall": {wall_id: Wall()}}
    state, agent_id = make_agent_state(
        agent_pos=(1, 1), extra_components=extra, move_fn=default_move_fn
    )
    state2 = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (1, 1)


def test_agent_pushes_single_box() -> None:
    box_id: EntityID = 2
    extra = {
        "position": {box_id: Position(2, 1)},
        "box": {box_id: Box()},
        "pushable": {box_id: Pushable()},
    }
    state, agent_id = make_agent_state(
        agent_pos=(1, 1), extra_components=extra, move_fn=default_move_fn
    )
    state2 = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (2, 1)
    assert (state2.position[box_id].x, state2.position[box_id].y) == (3, 1)


def test_agent_blocked_by_chain_of_boxes() -> None:
    box1: EntityID = 2
    box2: EntityID = 3
    extra = {
        "position": {box1: Position(2, 1), box2: Position(3, 1)},
        "box": {box1: Box(), box2: Box()},
        "pushable": {box1: Pushable(), box2: Pushable()},
    }
    state, agent_id = make_agent_state(
        agent_pos=(1, 1), extra_components=extra, move_fn=default_move_fn
    )
    state2 = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (1, 1)
    assert (state2.position[box1].x, state2.position[box1].y) == (2, 1)
    assert (state2.position[box2].x, state2.position[box2].y) == (3, 1)


def test_agent_with_ghost_moves_through_wall() -> None:
    wall_id: EntityID = 2
    powerup_status = pmap(
        {
            1: pmap(
                {
                    PowerUpType.GHOST: PowerUp(
                        type=PowerUpType.GHOST, limit=PowerUpLimit.DURATION, remaining=2
                    )
                }
            )
        }
    )
    extra = {"position": {wall_id: Position(2, 1)}, "wall": {wall_id: Wall()}}
    state, agent_id = make_agent_state(
        agent_pos=(1, 1),
        extra_components=extra,
        powerup_status=powerup_status,
        move_fn=default_move_fn,
    )
    state2 = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (2, 1)


def test_agent_with_double_speed_moves_two_steps() -> None:
    powerup_status = pmap(
        {
            1: pmap(
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
    state, agent_id = make_agent_state(
        agent_pos=(1, 1), powerup_status=powerup_status, move_fn=default_move_fn
    )
    state2 = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (3, 1)


def test_agent_wins_on_exit() -> None:
    exit_id: EntityID = 5
    extra = {
        "position": {exit_id: Position(2, 1)},
        "exit": {exit_id: Exit()},
    }
    state, agent_id = make_agent_state(
        agent_pos=(1, 1), extra_components=extra, move_fn=default_move_fn
    )
    state2 = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (2, 1)
    assert state2.win


def test_agent_loses_on_hazard() -> None:
    hazard_id: EntityID = 20
    extra = {
        "position": {hazard_id: Position(2, 1)},
        "hazard": {hazard_id: Hazard(type=HazardType.LAVA)},
        "lethal_damage": {hazard_id: LethalDamage()},
    }
    state, agent_id = make_agent_state(
        agent_pos=(1, 1), extra_components=extra, move_fn=default_move_fn
    )
    state2 = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (2, 1)
    assert agent_id in state2.dead


def test_agent_move_fn_returns_empty_list() -> None:
    def empty_move_fn(state, eid, direction) -> Sequence[Position]:
        return []

    state, agent_id = make_agent_state(agent_pos=(1, 1), move_fn=empty_move_fn)
    state2 = step(
        state,
        MoveAction(entity_id=agent_id, direction=Direction.RIGHT),
        agent_id=agent_id,
    )
    assert (state2.position[agent_id].x, state2.position[agent_id].y) == (1, 1)
