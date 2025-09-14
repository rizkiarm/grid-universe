"""Trail aggregation helpers.

Produces augmented trail maps merging current positions of specific entities
with previously recorded traversed positions. Used by portal and potential
AoE/effect systems to reason about *paths taken* rather than only endpoints.
"""

from collections import defaultdict
from typing import DefaultDict, Set
from pyrsistent import pmap, pset
from pyrsistent.typing import PMap, PSet
from grid_universe.components import Position
from grid_universe.state import State
from grid_universe.types import EntityID


def get_augmented_trail(
    state: State, entity_ids: PSet[EntityID]
) -> PMap[Position, PSet[EntityID]]:
    """Return merged mapping of positions to entity sets (current + historic).

    Args:
        state (State): Current immutable world state containing both live entity positions
            and the accumulated historic ``trail`` mapping of prior positions.
        entity_ids (PSet[EntityID]): Entity ids whose current position should be merged
            into the historic trail. Entities absent from ``state.position`` are ignored.

    Returns:
        PMap[Position, PSet[EntityID]]: Mapping from grid positions to the persistent set of
            entity ids that have either previously occupied (historic) or currently occupy
            that position among the provided tracked entities.
    """
    pos_to_eids: DefaultDict[Position, Set[EntityID]] = defaultdict(set)
    for eid in entity_ids:
        if eid not in state.position:
            continue
        pos = state.position[eid]
        pos_to_eids[pos].add(eid)
    # Merge with existing trail:
    for pos, eid_set in state.trail.items():
        # ``eid_set`` is already a persistent set; its items are EntityID.
        pos_to_eids[pos].update(eid_set)
    # Convert to persistent structures:
    return pmap({pos: pset(eids) for pos, eids in pos_to_eids.items()})
