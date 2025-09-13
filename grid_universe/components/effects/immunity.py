"""Immunity effect component (negates incoming damage instances)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Immunity:
    """Marker (no data)."""

    pass
