from dataclasses import replace
from typing import Callable, Tuple, List, Type

import pytest
from pyrsistent import pmap, PMap

from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.components import Collidable, Position, Agent, Box, Pushable, Portal
from grid_universe.systems.portal import portal_system

# --- Utility function for state creation ---


def make_entity_on_portal_state(
    entity_id: EntityID,
    entity_component: object,
    portal1_id: EntityID,
    portal2_id: EntityID,
    entity_pos: Tuple[int, int],
    portal1_pos: Tuple[int, int],
    portal2_pos: Tuple[int, int],
) -> State:
    position: PMap[EntityID, Position] = pmap(
        {
            entity_id: Position(*entity_pos),
            portal1_id: Position(*portal1_pos),
            portal2_id: Position(*portal2_pos),
        }
    )
    portal: PMap[EntityID, Portal] = pmap(
        {
            portal1_id: Portal(pair_entity=portal2_id),
            portal2_id: Portal(pair_entity=portal1_id),
        }
    )
    agent: PMap[EntityID, Agent] = (
        pmap({entity_id: entity_component})
        if isinstance(entity_component, Agent)
        else pmap()
    )
    box: PMap[EntityID, Box] = (
        pmap({entity_id: entity_component})
        if isinstance(entity_component, Box)
        else pmap()
    )
    pushable: PMap[EntityID, Pushable] = (
        pmap({entity_id: Pushable()}) if isinstance(entity_component, Box) else pmap()
    )
    collidable: PMap[EntityID, Collidable] = pmap({entity_id: Collidable()})

    empty_pmap: PMap = pmap()
    return State(
        width=10,
        height=10,
        move_fn=lambda s, eid, d: [],
        position=position,
        prev_position=position,  # assume standing still at the beginning
        agent=agent,
        enemy=empty_pmap,
        box=box,
        pushable=pushable,
        wall=empty_pmap,
        door=empty_pmap,
        locked=empty_pmap,
        portal=portal,
        exit=empty_pmap,
        key=empty_pmap,
        collectible=empty_pmap,
        rewardable=empty_pmap,
        cost=empty_pmap,
        item=empty_pmap,
        required=empty_pmap,
        inventory=empty_pmap,
        health=empty_pmap,
        powerup=empty_pmap,
        powerup_status=empty_pmap,
        floor=empty_pmap,
        blocking=empty_pmap,
        dead=empty_pmap,
        moving=empty_pmap,
        hazard=empty_pmap,
        collidable=collidable,
        damage=empty_pmap,
        lethal_damage=empty_pmap,
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )


# --- Parametrized fixtures for entity types ---

EntityType = Tuple[str, Type[object], Callable[[EntityID], object]]
ENTITY_TYPES: List[EntityType] = [
    ("agent", Agent, lambda entity_id: Agent()),
    ("box", Box, lambda entity_id: Box()),
]


@pytest.mark.parametrize("entity_label, entity_cls, entity_factory", ENTITY_TYPES)
def test_entity_standing_on_portal_does_not_teleport(
    entity_label: str,
    entity_cls: Type[object],
    entity_factory: Callable[[EntityID], object],
) -> None:
    """Ensure entity standing on portal tile does not teleport again unless moved."""
    entity_id: EntityID = 1
    portal1_id: EntityID = 2
    portal2_id: EntityID = 3
    entity_pos: Tuple[int, int] = (4, 4)
    portal1_pos: Tuple[int, int] = (4, 4)
    portal2_pos: Tuple[int, int] = (7, 7)

    state: State = make_entity_on_portal_state(
        entity_id,
        entity_factory(entity_id),
        portal1_id,
        portal2_id,
        entity_pos,
        portal1_pos,
        portal2_pos,
    )

    new_state: State = portal_system(state)
    assert new_state.position[entity_id] == Position(*portal1_pos)


@pytest.mark.parametrize("entity_label, entity_cls, entity_factory", ENTITY_TYPES)
def test_entity_teleported_when_entering_portal(
    entity_label: str,
    entity_cls: Type[object],
    entity_factory: Callable[[EntityID], object],
) -> None:
    """Ensure teleport occurs when entity enters portal from a non-portal tile."""
    entity_id: EntityID = 1
    portal1_id: EntityID = 2
    portal2_id: EntityID = 3
    start_pos: Tuple[int, int] = (1, 1)
    portal1_pos: Tuple[int, int] = (4, 4)
    portal2_pos: Tuple[int, int] = (7, 7)

    state: State = make_entity_on_portal_state(
        entity_id,
        entity_factory(entity_id),
        portal1_id,
        portal2_id,
        start_pos,
        portal1_pos,
        portal2_pos,
    )
    # Simulate entity moving onto portal1
    moved_state: State = replace(
        state, position=state.position.set(entity_id, Position(*portal1_pos))
    )
    new_state: State = portal_system(moved_state)
    assert new_state.position[entity_id] == Position(*portal2_pos)


