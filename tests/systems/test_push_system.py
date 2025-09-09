from dataclasses import replace

from pyrsistent import pmap, pset

from grid_universe.actions import Action
from grid_universe.components import (
    Agent,
    Appearance,
    AppearanceName,
    Blocking,
    Collectible,
    Collidable,
    Exit,
    Inventory,
    Portal,
    Position,
    Pushable,
)
from grid_universe.entity import Entity, new_entity_id
from grid_universe.objectives import default_objective_fn
from grid_universe.state import State
from grid_universe.systems.push import push_system
from grid_universe.types import EntityID


def make_push_state(
    agent_pos: tuple[int, int],
    box_positions: list[tuple[int, int]] | None = None,
    wall_positions: list[tuple[int, int]] | None = None,
    width: int = 5,
    height: int = 5,
) -> tuple[State, EntityID, list[EntityID], list[EntityID]]:
    entity: dict[EntityID, Entity] = {}
    pos: dict[EntityID, Position] = {}
    agent: dict[EntityID, Agent] = {}
    inventory: dict[EntityID, Inventory] = {}
    pushable: dict[EntityID, Pushable] = {}
    blocking: dict[EntityID, Blocking] = {}
    collidable: dict[EntityID, Collidable] = {}
    appearance: dict[EntityID, Appearance] = {}

    agent_id: EntityID = new_entity_id()
    entity[agent_id] = Entity()
    pos[agent_id] = Position(*agent_pos)
    agent[agent_id] = Agent()
    inventory[agent_id] = Inventory(pset())
    collidable[agent_id] = Collidable()
    appearance[agent_id] = Appearance(name=AppearanceName.HUMAN)

    box_ids: list[EntityID] = []
    if box_positions:
        for bpos in box_positions:
            bid: EntityID = new_entity_id()
            entity[bid] = Entity()
            pos[bid] = Position(*bpos)
            pushable[bid] = Pushable()
            collidable[bid] = Collidable()
            appearance[bid] = Appearance(name=AppearanceName.BOX)
            box_ids.append(bid)

    wall_ids: list[EntityID] = []
    if wall_positions:
        for wpos in wall_positions:
            wid: EntityID = new_entity_id()
            entity[wid] = Entity()
            pos[wid] = Position(*wpos)
            blocking[wid] = Blocking()
            collidable[wid] = Collidable()
            appearance[wid] = Appearance(name=AppearanceName.WALL)
            wall_ids.append(wid)

    state: State = State(
        width=width,
        height=height,
        move_fn=lambda s, eid, dir: [
            Position(
                s.position[eid].x
                + (1 if dir == Action.RIGHT else -1 if dir == Action.LEFT else 0),
                s.position[eid].y
                + (1 if dir == Action.DOWN else -1 if dir == Action.UP else 0),
            ),
        ],
        objective_fn=default_objective_fn,
        entity=pmap(entity),
        position=pmap(pos),
        agent=pmap(agent),
        pushable=pmap(pushable),
        inventory=pmap(inventory),
        appearance=pmap(appearance),
        blocking=pmap(blocking),
        collidable=pmap(collidable),
    )
    return state, agent_id, box_ids, wall_ids


def check_positions(state: State, expected: dict[EntityID, Position]) -> None:
    for eid, pos in expected.items():
        assert state.position[eid] == pos


def test_agent_pushes_box_successfully() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)],
    )
    next_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        next_state,
        {
            agent_id: Position(1, 0),
            box_ids[0]: Position(2, 0),
        },
    )


def test_push_blocked_by_wall() -> None:
    state, agent_id, box_ids, wall_ids = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)], wall_positions=[(2, 0)],
    )
    next_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        next_state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(1, 0),
            wall_ids[0]: Position(2, 0),
        },
    )


def test_push_blocked_by_another_box() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0), (2, 0)],
    )
    next_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        next_state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(1, 0),
            box_ids[1]: Position(2, 0),
        },
    )


def test_push_box_out_of_bounds() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(3, 0), box_positions=[(4, 0)], width=5, height=1,
    )
    next_state = push_system(state, agent_id, Position(4, 0))
    check_positions(
        next_state,
        {
            agent_id: Position(3, 0),
            box_ids[0]: Position(4, 0),
        },
    )


def test_push_box_onto_collectible() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)],
    )
    collectible_id: EntityID = new_entity_id()
    state = replace(
        state,
        collectible=state.collectible.set(collectible_id, Collectible()),
        position=state.position.set(collectible_id, Position(2, 0)),
        entity=state.entity.set(collectible_id, Entity()),
    )
    next_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        next_state,
        {
            agent_id: Position(1, 0),
            box_ids[0]: Position(2, 0),
            collectible_id: Position(2, 0),
        },
    )


def test_push_box_onto_exit() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)],
    )
    exit_id: EntityID = new_entity_id()
    state = replace(
        state,
        exit=state.exit.set(exit_id, Exit()),
        position=state.position.set(exit_id, Position(2, 0)),
        entity=state.entity.set(exit_id, Entity()),
    )
    next_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        next_state,
        {
            agent_id: Position(1, 0),
            box_ids[0]: Position(2, 0),
            exit_id: Position(2, 0),
        },
    )


