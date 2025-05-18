from dataclasses import replace
from grid_universe.systems.terminal import win_system, lose_system
from grid_universe.components import (
    Agent,
    Required,
    Collectible,
    Exit,
    Inventory,
    Item,
    Dead,
    Position,
)
from grid_universe.state import State
from grid_universe.types import EntityID
from pyrsistent import PMap, pmap, pset


def make_terminal_state(
    agent_on_exit: bool, all_required_collected: bool, agent_dead: bool
) -> tuple[State, EntityID, EntityID, list[EntityID]]:
    agent_id: EntityID = 1
    exit_id: EntityID = 2
    required_ids: list[EntityID] = [3, 4]

    agent = pmap({agent_id: Agent()})
    exit_map = pmap({exit_id: Exit()})
    # Place agent either on exit or away
    pos = {
        agent_id: Position(0, 0) if not agent_on_exit else Position(1, 1),
        exit_id: Position(1, 1),
    }
    # Place required items somewhere away from exit
    for i, rid in enumerate(required_ids):
        pos[rid] = Position(i + 5, 5)
    required = pmap({rid: Required() for rid in required_ids})
    collectible: PMap[EntityID, Collectible] = pmap()
    item: PMap[EntityID, Item] = pmap()
    inventory = pmap({agent_id: Inventory(pset())})
    # If all required collected, remove them from collectible
    if not all_required_collected:
        collectible = pmap({rid: Collectible() for rid in required_ids})
        item = pmap({rid: Item() for rid in required_ids})

    dead: PMap[EntityID, Dead] = pmap()
    if agent_dead:
        dead = pmap({agent_id: Dead()})

    state = State(
        width=5,
        height=5,
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
        exit=exit_map,
        key=pmap(),
        collectible=collectible,
        rewardable=pmap(),
        cost=pmap(),
        item=item,
        required=required,
        inventory=inventory,
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
    return state, agent_id, exit_id, required_ids


def test_win_when_on_exit_and_required_collected() -> None:
    state, agent_id, exit_id, required_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    new_state = win_system(state, agent_id)
    assert new_state.win


def test_no_win_if_required_not_collected() -> None:
    state, agent_id, exit_id, required_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=False, agent_dead=False
    )
    new_state = win_system(state, agent_id)
    assert not new_state.win


def test_no_win_if_not_on_exit() -> None:
    state, agent_id, exit_id, required_ids = make_terminal_state(
        agent_on_exit=False, all_required_collected=True, agent_dead=False
    )
    new_state = win_system(state, agent_id)
    assert not new_state.win


def test_lose_if_agent_dead() -> None:
    state, agent_id, exit_id, required_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=True
    )
    new_state = lose_system(state, agent_id)
    assert new_state.lose


def test_no_lose_if_agent_alive() -> None:
    state, agent_id, exit_id, required_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    new_state = lose_system(state, agent_id)
    assert not new_state.lose


def test_win_when_on_exit_no_required_items() -> None:
    state, agent_id, exit_id, required_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    # Remove all required items from state
    state = replace(state, required=pmap())
    new_state = win_system(state, agent_id)
    assert new_state.win


def test_dead_agent_on_exit_no_win() -> None:
    state, agent_id, exit_id, required_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=True
    )
    win_state = win_system(state, agent_id)
    lose_state = lose_system(state, agent_id)
    assert lose_state.lose
    assert not win_state.win  # Normally, no win if agent is dead


def test_win_state_is_idempotent() -> None:
    state, agent_id, exit_id, required_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    state = replace(state, win=True)
    new_state = win_system(state, agent_id)
    assert new_state.win


def test_lose_state_is_idempotent() -> None:
    state, agent_id, exit_id, required_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=True
    )
    state = replace(state, lose=True)
    new_state = lose_system(state, agent_id)
    assert new_state.lose


def test_no_win_if_agent_position_missing() -> None:
    state, agent_id, exit_id, required_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    state = replace(state, position=state.position.remove(agent_id))
    new_state = win_system(state, agent_id)
    assert not new_state.win


def test_no_win_if_no_agent_in_state() -> None:
    state, agent_id, exit_id, required_ids = make_terminal_state(
        agent_on_exit=True, all_required_collected=True, agent_dead=False
    )
    state = replace(state, agent=pmap())
    new_state = win_system(state, agent_id)
    assert not new_state.win


def test_win_when_on_any_exit() -> None:
    state, agent_id, exit_id, required_ids = make_terminal_state(
        agent_on_exit=False, all_required_collected=True, agent_dead=False
    )
    # Add another exit at agent's position
    exit2_id = 77
    pos = state.position.set(exit2_id, state.position[agent_id])
    exits = state.exit.set(exit2_id, Exit())
    state = replace(state, exit=exits, position=pos)
    new_state = win_system(state, agent_id)
    assert new_state.win
