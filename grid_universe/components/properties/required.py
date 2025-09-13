from dataclasses import dataclass


@dataclass(frozen=True)
class Required:
    """Marker signifying an entity must satisfy a condition to progress.

    Often attached to goal or exit entities to indicate prerequisites (such as
    possessing certain items) must be met; interpretation is handled by
    objective or validation systems.
    """

    pass
