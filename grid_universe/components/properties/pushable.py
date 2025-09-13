from dataclasses import dataclass


@dataclass(frozen=True)
class Pushable:
    """Marker indicating the entity can be displaced by another's movement.

    Push mechanics typically trigger when an agent attempts to move into a
    tile occupied by a pushable entity; the system tries to move the pushable
    entity in the same direction if the next tile is free.
    """

    pass
