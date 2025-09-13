"""Collidable component.

Indicates an entity participates in collision interactions (e.g. portal
entry). Distinct from ``Blocking`` which prevents movement; collidable objects
may coexist with pass-through mechanics.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Collidable:
    """Marker (no data)."""

    pass
