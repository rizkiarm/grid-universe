# tests/unit/test_moves.py

import pytest
from typing import List, Sequence, Tuple, Dict
from dataclasses import replace

from grid_universe.moves import (
    default_move_fn,
    wrap_around_move_fn,
    mirror_move_fn,
    slippery_move_fn,
    windy_move_fn,
    gravity_move_fn,
)
from grid_universe.actions import Action
from grid_universe.components import Position, Blocking
from grid_universe.objectives import default_objective_fn
from grid_universe.types import EntityID, MoveFn
from tests.test_utils import make_agent_state


@pytest.mark.parametrize(
    "move_fn, start, Action, expected",
    [
        # default_move_fn, all Actions
        (default_move_fn, (2, 2), Action.UP, (2, 1)),
        (default_move_fn, (2, 2), Action.DOWN, (2, 3)),
        (default_move_fn, (2, 2), Action.LEFT, (1, 2)),
        (default_move_fn, (2, 2), Action.RIGHT, (3, 2)),
        # default_move_fn, out-of-bounds
        (default_move_fn, (0, 0), Action.LEFT, (-1, 0)),
        (default_move_fn, (0, 0), Action.UP, (0, -1)),
        (default_move_fn, (4, 4), Action.DOWN, (4, 5)),
        (default_move_fn, (4, 4), Action.RIGHT, (5, 4)),
        # wrap_around_move_fn, edge wrap
        (wrap_around_move_fn, (0, 1), Action.LEFT, (4, 1)),
        (wrap_around_move_fn, (4, 1), Action.RIGHT, (0, 1)),
        (wrap_around_move_fn, (2, 0), Action.UP, (2, 4)),
        (wrap_around_move_fn, (2, 4), Action.DOWN, (2, 0)),
        # wrap_around_move_fn, not at edge (should not wrap)
        (wrap_around_move_fn, (2, 2), Action.UP, (2, 1)),
        (wrap_around_move_fn, (2, 2), Action.LEFT, (1, 2)),
        # mirror_move_fn
        (mirror_move_fn, (2, 2), Action.UP, (2, 1)),  # UP mirrored to UP
        (mirror_move_fn, (2, 2), Action.DOWN, (2, 3)),  # DOWN mirrored to DOWN
        (mirror_move_fn, (2, 2), Action.LEFT, (3, 2)),  # LEFT mirrored to RIGHT
        (mirror_move_fn, (2, 2), Action.RIGHT, (1, 2)),  # RIGHT mirrored to LEFT
        # mirror_move_fn, out-of-bounds mirror
        (mirror_move_fn, (0, 0), Action.LEFT, (1, 0)),  # mirrors to right
        (
            mirror_move_fn,
            (0, 0),
            Action.RIGHT,
            (-1, 0),
        ),  # mirrors to left (out of grid)
    ],
)
def test_simple_moves(
    move_fn: MoveFn,
    start: Tuple[int, int],
    Action: Action,
    expected: Tuple[int, int],
) -> None:
    width: int = 5
    height: int = 5
    state, agent_id = make_agent_state(
        agent_pos=start, move_fn=move_fn, width=width, height=height
    )
    positions: Sequence[Position] = move_fn(state, agent_id, Action)
    assert positions and positions[0] == Position(*expected)


@pytest.mark.parametrize(
    "move_fn",
    [
        default_move_fn,
        wrap_around_move_fn,
        mirror_move_fn,
        slippery_move_fn,
        windy_move_fn,
        gravity_move_fn,
    ],
)
def test_move_fn_missing_position_raises(
    move_fn: MoveFn,
) -> None:
    width: int = 3
    height: int = 3
    state, agent_id = make_agent_state(
        agent_pos=(1, 1), move_fn=move_fn, width=width, height=height
    )
    state = replace(state, position=state.position.remove(agent_id))
    with pytest.raises(KeyError):
        move_fn(state, agent_id, Action.UP)


def test_wrap_around_move_fn_raises_on_missing_size() -> None:
    state, agent_id = make_agent_state(agent_pos=(1, 1))
    # Remove width/height using dataclasses.replace (frozen dataclass)
    state = replace(state, width=None, height=None)  # type: ignore
    with pytest.raises(ValueError):
        wrap_around_move_fn(state, agent_id, Action.UP)