@pytest.mark.parametrize("entity_label, entity_cls, entity_factory", ENTITY_TYPES)
def test_entity_not_teleported_if_not_on_portal(
    entity_label: str,
    entity_cls: Type[object],
    entity_factory: Callable[[EntityID], object],
) -> None:
    """No teleport occurs if entity is not on any portal."""
    entity_id: EntityID = 1
    portal1_id: EntityID = 2
    portal2_id: EntityID = 3
    entity_pos: Tuple[int, int] = (1, 2)
    portal1_pos: Tuple[int, int] = (3, 5)
    portal2_pos: Tuple[int, int] = (7, 7)

    state: State = make_entity_on_portal_state(
        entity_id,
        entity_factory(entity_id),
        portal1_id,
        portal2_id,
        entity_pos,
        portal1_pos,
        portal2_pos,
    )

    new_state: State = portal_system(state)
    assert new_state.position[entity_id] == Position(*entity_pos)


def test_box_teleported_when_pushed_onto_portal() -> None:
    """Box is teleported when pushed onto a portal tile."""
    entity_id: EntityID = 10
    portal1_id: EntityID = 20
    portal2_id: EntityID = 30
    start_pos: Tuple[int, int] = (2, 2)
    portal1_pos: Tuple[int, int] = (4, 4)
    portal2_pos: Tuple[int, int] = (8, 8)
    # Simulate box being pushed onto portal1
    state: State = make_entity_on_portal_state(
        entity_id, Box(), portal1_id, portal2_id, start_pos, portal1_pos, portal2_pos
    )
    moved_state: State = replace(
        state, position=state.position.set(entity_id, Position(*portal1_pos))
    )
    new_state: State = portal_system(moved_state)
    assert new_state.position[entity_id] == Position(*portal2_pos)


