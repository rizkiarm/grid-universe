"""Key item component (pairs with Locked)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Key:
    """Key id string used to unlock matching locked entities."""

    key_id: str  # 'red', 'blue', etc.
