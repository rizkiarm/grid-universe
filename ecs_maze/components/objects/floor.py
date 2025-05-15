from dataclasses import dataclass


@dataclass(frozen=True)
class Floor:
    cost: int = 1
