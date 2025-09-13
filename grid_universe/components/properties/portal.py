from dataclasses import dataclass


@dataclass(frozen=True)
class Portal:
    """Teleportation link between two entities.

    Attributes:
        pair_entity:
            Entity ID of the destination/linked portal. When an entity moves onto
            this portal, movement systems may relocate it to the paired portal's
            position (often preserving direction or applying post-teleport rules).
    """

    pair_entity: int  # Entity ID of the paired portal
