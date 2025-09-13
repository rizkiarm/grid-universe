"""Agent marker component.

Presence of :class:`Agent` designates the controllable player entity. Only
one agent is typically present; the reducer will select the first if multiple
exist. This component carries no data but enables queries / system routing.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Agent:
    """Marker (no fields)."""

    pass