def test_portal_pair_missing_does_not_crash() -> None:
    """Teleport on incomplete portal pair does not crash, entity not moved."""
    agent_id: EntityID = 1
    portal1_id: EntityID = 2
    agent_pos: Tuple[int, int] = (2, 2)
    portal1_pos: Tuple[int, int] = (2, 2)
    # Omit portal2
    position: PMap[EntityID, Position] = pmap(
        {
            agent_id: Position(*agent_pos),
            portal1_id: Position(*portal1_pos),
        }
    )
    portal: PMap[EntityID, Portal] = pmap(
        {portal1_id: Portal(pair_entity=999)}  # points to missing portal
    )
    agent: PMap[EntityID, Agent] = pmap({agent_id: Agent()})
    collidable: PMap[EntityID, Collidable] = pmap({agent_id: Collidable()})
    empty_pmap: PMap = pmap()
    state: State = State(
        width=5,
        height=5,
        move_fn=lambda s, eid, d: [],
        position=position,
        agent=agent,
        enemy=empty_pmap,
        box=empty_pmap,
        pushable=empty_pmap,
        wall=empty_pmap,
        door=empty_pmap,
        locked=empty_pmap,
        portal=portal,
        exit=empty_pmap,
        key=empty_pmap,
        collectible=empty_pmap,
        rewardable=empty_pmap,
        cost=empty_pmap,
        item=empty_pmap,
        required=empty_pmap,
        inventory=empty_pmap,
        health=empty_pmap,
        powerup=empty_pmap,
        powerup_status=empty_pmap,
        floor=empty_pmap,
        blocking=empty_pmap,
        dead=empty_pmap,
        moving=empty_pmap,
        hazard=empty_pmap,
        collidable=collidable,
        damage=empty_pmap,
        lethal_damage=empty_pmap,
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
    new_state: State = portal_system(state)
    assert new_state.position[agent_id] == Position(*agent_pos)


def test_multiple_entities_on_portal_all_teleported_on_entry() -> None:
    """Multiple entities entering different portals are all teleported."""
    agent_id: EntityID = 1
    box_id: EntityID = 2
    portal1_id: EntityID = 10
    portal2_id: EntityID = 20
    portal1_pos: Tuple[int, int] = (2, 2)
    portal2_pos: Tuple[int, int] = (7, 7)
    position: PMap[EntityID, Position] = pmap(
        {
            agent_id: Position(*portal1_pos),
            box_id: Position(*portal2_pos),
            portal1_id: Position(*portal1_pos),
            portal2_id: Position(*portal2_pos),
        }
    )
    portal: PMap[EntityID, Portal] = pmap(
        {
            portal1_id: Portal(pair_entity=portal2_id),
            portal2_id: Portal(pair_entity=portal1_id),
        }
    )
    agent: PMap[EntityID, Agent] = pmap({agent_id: Agent()})
    box: PMap[EntityID, Box] = pmap({box_id: Box()})
    pushable: PMap[EntityID, Pushable] = pmap({box_id: Pushable()})
    collidable: PMap[EntityID, Collidable] = pmap(
        {agent_id: Collidable(), box_id: Collidable()}
    )
    empty_pmap: PMap = pmap()
    state: State = State(
        width=10,
        height=10,
        move_fn=lambda s, eid, d: [],
        position=position,
        agent=agent,
        enemy=empty_pmap,
        box=box,
        pushable=pushable,
        wall=empty_pmap,
        door=empty_pmap,
        locked=empty_pmap,
        portal=portal,
        exit=empty_pmap,
        key=empty_pmap,
        collectible=empty_pmap,
        rewardable=empty_pmap,
        cost=empty_pmap,
        item=empty_pmap,
        required=empty_pmap,
        inventory=empty_pmap,
        health=empty_pmap,
        powerup=empty_pmap,
        powerup_status=empty_pmap,
        floor=empty_pmap,
        blocking=empty_pmap,
        dead=empty_pmap,
        moving=empty_pmap,
        hazard=empty_pmap,
        collidable=collidable,
        damage=empty_pmap,
        lethal_damage=empty_pmap,
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
    new_state: State = portal_system(state)
    assert new_state.position[agent_id] == Position(*portal2_pos)
    assert new_state.position[box_id] == Position(*portal1_pos)


def test_entity_chained_portals_no_infinite_teleport() -> None:
    """Entity entering chained portals is teleported once, not in a loop."""
    agent_id: EntityID = 1
    portal_a: EntityID = 10
    portal_b: EntityID = 20
    portal_c: EntityID = 30
    pos_a: Tuple[int, int] = (2, 2)
    pos_b: Tuple[int, int] = (4, 4)
    pos_c: Tuple[int, int] = (6, 6)
    position: PMap[EntityID, Position] = pmap(
        {
            agent_id: Position(*pos_a),
            portal_a: Position(*pos_a),
            portal_b: Position(*pos_b),
            portal_c: Position(*pos_c),
        }
    )
    portal: PMap[EntityID, Portal] = pmap(
        {
            portal_a: Portal(pair_entity=portal_b),
            portal_b: Portal(pair_entity=portal_c),
            portal_c: Portal(pair_entity=portal_a),
        }
    )
    agent: PMap[EntityID, Agent] = pmap({agent_id: Agent()})
    collidable: PMap[EntityID, Collidable] = pmap({agent_id: Collidable()})
    empty_pmap: PMap = pmap()
    state: State = State(
        width=10,
        height=10,
        move_fn=lambda s, eid, d: [],
        position=position,
        agent=agent,
        enemy=empty_pmap,
        box=empty_pmap,
        pushable=empty_pmap,
        wall=empty_pmap,
        door=empty_pmap,
        locked=empty_pmap,
        portal=portal,
        exit=empty_pmap,
        key=empty_pmap,
        collectible=empty_pmap,
        rewardable=empty_pmap,
        cost=empty_pmap,
        item=empty_pmap,
        required=empty_pmap,
        inventory=empty_pmap,
        health=empty_pmap,
        powerup=empty_pmap,
        powerup_status=empty_pmap,
        floor=empty_pmap,
        blocking=empty_pmap,
        dead=empty_pmap,
        moving=empty_pmap,
        hazard=empty_pmap,
        collidable=collidable,
        damage=empty_pmap,
        lethal_damage=empty_pmap,
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
    new_state: State = portal_system(state)
    # Only one teleport: A→B (not B→C or C→A)
    assert new_state.position[agent_id] == Position(*pos_b)
