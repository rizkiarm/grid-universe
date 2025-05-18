from dataclasses import dataclass


@dataclass(frozen=True)
class Rewardable:
    reward: int
