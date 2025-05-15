from dataclasses import dataclass


@dataclass(frozen=True)
class Damage:
    amount: int
