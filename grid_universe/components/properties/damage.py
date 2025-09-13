"""Damage component (non-lethal)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Damage:
    """Hit point damage applied on contact / crossing."""

    amount: int
