from typing import TypedDict, TypeVar

from pyrsistent import pmap, pset
from pyrsistent.typing import PMap

from grid_universe.components import (
    Agent,
    Appearance,
    AppearanceName,
    Blocking,
    Collectible,
    Collidable,
    Cost,
    Damage,
    Dead,
    Exit,
    Health,
    Immunity,
    Inventory,
    Key,
    LethalDamage,
    Locked,
    Moving,
    Phasing,
    Portal,
    Position,
    Pushable,
    Required,
    Rewardable,
    Speed,
    Status,
    TimeLimit,
    UsageLimit,
)
from grid_universe.entity import Entity, new_entity_id
from grid_universe.moves import default_move_fn
from grid_universe.objectives import default_objective_fn
from grid_universe.state import State
from grid_universe.types import EntityID, MoveFn, ObjectiveFn


class MinimalEntities(TypedDict):
    agent_id: EntityID
    key_id: EntityID
    door_id: EntityID


def make_minimal_key_door_state() -> tuple[State, MinimalEntities]:
    """Standard key-door ECS state for integration tests."""
    pos: dict[EntityID, Position] = {}
    agent: dict[EntityID, Agent] = {}
    inventory: dict[EntityID, Inventory] = {}
    key: dict[EntityID, Key] = {}
    collectible: dict[EntityID, Collectible] = {}
    locked: dict[EntityID, Locked] = {}
    blocking: dict[EntityID, Blocking] = {}
    collidable: dict[EntityID, Collidable] = {}
    appearance: dict[EntityID, Appearance] = {}
    entity: dict[EntityID, Entity] = {}

    agent_id = new_entity_id()
    key_id = new_entity_id()
    door_id = new_entity_id()
    positions = {
        "agent": (0, 0),
        "key": (0, 1),
        "door": (0, 2),
    }
    pos[agent_id] = Position(*positions["agent"])
    pos[key_id] = Position(*positions["key"])
    pos[door_id] = Position(*positions["door"])
    agent[agent_id] = Agent()
    inventory[agent_id] = Inventory(pset())
    key[key_id] = Key(key_id="red")
    collectible[key_id] = Collectible()
    locked[door_id] = Locked(key_id="red")
    blocking[door_id] = Blocking()
    collidable[agent_id] = Collidable()
    collidable[door_id] = Collidable()
    appearance[agent_id] = Appearance(name=AppearanceName.HUMAN)
    appearance[key_id] = Appearance(name=AppearanceName.KEY)
    appearance[door_id] = Appearance(name=AppearanceName.DOOR)
    entity[agent_id] = Entity()
    entity[key_id] = Entity()
    entity[door_id] = Entity()

    state = State(
        width=3,
        height=3,
        move_fn=default_move_fn,
        objective_fn=default_objective_fn,
        entity=pmap(entity),
        position=pmap(pos),
        agent=pmap(agent),
        locked=pmap(locked),
        key=pmap(key),
        collectible=pmap(collectible),
        inventory=pmap(inventory),
        appearance=pmap(appearance),
        blocking=pmap(blocking),
        collidable=pmap(collidable),
    )
    return state, MinimalEntities(agent_id=agent_id, key_id=key_id, door_id=door_id)


def make_exit_entity(
    position: tuple[int, int],
) -> tuple[
    EntityID, dict[EntityID, Exit], dict[EntityID, Position], dict[EntityID, Entity],
]:
    """Utility to add a single Exit entity at a given position."""
    exit_id = new_entity_id()
    return (
        exit_id,
        {exit_id: Exit()},
        {exit_id: Position(*position)},
        {exit_id: Entity()},
    )


