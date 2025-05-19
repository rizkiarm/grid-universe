from dataclasses import dataclass


@dataclass(frozen=True)
class Speed:
    multiplier: int
