from dataclasses import dataclass


@dataclass(frozen=True)
class Locked:
    key_id: str = ""  # If empty, may mean "locked with no key" or generic lock
