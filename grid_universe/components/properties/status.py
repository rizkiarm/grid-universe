"""Status component.

Holds a *set* of effect entity ids the holder currently has active. The
ordering is not semantically relevant (set semantics) but systems iterate the
``PSet`` in deterministic order for reproducibility. Limits (time/usage) are
stored on the effect entities themselves.
"""

from dataclasses import dataclass
from pyrsistent import PSet
from grid_universe.types import EntityID


@dataclass(frozen=True)
class Status:
    """Active effect references.

    Attributes:
        effect_ids: Persistent set of effect entity ids.
    """

    effect_ids: PSet[EntityID]
