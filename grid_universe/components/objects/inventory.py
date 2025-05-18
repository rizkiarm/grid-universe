from dataclasses import dataclass
from pyrsistent import PSet


@dataclass(frozen=True)
class Inventory:
    item_ids: PSet[int]  # Immutable set of item entity IDs (keys, etc.)
