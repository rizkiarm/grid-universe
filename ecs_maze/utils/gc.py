from typing import Set

from pyrsistent.typing import PMap
from ecs_maze.state import State
from ecs_maze.types import EntityID


def compute_alive_entities(state: State) -> Set[EntityID]:
    alive: Set[EntityID] = set()
    alive |= set(state.position.keys())
    alive |= set(state.collectible.keys())
    alive |= set(state.agent.keys())
    alive |= set(state.enemy.keys())
    alive |= set(state.box.keys())
    alive |= set(state.key.keys())
    alive |= set(state.portal.keys())
    alive |= set(state.exit.keys())
    for inv in state.inventory.values():
        alive |= set(inv.item_ids)
    return alive


def run_garbage_collector(state: State) -> State:
    alive = compute_alive_entities(state)
    kwargs = {}
    for field in state.__dataclass_fields__:
        value = getattr(state, field)
        # Only clean mappings keyed by int (EntityID), leave everything else untouched
        if isinstance(value, PMap) and value:
            key_sample = next(iter(value.keys()))
            if isinstance(key_sample, EntityID):
                # Keep only entries for alive entities
                filtered = value.filter(lambda eid, _: eid in alive)
                kwargs[field] = filtered
            else:
                kwargs[field] = value
        else:
            kwargs[field] = value
    return State(**kwargs)
