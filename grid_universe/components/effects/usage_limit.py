from dataclasses import dataclass


@dataclass(frozen=True)
class UsageLimit:
    amount: int
