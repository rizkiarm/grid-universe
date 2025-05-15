from typing import Optional, List, Dict, Tuple, Set
import random
from pyrsistent import PMap, pmap, pset

from ecs_maze.state import State
from ecs_maze.entity import new_entity_id
from ecs_maze.components import (
    Position,
    Agent,
    Wall,
    Box,
    Pushable,
    Moving,
    Collectible,
    Rewardable,
    Required,
    Key,
    Locked,
    Door,
    Portal,
    Inventory,
    Exit,
    Health,
    PowerUp,
    PowerUpType,
    Hazard,
    HazardType,
    Enemy,
    PowerUpLimit,
    Item,
    Floor,
    Collidable,
    Blocking,
    Damage,
    LethalDamage,
    Cost,
)
from ecs_maze.moves import default_move_fn
from ecs_maze.types import EntityID, HazardSpec, MoveFn, PowerupSpec, EnemySpec

from ecs_maze.utils.maze import (
    generate_perfect_maze,
    all_required_path_positions,
    adjust_maze_wall_percentage,
)

DEFAULT_POWERUPS: List[PowerupSpec] = [
    (PowerUpType.GHOST, PowerUpLimit.DURATION, 5),
    (PowerUpType.SHIELD, PowerUpLimit.USAGE, 5),
    (PowerUpType.HAZARD_IMMUNITY, PowerUpLimit.DURATION, 5),
    (PowerUpType.DOUBLE_SPEED, PowerUpLimit.DURATION, 5),
]

DEFAULT_HAZARDS: List[HazardSpec] = [
    (HazardType.LAVA, 5, True),
    (HazardType.SPIKE, 3, False),
]

DEFAULT_ENEMIES: List[EnemySpec] = [
    (5, True, True),
    (3, False, False),
]


def place_floors(
    floor_tiles: List[Tuple[int, int]],
    position: Dict[EntityID, Position],
    cost: Dict[EntityID, Cost],
    floor: Dict[EntityID, Floor],
    floor_cost: int = 1,
) -> None:
    for pos in floor_tiles:
        eid: EntityID = new_entity_id()
        floor[eid] = Floor()
        cost[eid] = Cost(amount=floor_cost)
        position[eid] = Position(*pos)


def place_agent(
    position: Dict[EntityID, Position],
    agent: Dict[EntityID, Agent],
    inventory: Dict[EntityID, Inventory],
    health: Dict[EntityID, Health],
    collidable: Dict[EntityID, Collidable],
    start_pos: Tuple[int, int],
    powerup_status: Dict[EntityID, PMap[PowerUpType, PowerUp]],
    agent_health: int,
) -> EntityID:
    agent_id: EntityID = new_entity_id()
    agent[agent_id] = Agent()
    position[agent_id] = Position(*start_pos)
    inventory[agent_id] = Inventory(pset())
    health[agent_id] = Health(health=agent_health, max_health=agent_health)
    collidable[agent_id] = Collidable()
    empty_powerup_status: PMap[PowerUpType, PowerUp] = pmap()
    powerup_status[agent_id] = empty_powerup_status
    return agent_id


def place_exit(
    position: Dict[EntityID, Position],
    exit_store: Dict[EntityID, Exit],
    goal_pos: Tuple[int, int],
) -> None:
    exit_id: EntityID = new_entity_id()
    exit_store[exit_id] = Exit()
    position[exit_id] = Position(*goal_pos)


def place_items(
    n: int,
    position: Dict[EntityID, Position],
    collectible: Dict[EntityID, Collectible],
    item: Dict[EntityID, Item],
    rewardable: Optional[Dict[EntityID, Rewardable]] = None,
    required: Optional[Dict[EntityID, Required]] = None,
    positions_source: List[Tuple[int, int]] = [],
    reward: Optional[int] = None,
) -> List[Tuple[int, int]]:
    used_positions: List[Tuple[int, int]] = []
    for _ in range(n):
        if not positions_source:
            break
        tpos = positions_source.pop()
        tid: EntityID = new_entity_id()
        item[tid] = Item()
        collectible[tid] = Collectible()
        if rewardable is not None and reward is not None:
            rewardable[tid] = Rewardable(reward=reward)
        if required is not None:
            required[tid] = Required()
        position[tid] = Position(*tpos)
        used_positions.append(tpos)
    return used_positions


