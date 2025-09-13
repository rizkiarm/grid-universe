"""Tile movement cost component (per-step penalty)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Cost:
    """Movement cost applied once per logical action when on this tile."""

    amount: int
