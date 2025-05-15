from typing import Dict, Tuple, List, Optional, Type, TypeVar, TypedDict
from pyrsistent import pmap, pset
from pyrsistent.typing import PMap
from ecs_maze.state import State
from ecs_maze.components import (
    Position,
    Agent,
    Inventory,
    Key,
    Collectible,
    Item,
    Door,
    Locked,
    Blocking,
    Collidable,
    Exit,
    Box,
    Pushable,
    Wall,
    Cost,
    Damage,
    Dead,
    Enemy,
    Floor,
    Hazard,
    Health,
    LethalDamage,
    Moving,
    Portal,
    PowerUp,
    PowerUpType,
    Required,
    Rewardable,
)
from ecs_maze.entity import new_entity_id
from ecs_maze.types import EntityID, MoveFn
from ecs_maze.moves import default_move_fn


class MinimalEntities(TypedDict):
    agent_id: EntityID
    key_id: EntityID
    door_id: EntityID


def make_minimal_key_door_state() -> Tuple[State, MinimalEntities]:
    """Standard key-door ECS state for integration tests."""
    pos: Dict[EntityID, Position] = {}
    agent: Dict[EntityID, Agent] = {}
    inventory: Dict[EntityID, Inventory] = {}
    key: Dict[EntityID, Key] = {}
    collectible: Dict[EntityID, Collectible] = {}
    item: Dict[EntityID, Item] = {}
    door: Dict[EntityID, Door] = {}
    locked: Dict[EntityID, Locked] = {}
    blocking: Dict[EntityID, Blocking] = {}
    collidable: Dict[EntityID, Collidable] = {}

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
    item[key_id] = Item()
    door[door_id] = Door()
    locked[door_id] = Locked(key_id="red")
    blocking[door_id] = Blocking()
    collidable[agent_id] = Collidable()
    collidable[door_id] = Collidable()

    state = State(
        width=3,
        height=3,
        move_fn=default_move_fn,
        position=pmap(pos),
        agent=pmap(agent),
        enemy=pmap(),
        box=pmap(),
        pushable=pmap(),
        wall=pmap(),
        door=pmap(door),
        locked=pmap(locked),
        portal=pmap(),
        exit=pmap(),
        key=pmap(key),
        collectible=pmap(collectible),
        rewardable=pmap(),
        cost=pmap(),
        item=pmap(item),
        required=pmap(),
        inventory=pmap(inventory),
        health=pmap(),
        powerup=pmap(),
        powerup_status=pmap(),
        floor=pmap(),
        blocking=pmap(blocking),
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
    return state, MinimalEntities(agent_id=agent_id, key_id=key_id, door_id=door_id)


def make_exit_entity(
    position: Tuple[int, int],
) -> Tuple[EntityID, Dict[EntityID, Exit], Dict[EntityID, Position]]:
    """Utility to add a single Exit entity at a given position."""
    exit_id = new_entity_id()
    return exit_id, {exit_id: Exit()}, {exit_id: Position(*position)}


def make_agent_box_wall_state(
    agent_pos: Tuple[int, int],
    box_positions: Optional[List[Tuple[int, int]]] = None,
    wall_positions: Optional[List[Tuple[int, int]]] = None,
    width: int = 5,
    height: int = 5,
) -> Tuple[State, EntityID, List[EntityID], List[EntityID]]:
    """
    Utility for integration: agent + any number of boxes and walls.
    Returns state, agent_id, [box_ids], [wall_ids].
    """
    pos: Dict[EntityID, Position] = {}
    agent: Dict[EntityID, Agent] = {}
    inventory: Dict[EntityID, Inventory] = {}
    box: Dict[EntityID, Box] = {}
    pushable: Dict[EntityID, Pushable] = {}
    wall: Dict[EntityID, Wall] = {}
    collidable: Dict[EntityID, Collidable] = {}

    agent_id = new_entity_id()
    pos[agent_id] = Position(*agent_pos)
    agent[agent_id] = Agent()
    inventory[agent_id] = Inventory(pset())
    collidable[agent_id] = Collidable()

    box_ids: List[EntityID] = []
    if box_positions:
        for bpos in box_positions:
            bid = new_entity_id()
            pos[bid] = Position(*bpos)
            box[bid] = Box()
            pushable[bid] = Pushable()
            collidable[bid] = Collidable()
            box_ids.append(bid)

    wall_ids: List[EntityID] = []
    if wall_positions:
        for wpos in wall_positions:
            wid = new_entity_id()
            pos[wid] = Position(*wpos)
            wall[wid] = Wall()
            collidable[wid] = Collidable()
            wall_ids.append(wid)

    state = State(
        width=width,
        height=height,
        move_fn=default_move_fn,
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


def make_agent_with_powerup_collectible(
    agent_pos: Tuple[int, int], collectible_pos: Tuple[int, int], powerup: PowerUp
) -> Tuple[State, EntityID, EntityID]:
    agent_id: EntityID = 1
    collectible_id: EntityID = 2

    pos: Dict[EntityID, Position] = {
        agent_id: Position(*agent_pos),
        collectible_id: Position(*collectible_pos),
    }
    agent: PMap[EntityID, Agent] = pmap({agent_id: Agent()})
    inventory: PMap[EntityID, Inventory] = pmap({agent_id: Inventory(pset())})
    collectible: PMap[EntityID, Collectible] = pmap({collectible_id: Collectible()})
    item: PMap[EntityID, Item] = pmap({collectible_id: Item()})
    powerup_map: PMap[EntityID, PowerUp] = pmap({collectible_id: powerup})

    state: State = State(
        width=3,
        height=1,
        move_fn=lambda s, eid, dir: [Position(pos[eid].x + 1, 0)],
        position=pmap(pos),
        agent=agent,
        enemy=pmap(),
        box=pmap(),
        pushable=pmap(),
        wall=pmap(),
        door=pmap(),
        locked=pmap(),
        portal=pmap(),
        exit=pmap(),
        key=pmap(),
        collectible=collectible,
        rewardable=pmap(),
        cost=pmap(),
        item=item,
        required=pmap(),
        inventory=inventory,
        health=pmap({agent_id: Health(health=10, max_health=10)}),
        powerup=powerup_map,
        powerup_status=pmap(),
        floor=pmap(),
        blocking=pmap(),
        dead=pmap(),
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
    return state, agent_id, collectible_id


def assert_entity_positions(
    state: State, expected: Dict[EntityID, Tuple[int, int]]
) -> None:
    """Check that expected entities are at the right positions."""
    for eid, (x, y) in expected.items():
        actual = state.position.get(eid)
        assert actual == Position(x, y), (
            f"Entity {eid} expected at {(x, y)}, got {actual}"
        )


T = TypeVar("T")


def filter_component_map(
    extra_components: Optional[Dict[str, Dict[EntityID, object]]],
    key: str,
    typ: Type[T],
) -> Dict[EntityID, T]:
    result: Dict[EntityID, T] = {}
    if extra_components and key in extra_components:
        for k, v in extra_components[key].items():
            if isinstance(v, typ):
                result[k] = v
    return result


def make_agent_state(
    *,
    agent_pos: Tuple[int, int],
    move_fn: Optional[MoveFn] = None,
    extra_components: Optional[Dict[str, Dict[EntityID, object]]] = None,
    width: int = 5,
    height: int = 5,
    agent_dead: bool = False,
    powerup_status: Optional[PMap[EntityID, PMap[PowerUpType, PowerUp]]] = None,
) -> Tuple[State, EntityID]:
    agent_id: EntityID = 1

    positions: Dict[EntityID, Position] = {agent_id: Position(*agent_pos)}
    positions.update(filter_component_map(extra_components, "position", Position))

    agent_map: Dict[EntityID, Agent] = {agent_id: Agent()}
    inventory: Dict[EntityID, Inventory] = {agent_id: Inventory(pset())}
    dead_map: PMap[EntityID, Dead] = pmap({agent_id: Dead()}) if agent_dead else pmap()
    powerup_status_map: PMap[EntityID, PMap[PowerUpType, PowerUp]] = (
        powerup_status if powerup_status else pmap()
    )

    state: State = State(
        width=width,
        height=height,
        move_fn=move_fn if move_fn is not None else default_move_fn,
        position=pmap(positions),
        agent=pmap(agent_map),
        enemy=pmap(filter_component_map(extra_components, "enemy", Enemy)),
        box=pmap(filter_component_map(extra_components, "box", Box)),
        pushable=pmap(filter_component_map(extra_components, "pushable", Pushable)),
        wall=pmap(filter_component_map(extra_components, "wall", Wall)),
        door=pmap(filter_component_map(extra_components, "door", Door)),
        locked=pmap(filter_component_map(extra_components, "locked", Locked)),
        portal=pmap(filter_component_map(extra_components, "portal", Portal)),
        exit=pmap(filter_component_map(extra_components, "exit", Exit)),
        key=pmap(filter_component_map(extra_components, "key", Key)),
        collectible=pmap(
            filter_component_map(extra_components, "collectible", Collectible)
        ),
        rewardable=pmap(
            filter_component_map(extra_components, "rewardable", Rewardable)
        ),
        cost=pmap(filter_component_map(extra_components, "cost", Cost)),
        item=pmap(filter_component_map(extra_components, "item", Item)),
        required=pmap(filter_component_map(extra_components, "required", Required)),
        inventory=pmap(inventory),
        health=pmap(filter_component_map(extra_components, "health", Health)),
        powerup=pmap(filter_component_map(extra_components, "powerup", PowerUp)),
        powerup_status=powerup_status_map,
        floor=pmap(filter_component_map(extra_components, "floor", Floor)),
        blocking=pmap(filter_component_map(extra_components, "blocking", Blocking)),
        dead=dead_map,
        moving=pmap(filter_component_map(extra_components, "moving", Moving)),
        hazard=pmap(filter_component_map(extra_components, "hazard", Hazard)),
        collidable=pmap(
            filter_component_map(extra_components, "collidable", Collidable)
        ),
        damage=pmap(filter_component_map(extra_components, "damage", Damage)),
        lethal_damage=pmap(
            filter_component_map(extra_components, "lethal_damage", LethalDamage)
        ),
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
    )
    return state, agent_id