def place_pushable_boxes(
    n: int,
    position: Dict[EntityID, Position],
    box: Dict[EntityID, Box],
    pushable: Dict[EntityID, Pushable],
    blocking: Dict[EntityID, Blocking],
    collidable: Dict[EntityID, Collidable],
    positions_source: List[Tuple[int, int]],
) -> None:
    for _ in range(n):
        if not positions_source:
            break
        bx_pos = positions_source.pop()
        bid: EntityID = new_entity_id()
        box[bid] = Box()
        pushable[bid] = Pushable()
        blocking[bid] = Blocking()
        collidable[bid] = Collidable()
        position[bid] = Position(*bx_pos)


def place_moving_boxes(
    n: int,
    position: Dict[EntityID, Position],
    box: Dict[EntityID, Box],
    blocking: Dict[EntityID, Blocking],
    collidable: Dict[EntityID, Collidable],
    moving: Dict[EntityID, Moving],
    positions_source: List[Tuple[int, int]],
    rng: random.Random,
) -> None:
    for _ in range(n):
        if not positions_source:
            break
        mbx_pos = positions_source.pop()
        mbid: EntityID = new_entity_id()
        box[mbid] = Box()
        blocking[mbid] = Blocking()
        collidable[mbid] = Collidable()
        moving[mbid] = Moving(
            axis=rng.choice(["horizontal", "vertical"]), direction=rng.choice([-1, 1])
        )
        position[mbid] = Position(*mbx_pos)


def place_portals(
    n: int,
    position: Dict[EntityID, Position],
    portal: Dict[EntityID, Portal],
    positions_source: List[Tuple[int, int]],
) -> None:
    for _ in range(n):
        if len(positions_source) < 2:
            break
        p1 = positions_source.pop()
        p2 = positions_source.pop()
        id1: EntityID = new_entity_id()
        id2: EntityID = new_entity_id()
        portal[id1] = Portal(pair_entity=id2)
        portal[id2] = Portal(pair_entity=id1)
        position[id1] = Position(*p1)
        position[id2] = Position(*p2)


def place_doors_and_keys(
    n: int,
    position: Dict[EntityID, Position],
    key: Dict[EntityID, Key],
    collectible: Dict[EntityID, Collectible],
    item: Dict[EntityID, Item],
    door: Dict[EntityID, Door],
    blocking: Dict[EntityID, Blocking],
    locked: Dict[EntityID, Locked],
    positions_source: List[Tuple[int, int]],
) -> None:
    for i in range(n):
        if len(positions_source) < 2:
            break
        key_pos = positions_source.pop()
        lock_pos = positions_source.pop()
        kid: EntityID = new_entity_id()
        lid: EntityID = new_entity_id()
        key[kid] = Key(key_id=f"key{i}")
        collectible[kid] = Collectible()
        item[kid] = Item()
        position[kid] = Position(*key_pos)
        door[lid] = Door()
        blocking[lid] = Blocking()
        locked[lid] = Locked(key_id=f"key{i}")
        position[lid] = Position(*lock_pos)


def place_enemies(
    enemies: List[EnemySpec],
    position: Dict[EntityID, Position],
    enemy: Dict[EntityID, Enemy],
    damage: Dict[EntityID, Damage],
    lethal_damage: Dict[EntityID, LethalDamage],
    collidable: Dict[EntityID, Collidable],
    positions_source: List[Tuple[int, int]],
    moving: Dict[EntityID, Moving],
    rng: Optional[random.Random] = None,
) -> None:
    if rng is None:
        rng = random.Random()
    for damage_amount, lethal, is_moving in enemies:
        if not positions_source:
            break
        epos = positions_source.pop()
        eid: EntityID = new_entity_id()
        enemy[eid] = Enemy()
        if lethal:
            lethal_damage[eid] = LethalDamage()
        else:
            damage[eid] = Damage(amount=damage_amount)
        position[eid] = Position(*epos)
        collidable[eid] = Collidable()
        if is_moving:
            moving[eid] = Moving(
                axis=rng.choice(["horizontal", "vertical"]),
                direction=rng.choice([-1, 1]),
            )


