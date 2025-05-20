from collections import defaultdict
from pyrsistent import pmap, pset
from pyrsistent.typing import PMap, PSet
from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID


def get_augmented_trail(
    state: State, entity_ids: PSet[EntityID]
) -> PMap[Position, PSet[EntityID]]:
    pos_to_eids = defaultdict(set)
    for eid in entity_ids:
        if eid not in state.position:
            continue
        pos = state.position[eid]
        pos_to_eids[pos].add(eid)
    # Merge with existing trail:
    for pos, eid_set in state.trail.items():
        pos_to_eids[pos].update(eid_set)
    # Convert to persistent structures:
    return pmap({pos: pset(eids) for pos, eids in pos_to_eids.items()})
