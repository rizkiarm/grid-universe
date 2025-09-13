from dataclasses import dataclass
from pyrsistent import PSet
from grid_universe.types import EntityID


@dataclass(frozen=True)
class Inventory:
    """Set of owned item entity IDs.

    The immutable ``PSet`` enables O(1) sharing across state copies; adding or
    removing an item produces a new component instance. Other systems (e.g.
    keys, rewards) inspect membership for gating logic.

    Attributes:
        item_ids:
            Persistent set of entity identifiers currently held.
    """

    item_ids: PSet[EntityID]