def place_powerups(
    powerups: List[PowerupSpec],
    position: Dict[EntityID, Position],
    collectible: Dict[EntityID, Collectible],
    powerup: Dict[EntityID, PowerUp],
    positions_source: List[Tuple[int, int]],
) -> None:
    for pu_type, limit_type, remaining in powerups:
        if not positions_source:
            break
        pu_pos = positions_source.pop()
        pu_id: EntityID = new_entity_id()
        powerup[pu_id] = PowerUp(type=pu_type, limit=limit_type, remaining=remaining)
        collectible[pu_id] = Collectible()
        position[pu_id] = Position(*pu_pos)


def place_hazards(
    hazards: List[HazardSpec],
    maze_grid: Dict[Tuple[int, int], bool],
    essential_path: Set[Tuple[int, int]],
    damage: Dict[EntityID, Damage],
    lethal_damage: Dict[EntityID, LethalDamage],
    position: Dict[EntityID, Position],
    hazard: Dict[EntityID, Hazard],
    positions_source: List[Tuple[int, int]],
    start_pos: Tuple[int, int],
    goal_pos: Tuple[int, int],
    rng: random.Random,
) -> None:
    candidates = [
        pos
        for pos in positions_source
        if pos not in essential_path and pos != goal_pos and pos != start_pos
    ]
    for htype, damage_amount, lethal in hazards:
        if len(candidates) == 0:
            break
        pos = candidates.pop()
        hid: EntityID = new_entity_id()
        hazard[hid] = Hazard(type=htype)
        if lethal:
            lethal_damage[hid] = LethalDamage()
        else:
            damage[hid] = Damage(amount=damage_amount)
        position[hid] = Position(*pos)


def place_walls(
    maze_grid: Dict[Tuple[int, int], bool],
    position: Dict[EntityID, Position],
    wall: Dict[EntityID, Wall],
) -> None:
    for pos, open_ in maze_grid.items():
        if not open_:
            wid: EntityID = new_entity_id()
            wall[wid] = Wall()
            position[wid] = Position(*pos)