@pytest.mark.parametrize(
    "start, blockers, Action, expected",
    [
        ((1, 1), [(3, 1)], Action.RIGHT, [(2, 1)]),  # slides until before wall
        ((1, 1), [], Action.RIGHT, [(2, 1), (3, 1), (4, 1)]),  # slides to edge
        ((1, 1), [(2, 1)], Action.RIGHT, [(1, 1)]),  # blocked immediately
        (
            (1, 1),
            [(1, 4)],
            Action.DOWN,
            [(1, 2), (1, 3)],
        ),  # slides till before wall at bottom
        ((1, 4), [], Action.DOWN, [(1, 4)]),  # stuck at edge, can't slide
        ((0, 0), [], Action.LEFT, [(0, 0)]),  # stuck at edge, can't slide
    ],
)
def test_slippery_move_fn(
    start: Tuple[int, int],
    blockers: List[Tuple[int, int]],
    Action: Action,
    expected: List[Tuple[int, int]],
) -> None:
    width: int = 5
    height: int = 5
    blocking_entities: Dict[EntityID, Blocking] = {}
    pos_map: Dict[EntityID, Position] = {}
    for idx, blocker_pos in enumerate(blockers):
        wid: EntityID = 100 + idx
        blocking_entities[wid] = Blocking()
        pos_map[wid] = Position(*blocker_pos)
    extra = {
        "blocking": blocking_entities,
        "position": pos_map,
    }
    state, agent_id = make_agent_state(
        agent_pos=start,
        move_fn=slippery_move_fn,
        objective_fn=default_objective_fn,
        width=width,
        height=height,
        extra_components=extra,
    )
    positions: Sequence[Position] = slippery_move_fn(state, agent_id, Action)
    assert [p for p in positions] == [Position(*xy) for xy in expected]


@pytest.mark.parametrize(
    "start, blockers, Action, expected",
    [
        ((1, 1), [(1, 3)], Action.DOWN, [(1, 2)]),  # falls to just before wall
        ((1, 1), [], Action.DOWN, [(1, 2), (1, 3), (1, 4)]),  # falls to bottom
        ((1, 1), [(1, 2)], Action.DOWN, [(1, 1)]),  # blocked immediately
        ((1, 4), [], Action.DOWN, [(1, 4)]),  # at bottom: can't move
    ],
)
def test_gravity_move_fn(
    start: Tuple[int, int],
    blockers: List[Tuple[int, int]],
    Action: Action,
    expected: List[Tuple[int, int]],
) -> None:
    width: int = 5
    height: int = 5
    blocking_entities: Dict[EntityID, Blocking] = {}
    pos_map: Dict[EntityID, Position] = {}
    for idx, blocker_pos in enumerate(blockers):
        wid: EntityID = 200 + idx
        blocking_entities[wid] = Blocking()
        pos_map[wid] = Position(*blocker_pos)
    extra = {
        "blocking": blocking_entities,
        "position": pos_map,
    }
    state, agent_id = make_agent_state(
        agent_pos=start,
        move_fn=gravity_move_fn,
        objective_fn=default_objective_fn,
        width=width,
        height=height,
        extra_components=extra,
    )
    positions: Sequence[Position] = gravity_move_fn(state, agent_id, Action)
    assert [p for p in positions] == [Position(*xy) for xy in expected]


@pytest.mark.parametrize(
    "wind_first, wind_dir, start, Action, blockers, expected",
    [
        # No wind, just first move
        (0.5, (0, 1), (1, 1), Action.UP, [], [(1, 0)]),
        # Wind triggers, wind right, not blocked
        (0.1, (1, 0), (1, 1), Action.UP, [], [(1, 0), (2, 0)]),
        # Wind triggers, wind left, not blocked
        (0.1, (-1, 0), (1, 1), Action.UP, [], [(1, 0), (0, 0)]),
        # Wind triggers, wind up, but first move out of bounds—should just return current pos
        (0.1, (0, -1), (0, 0), Action.UP, [], [(0, 0)]),
        # Wind triggers, wind right, but right is blocked (move fn does not check blockers)
        (0.1, (1, 0), (1, 1), Action.UP, [(2, 0)], [(1, 0), (2, 0)]),
    ],
)
def test_windy_move_fn(
    monkeypatch: pytest.MonkeyPatch,
    wind_first: float,
    wind_dir: Tuple[int, int],
    start: Tuple[int, int],
    Action: Action,
    blockers: List[Tuple[int, int]],
    expected: List[Tuple[int, int]],
) -> None:
    import grid_universe.moves as moves_mod

    class DummyRng:
        def random(self) -> float:
            return wind_first

        def choice(self, *_) -> Tuple[int, int]:
            return wind_dir

    monkeypatch.setattr(moves_mod.random, "Random", lambda *_args, **_kw: DummyRng())
    width: int = 5
    height: int = 5
    blocking_entities: Dict[EntityID, Blocking] = {}
    pos_map: Dict[EntityID, Position] = {}
    for idx, blocker_pos in enumerate(blockers):
        wid: EntityID = 300 + idx
        blocking_entities[wid] = Blocking()
        pos_map[wid] = Position(*blocker_pos)
    extra = {
        "blocking": blocking_entities,
        "position": pos_map,
    }
    state, agent_id = make_agent_state(
        agent_pos=start,
        move_fn=windy_move_fn,
        objective_fn=default_objective_fn,
        width=width,
        height=height,
        extra_components=extra,
    )
    positions: Sequence[Position] = windy_move_fn(state, agent_id, Action)
    assert [p for p in positions] == [Position(*xy) for xy in expected]
