from typing import Tuple

from grid_universe.actions import Action
from grid_universe.components import Position, Moving, MovingAxis, Blocking
from grid_universe.step import step
from grid_universe.types import EntityID
from tests.test_utils import make_agent_state


def test_two_bouncing_movers_do_not_overlap_on_intersection() -> None:
    """
    Two moving, bouncing blockers start at (0,3) moving right and (3,0) moving down.
    After 3 turns they'd both target (3,3) simultaneously; ensure they don't overlap
    and that exactly one of them bounces (reverses direction).
    """
    agent_id: EntityID = 1
    right_id: EntityID = 2
    down_id: EntityID = 3

    extra = {
        "position": {
            right_id: Position(0, 3),
            down_id: Position(3, 0),
        },
        "moving": {
            right_id: Moving(axis=MovingAxis.HORIZONTAL, direction=1, bounce=True),
            down_id: Moving(axis=MovingAxis.VERTICAL, direction=1, bounce=True),
        },
        # Mark as blocking so they treat each other as obstacles
        "blocking": {
            right_id: Blocking(),
            down_id: Blocking(),
        },
    }

    # Place the agent out of the way; default grid (5x5) includes (3,3)
    state, _ = make_agent_state(
        agent_id=agent_id, agent_pos=(4, 4), extra_components=extra
    )

    # Advance three turns with no agent movement (WAIT); autonomous movers update each step
    for _ in range(3):
        state = step(state, Action.WAIT, agent_id=agent_id)

    pos_right: Tuple[int, int] = (
        state.position[right_id].x,
        state.position[right_id].y,
    )
    pos_down: Tuple[int, int] = (state.position[down_id].x, state.position[down_id].y)

    # They must not overlap; in particular both must not end up at (3,3)
    assert pos_right != pos_down, f"Movers overlapped at {pos_right}"
    assert not (pos_right == (3, 3) and pos_down == (3, 3)), "Both movers reached (3,3)"

    # Exactly one of them should have bounced (direction reversed)
    dir_right = state.moving[right_id].direction
    dir_down = state.moving[down_id].direction
    assert sum(1 for d in (dir_right, dir_down) if d == -1) == 1, (
        f"Expected exactly one bounce; directions were right={dir_right}, down={dir_down}"
    )
