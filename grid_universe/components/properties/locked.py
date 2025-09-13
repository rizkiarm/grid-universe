from dataclasses import dataclass


@dataclass(frozen=True)
class Locked:
    """Indicates the entity is locked and may require a key to unlock.

    Attributes:
        key_id:
            Identifier of the key required. An empty string can represent a
            generic lock (any key) or a permanently locked state depending on
            objective / system interpretation.
    """

    key_id: str = ""  # If empty, may mean "locked with no key" or generic lock
