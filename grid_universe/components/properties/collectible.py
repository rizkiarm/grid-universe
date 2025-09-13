"""Collectible component.

Marks an entity that can be picked up into an agent's inventory. If combined
with :class:`Rewardable` or :class:`Required`, logic in collectible / objective
systems updates score or win conditions at pickup.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Collectible:
    """Marker (no data)."""

    pass
