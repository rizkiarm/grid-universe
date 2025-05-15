from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    x: int
    y: int