def generate(
    width: int,
    height: int,
    num_required_items: int,
    num_rewardable_items: int,
    num_boxes: int,
    num_moving_boxes: int,
    num_portals: int,
    num_doors: int,
    agent_health: int = 5,
    floor_cost: int = 1,
    required_item_reward: int = 10,
    rewardable_item_reward: int = 10,
    powerups: List[PowerupSpec] = DEFAULT_POWERUPS,
    hazards: List[HazardSpec] = DEFAULT_HAZARDS,
    enemies: List[EnemySpec] = DEFAULT_ENEMIES,
    wall_percentage: float = 0.8,
    move_fn: MoveFn = default_move_fn,
    seed: Optional[int] = None,
) -> State:
    rng: random.Random = random.Random(seed)
    maze_grid: Dict[Tuple[int, int], bool] = generate_perfect_maze(width, height, rng)
    # for _ in range((width * height) // 5):
    #     x: int = rng.randint(1, width - 2)
    #     y: int = rng.randint(1, height - 2)
    #     maze_grid[(x, y)] = True
    maze_grid = adjust_maze_wall_percentage(maze_grid, wall_percentage, rng)

    # Component dicts, fully typed
    position: Dict[EntityID, Position] = {}
    agent: Dict[EntityID, Agent] = {}
    wall: Dict[EntityID, Wall] = {}
    floor: Dict[EntityID, Floor] = {}
    box: Dict[EntityID, Box] = {}
    pushable: Dict[EntityID, Pushable] = {}
    moving: Dict[EntityID, Moving] = {}
    blocking: Dict[EntityID, Blocking] = {}
    collectible: Dict[EntityID, Collectible] = {}
    rewardable: Dict[EntityID, Rewardable] = {}
    cost: Dict[EntityID, Cost] = {}
    item: Dict[EntityID, Item] = {}
    required: Dict[EntityID, Required] = {}
    key: Dict[EntityID, Key] = {}
    inventory: Dict[EntityID, Inventory] = {}
    exit_store: Dict[EntityID, Exit] = {}
    locked: Dict[EntityID, Locked] = {}
    door: Dict[EntityID, Door] = {}
    portal: Dict[EntityID, Portal] = {}
    powerup: Dict[EntityID, PowerUp] = {}
    hazard: Dict[EntityID, Hazard] = {}
    health: Dict[EntityID, Health] = {}
    enemy: Dict[EntityID, Enemy] = {}
    collidable: Dict[EntityID, Collidable] = {}
    powerup_status: Dict[EntityID, PMap[PowerUpType, PowerUp]] = {}
    damage: Dict[EntityID, Damage] = {}
    lethal_damage: Dict[EntityID, LethalDamage] = {}

    # Tiles setup
    floor_tiles: List[Tuple[int, int]] = [
        pos for pos, open_ in maze_grid.items() if open_
    ]
    rng.shuffle(floor_tiles)

    # Floor
    place_floors(floor_tiles[:], position, cost, floor, floor_cost)

    # Agent/exit
    start_pos: Tuple[int, int] = floor_tiles.pop()
    place_agent(
        position,
        agent,
        inventory,
        health,
        collidable,
        start_pos,
        powerup_status,
        agent_health,
    )
    goal_pos: Tuple[int, int] = floor_tiles.pop()
    place_exit(position, exit_store, goal_pos)

    # Required collectibles
    required_positions: List[Tuple[int, int]] = place_items(
        num_required_items,
        position,
        collectible,
        item,
        rewardable,
        required,
        floor_tiles,
        reward=required_item_reward,
    )

    # Rewardable collectibles
    place_items(
        num_rewardable_items,
        position,
        collectible,
        item,
        rewardable,
        None,
        floor_tiles,
        reward=rewardable_item_reward,
    )

    # Static boxes
    place_pushable_boxes(
        num_boxes, position, box, pushable, blocking, collidable, floor_tiles
    )

    # Moving boxes
    place_moving_boxes(
        num_moving_boxes, position, box, blocking, collidable, moving, floor_tiles, rng
    )

    # Portals
    place_portals(num_portals, position, portal, floor_tiles)

    # Doors/keys
    place_doors_and_keys(
        num_doors, position, key, collectible, item, door, blocking, locked, floor_tiles
    )

    # Enemies
    place_enemies(
        enemies,
        position,
        enemy,
        damage,
        lethal_damage,
        collidable,
        floor_tiles,
        moving,
        rng=rng,
    )

    # Powerups
    place_powerups(powerups, position, collectible, powerup, floor_tiles)

    # Essential path for hazard placement
    essential_path: Set[Tuple[int, int]] = all_required_path_positions(
        maze_grid, start_pos, required_positions, goal_pos
    )
    place_hazards(
        hazards,
        maze_grid,
        essential_path,
        damage,
        lethal_damage,
        position,
        hazard,
        floor_tiles,
        start_pos,
        goal_pos,
        rng,
    )

    # Walls
    place_walls(maze_grid, position, wall)

    # Assemble State
    return State(
        move_fn=move_fn,
        position=pmap(position),
        prev_position=pmap(position),  # assume standing still at the beginning
        agent=pmap(agent),
        enemy=pmap(enemy),
        box=pmap(box),
        pushable=pmap(pushable),
        wall=pmap(wall),
        door=pmap(door),
        locked=pmap(locked),
        portal=pmap(portal),
        exit=pmap(exit_store),
        key=pmap(key),
        collectible=pmap(collectible),
        rewardable=pmap(rewardable),
        cost=pmap(cost),
        item=pmap(item),
        required=pmap(required),
        inventory=pmap(inventory),
        health=pmap(health),
        powerup=pmap(powerup),
        powerup_status=pmap(powerup_status),
        floor=pmap(floor),
        blocking=pmap(blocking),
        dead=pmap(),
        moving=pmap(moving),
        hazard=pmap(hazard),
        collidable=pmap(collidable),
        damage=pmap(damage),
        lethal_damage=pmap(lethal_damage),
        turn=0,
        score=0,
        win=False,
        lose=False,
        message=None,
        width=width,
        height=height,
    )
