from dataclasses import dataclass


@dataclass(frozen=True)
class Key:
    key_id: str  # 'red', 'blue', etc.
