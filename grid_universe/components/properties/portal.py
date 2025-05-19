from dataclasses import dataclass


@dataclass(frozen=True)
class Portal:
    pair_entity: int  # Entity ID of the paired portal