def test_push_box_onto_portal() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)],
    )
    portal_id: EntityID = new_entity_id()
    paired_portal_id: EntityID = new_entity_id()
    state = replace(
        state,
        portal=state.portal.set(portal_id, Portal(pair_entity=paired_portal_id)).set(
            paired_portal_id, Portal(pair_entity=portal_id),
        ),
        position=state.position.set(portal_id, Position(2, 0)).set(
            paired_portal_id, Position(4, 0),
        ),
        entity=state.entity.set(portal_id, Entity()).set(paired_portal_id, Entity()),
    )
    next_state = push_system(state, agent_id, Position(1, 0))
    # Box should land at (2,0) (portal logic would teleport after push_system, not during push_system itself)
    check_positions(
        next_state,
        {
            agent_id: Position(1, 0),
            box_ids[0]: Position(2, 0),
            portal_id: Position(2, 0),
            paired_portal_id: Position(4, 0),
        },
    )


def test_push_box_onto_agent() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)],
    )
    other_agent_id: EntityID = new_entity_id()
    state = replace(
        state,
        agent=state.agent.set(other_agent_id, Agent()),
        collidable=state.collidable.set(other_agent_id, Collidable()),
        position=state.position.set(other_agent_id, Position(2, 0)),
        inventory=state.inventory.set(other_agent_id, Inventory(pset())),
        entity=state.entity.set(other_agent_id, Entity()),
    )
    next_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        next_state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(1, 0),
            other_agent_id: Position(2, 0),
        },
    )


def test_push_box_left_right_up_down() -> None:
    cases: list[tuple[Action, tuple[int, int], tuple[int, int], tuple[int, int]]] = [
        (Action.RIGHT, (0, 0), (1, 0), (2, 0)),
        (Action.LEFT, (2, 0), (1, 0), (0, 0)),
        (Action.DOWN, (0, 0), (0, 1), (0, 2)),
        (Action.UP, (0, 2), (0, 1), (0, 0)),
    ]
    for direction, agent_p, box_p, dest_p in cases:
        state, agent_id, box_ids, _ = make_push_state(
            agent_pos=agent_p, box_positions=[box_p], width=3, height=3,
        )
        next_box_pos = Position(*dest_p)
        next_state = push_system(state, agent_id, Position(*box_p))
        check_positions(
            next_state,
            {
                agent_id: Position(*box_p),
                box_ids[0]: next_box_pos,
            },
        )


def test_push_box_on_narrow_grid_edge() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(0, 1)], width=1, height=2,
    )
    next_state = push_system(state, agent_id, Position(0, 1))
    check_positions(
        next_state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(0, 1),
        },
    )


def test_push_chain_of_boxes_blocked() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0), (2, 0)],
    )
    next_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        next_state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(1, 0),
            box_ids[1]: Position(2, 0),
        },
    )


def test_push_chain_wall_box_blocked() -> None:
    # Wall at (2,0), box at (1,0) (agent at (0,0)): can't push box because wall blocks chain.
    state, agent_id, box_ids, wall_ids = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)], wall_positions=[(2, 0)],
    )
    next_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        next_state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(1, 0),
            wall_ids[0]: Position(2, 0),
        },
    )


def test_push_chain_box_wall_blocked() -> None:
    # Box at (1,0), wall at (2,0), box at (3,0). Can't push into wall.
    state, agent_id, box_ids, wall_ids = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0), (3, 0)], wall_positions=[(2, 0)],
    )
    next_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        next_state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(1, 0),
            wall_ids[0]: Position(2, 0),
            box_ids[1]: Position(3, 0),
        },
    )


def test_push_box_onto_multiple_collidables() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)],
    )
    collectible_id = new_entity_id()
    exit_id = new_entity_id()
    state = replace(
        state,
        collectible=state.collectible.set(collectible_id, Collectible()),
        exit=state.exit.set(exit_id, Exit()),
        position=state.position.set(collectible_id, Position(2, 0)).set(
            exit_id, Position(2, 0),
        ),
        entity=state.entity.set(collectible_id, Entity()).set(exit_id, Entity()),
    )
    next_state = push_system(state, agent_id, Position(1, 0))
    check_positions(
        next_state,
        {
            agent_id: Position(1, 0),
            box_ids[0]: Position(2, 0),
            collectible_id: Position(2, 0),
            exit_id: Position(2, 0),
        },
    )


def test_push_not_adjacent() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(2, 0)],
    )
    next_state = push_system(state, agent_id, Position(1, 0))
    assert box_ids[0] in next_state.position and next_state.position[
        box_ids[0]
    ] == Position(2, 0)


def test_push_no_pushable_at_destination() -> None:
    state, agent_id, _, _ = make_push_state(agent_pos=(0, 0))
    next_state = push_system(state, agent_id, Position(1, 0))
    assert next_state.position[agent_id] == Position(
        0, 0,
    )  # push system doesn't handle agent movement


def test_push_box_missing_position() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)],
    )
    state = replace(state, position=state.position.remove(box_ids[0]))
    next_state = push_system(state, agent_id, Position(1, 0))
    assert agent_id in next_state.position
    assert box_ids[0] not in next_state.position


def test_push_missing_agent_position() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)],
    )
    state = replace(state, position=state.position.remove(agent_id))
    next_state = push_system(state, agent_id, Position(1, 0))
    assert box_ids[0] in next_state.position
    assert agent_id not in next_state.position


def test_push_box_at_narrow_grid_edge() -> None:
    state, agent_id, box_ids, _ = make_push_state(
        agent_pos=(0, 0), box_positions=[(1, 0)],
    )
    state = replace(state, width=1, height=2)
    state = replace(
        state,
        position=state.position.set(agent_id, Position(0, 0)).set(
            box_ids[0], Position(0, 1),
        ),
    )
    next_state = push_system(state, agent_id, Position(0, 1))
    check_positions(
        next_state,
        {
            agent_id: Position(0, 0),
            box_ids[0]: Position(0, 1),
        },
    )
