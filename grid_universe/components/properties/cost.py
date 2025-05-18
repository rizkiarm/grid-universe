from dataclasses import dataclass


@dataclass(frozen=True)
class Cost:
    amount: int