def make_agent_box_wall_state(
    agent_pos: tuple[int, int],
    box_positions: list[tuple[int, int]] | None = None,
    wall_positions: list[tuple[int, int]] | None = None,
    width: int = 5,
    height: int = 5,
) -> tuple[State, EntityID, list[EntityID], list[EntityID]]:
    """Utility for integration: agent + any number of boxes and walls.
    Returns state, agent_id, [box_ids], [wall_ids].
    """
    pos: dict[EntityID, Position] = {}
    agent: dict[EntityID, Agent] = {}
    inventory: dict[EntityID, Inventory] = {}
    pushable: dict[EntityID, Pushable] = {}
    blocking: dict[EntityID, Blocking] = {}
    collidable: dict[EntityID, Collidable] = {}
    appearance: dict[EntityID, Appearance] = {}
    entity: dict[EntityID, Entity] = {}

    agent_id = new_entity_id()
    pos[agent_id] = Position(*agent_pos)
    agent[agent_id] = Agent()
    inventory[agent_id] = Inventory(pset())
    collidable[agent_id] = Collidable()
    appearance[agent_id] = Appearance(name=AppearanceName.HUMAN)
    entity[agent_id] = Entity()

    box_ids: list[EntityID] = []
    if box_positions:
        for bpos in box_positions:
            bid = new_entity_id()
            pos[bid] = Position(*bpos)
            pushable[bid] = Pushable()
            collidable[bid] = Collidable()
            appearance[bid] = Appearance(name=AppearanceName.BOX)
            entity[bid] = Entity()
            box_ids.append(bid)

    wall_ids: list[EntityID] = []
    if wall_positions:
        for wpos in wall_positions:
            wid = new_entity_id()
            pos[wid] = Position(*wpos)
            blocking[wid] = Blocking()
            collidable[wid] = Collidable()
            appearance[wid] = Appearance(name=AppearanceName.WALL)
            entity[wid] = Entity()
            wall_ids.append(wid)

    state = State(
        width=width,
        height=height,
        move_fn=default_move_fn,
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


def assert_entity_positions(
    state: State, expected: dict[EntityID, tuple[int, int]],
) -> None:
    """Check that expected entities are at the right positions."""
    for eid, (x, y) in expected.items():
        actual = state.position.get(eid)
        assert actual == Position(x, y), (
            f"Entity {eid} expected at {(x, y)}, got {actual}"
        )


T = TypeVar("T")


def filter_component_map(
    extra_components: dict[str, dict[EntityID, object]] | None,
    key: str,
    typ: type[T],
) -> dict[EntityID, T]:
    result: dict[EntityID, T] = {}
    if extra_components and key in extra_components:
        for k, v in extra_components[key].items():
            if isinstance(v, typ):
                result[k] = v
    return result


def make_agent_state(
    *,
    agent_pos: tuple[int, int],
    move_fn: MoveFn | None = None,
    objective_fn: ObjectiveFn | None = None,
    extra_components: dict[str, dict[EntityID, object]] | None = None,
    width: int = 5,
    height: int = 5,
    agent_dead: bool = False,
    agent_id: EntityID = 1,
) -> tuple[State, EntityID]:
    positions: dict[EntityID, Position] = {agent_id: Position(*agent_pos)}
    positions.update(filter_component_map(extra_components, "position", Position))

    agent_map: dict[EntityID, Agent] = {agent_id: Agent()}
    inventory: dict[EntityID, Inventory] = {agent_id: Inventory(pset())}
    dead_map: PMap[EntityID, Dead] = pmap({agent_id: Dead()}) if agent_dead else pmap()
    entity: dict[EntityID, Entity] = {agent_id: Entity()}
    for eid in positions:
        if eid not in entity:
            entity[eid] = Entity()

    state: State = State(
        width=width,
        height=height,
        move_fn=move_fn if move_fn is not None else default_move_fn,
        objective_fn=(
            objective_fn if objective_fn is not None else default_objective_fn
        ),
        entity=pmap(entity),
        position=pmap(positions),
        agent=pmap(agent_map),
        pushable=pmap(filter_component_map(extra_components, "pushable", Pushable)),
        locked=pmap(filter_component_map(extra_components, "locked", Locked)),
        portal=pmap(filter_component_map(extra_components, "portal", Portal)),
        exit=pmap(filter_component_map(extra_components, "exit", Exit)),
        key=pmap(filter_component_map(extra_components, "key", Key)),
        collectible=pmap(
            filter_component_map(extra_components, "collectible", Collectible),
        ),
        rewardable=pmap(
            filter_component_map(extra_components, "rewardable", Rewardable),
        ),
        cost=pmap(filter_component_map(extra_components, "cost", Cost)),
        required=pmap(filter_component_map(extra_components, "required", Required)),
        inventory=pmap(inventory),
        health=pmap(filter_component_map(extra_components, "health", Health)),
        appearance=pmap(
            filter_component_map(extra_components, "appearance", Appearance),
        ),
        blocking=pmap(filter_component_map(extra_components, "blocking", Blocking)),
        dead=dead_map,
        moving=pmap(filter_component_map(extra_components, "moving", Moving)),
        collidable=pmap(
            filter_component_map(extra_components, "collidable", Collidable),
        ),
        damage=pmap(filter_component_map(extra_components, "damage", Damage)),
        lethal_damage=pmap(
            filter_component_map(extra_components, "lethal_damage", LethalDamage),
        ),
        immunity=pmap(filter_component_map(extra_components, "immunity", Immunity)),
        phasing=pmap(filter_component_map(extra_components, "phasing", Phasing)),
        speed=pmap(filter_component_map(extra_components, "speed", Speed)),
        time_limit=pmap(
            filter_component_map(extra_components, "time_limit", TimeLimit),
        ),
        usage_limit=pmap(
            filter_component_map(extra_components, "usage_limit", UsageLimit),
        ),
        status=pmap(filter_component_map(extra_components, "status", Status)),
    )
    return state, agent_id
