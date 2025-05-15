from dataclasses import replace
from typing import Dict, List, Tuple
from pyrsistent import pmap, pset
from pyrsistent.typing import PMap

from ecs_maze.state import State
from ecs_maze.types import EntityID
from ecs_maze.components import (
    Agent,
    Required,
    Collectible,
    Exit,
    Inventory,
    Item,
    Dead,
    Position,
)
from ecs_maze.actions import MoveAction, Direction
from ecs_maze.step import step


def make_terminal_state(
    *,
    agent_on_exit: bool,
    required_ids: List[EntityID],
    collected_required_ids: List[EntityID],
    agent_dead: bool,
) -> Tuple[State, EntityID, List[EntityID], EntityID]:
    agent_id: EntityID = 1
    exit_id: EntityID = 2
    agent: Dict[EntityID, Agent] = {agent_id: Agent()}
    pos: Dict[EntityID, Position] = {}
    inventory: Dict[EntityID, Inventory] = {
        agent_id: Inventory(pset(collected_required_ids))
    }
    required: Dict[EntityID, Required] = {}
    collectible: Dict[EntityID, Collectible] = {}
    item: Dict[EntityID, Item] = {}
    for rid in required_ids:
        required[rid] = Required()
        if rid not in collected_required_ids:
            collectible[rid] = Collectible()
            item[rid] = Item()
            pos[rid] = Position(5 + rid, 5)
    pos[agent_id] = Position(1, 1) if agent_on_exit else Position(0, 0)
    pos[exit_id] = Position(1, 1)
    exit_map: Dict[EntityID, Exit] = {exit_id: Exit()}
    dead: PMap[EntityID, Dead] = pmap({agent_id: Dead()}) if agent_dead else pmap()

    state: State = State(
        width=10,
        height=10,
        move_fn=lambda s, eid, d: [],
        position=pmap(pos),
        agent=pmap(agent),
        enemy=pmap(),
        box=pmap(),
        pushable=pmap(),
        wall=pmap(),
        door=pmap(),
        locked=pmap(),
        portal=pmap(),
        exit=pmap(exit_map),
        key=pmap(),
        collectible=pmap(collectible),
        rewardable=pmap(),
        cost=pmap(),
        item=pmap(item),
        required=pmap(required),
        inventory=pmap(inventory),
        health=pmap(),
        powerup=pmap(),
        powerup_status=pmap(),
        floor=pmap(),
        blocking=pmap(),
        dead=dead,
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
    return state, agent_id, required_ids, exit_id


def test_win_when_on_exit_and_all_required_collected() -> None:
    state, agent_id, required_ids, exit_id = make_terminal_state(
        agent_on_exit=True,
        required_ids=[3, 4],
        collected_required_ids=[3, 4],
        agent_dead=False,
    )
    new_state: State = step(
        state, MoveAction(entity_id=agent_id, direction=Direction.UP), agent_id=agent_id
    )
    assert new_state.win
    assert not new_state.lose


def test_no_win_if_required_not_collected() -> None:
    state, agent_id, required_ids, exit_id = make_terminal_state(
        agent_on_exit=True,
        required_ids=[3, 4],
        collected_required_ids=[3],
        agent_dead=False,
    )
    new_state: State = step(
        state, MoveAction(entity_id=agent_id, direction=Direction.UP), agent_id=agent_id
    )
    assert not new_state.win


def test_no_win_if_not_on_exit() -> None:
    state, agent_id, required_ids, exit_id = make_terminal_state(
        agent_on_exit=False,
        required_ids=[3],
        collected_required_ids=[3],
        agent_dead=False,
    )
    new_state: State = step(
        state, MoveAction(entity_id=agent_id, direction=Direction.UP), agent_id=agent_id
    )
    assert not new_state.win


def test_lose_if_agent_dead() -> None:
    state, agent_id, required_ids, exit_id = make_terminal_state(
        agent_on_exit=True, required_ids=[], collected_required_ids=[], agent_dead=True
    )
    new_state: State = step(
        state, MoveAction(entity_id=agent_id, direction=Direction.UP), agent_id=agent_id
    )
    assert new_state.lose


def test_no_lose_if_agent_alive() -> None:
    state, agent_id, required_ids, exit_id = make_terminal_state(
        agent_on_exit=True, required_ids=[], collected_required_ids=[], agent_dead=False
    )
    new_state: State = step(
        state, MoveAction(entity_id=agent_id, direction=Direction.UP), agent_id=agent_id
    )
    assert not new_state.lose


def test_win_when_on_exit_no_required_items() -> None:
    state, agent_id, required_ids, exit_id = make_terminal_state(
        agent_on_exit=True, required_ids=[], collected_required_ids=[], agent_dead=False
    )
    new_state: State = step(
        state, MoveAction(entity_id=agent_id, direction=Direction.UP), agent_id=agent_id
    )
    assert new_state.win


def test_dead_agent_on_exit_no_win() -> None:
    state, agent_id, required_ids, exit_id = make_terminal_state(
        agent_on_exit=True,
        required_ids=[3],
        collected_required_ids=[3],
        agent_dead=True,
    )
    new_state: State = step(
        state, MoveAction(entity_id=agent_id, direction=Direction.UP), agent_id=agent_id
    )
    assert not new_state.win


def test_win_state_is_idempotent() -> None:
    state, agent_id, required_ids, exit_id = make_terminal_state(
        agent_on_exit=True, required_ids=[], collected_required_ids=[], agent_dead=False
    )
    state = replace(state, win=True)
    new_state: State = step(
        state, MoveAction(entity_id=agent_id, direction=Direction.UP), agent_id=agent_id
    )
    assert new_state.win


def test_lose_state_is_idempotent() -> None:
    state, agent_id, required_ids, exit_id = make_terminal_state(
        agent_on_exit=True, required_ids=[], collected_required_ids=[], agent_dead=True
    )
    state = replace(state, lose=True)
    new_state: State = step(
        state, MoveAction(entity_id=agent_id, direction=Direction.UP), agent_id=agent_id
    )
    assert new_state.lose


def test_no_win_if_agent_position_missing() -> None:
    state, agent_id, required_ids, exit_id = make_terminal_state(
        agent_on_exit=True,
        required_ids=[3],
        collected_required_ids=[3],
        agent_dead=False,
    )
    state = replace(state, position=state.position.remove(agent_id))
    new_state: State = step(
        state, MoveAction(entity_id=agent_id, direction=Direction.UP), agent_id=agent_id
    )
    assert not new_state.win


def test_no_win_if_no_agent_in_state() -> None:
    state, agent_id, required_ids, exit_id = make_terminal_state(
        agent_on_exit=True,
        required_ids=[3],
        collected_required_ids=[3],
        agent_dead=False,
    )
    state = replace(state, agent=state.agent.remove(agent_id))
    new_state: State = step(
        state, MoveAction(entity_id=agent_id, direction=Direction.UP), agent_id=agent_id
    )
    assert not new_state.win


def test_win_when_on_any_exit() -> None:
    state, agent_id, required_ids, exit_id = make_terminal_state(
        agent_on_exit=False,
        required_ids=[3],
        collected_required_ids=[3],
        agent_dead=False,
    )
    extra_exit_id: EntityID = 77
    exit_pos: Position = state.position[agent_id]
    state = replace(
        state,
        exit=state.exit.set(extra_exit_id, Exit()),
        position=state.position.set(extra_exit_id, exit_pos),
    )
    new_state: State = step(
        state, MoveAction(entity_id=agent_id, direction=Direction.UP), agent_id=agent_id
    )
    assert new_state.win
