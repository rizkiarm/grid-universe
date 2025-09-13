"""Blocking component.

Marks an entity as occupying its tile for purposes of movement collision.
Ignored for entities with active Phasing effect.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Blocking:
    """Marker (no data)."""

    pass
