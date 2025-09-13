from dataclasses import dataclass


@dataclass(frozen=True)
class LethalDamage:
    """Marker: entity inflicts fatal damage on contact / interaction.

    Systems detecting collisions or overlaps may directly set a target's
    ``Health`` to zero (or apply sufficient damage) when encountering an
    entity with this component. Presence alone conveys semantics.
    """

    pass
