from dataclasses import dataclass


@dataclass(frozen=True)
class Exit:
    """Marks an entity as an exit tile / goal location.

    Objective predicates typically search for agents reaching any entity with
    this component. The component has no fields; presence alone is meaningful.
    """

    pass
