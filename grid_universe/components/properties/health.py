from dataclasses import dataclass


@dataclass(frozen=True)
class Health:
    health: int
    max_health: int
