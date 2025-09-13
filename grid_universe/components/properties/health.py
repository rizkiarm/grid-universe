from dataclasses import dataclass


@dataclass(frozen=True)
class Health:
    """Tracks current and maximum hit points for damage / healing systems.

    Attributes:
        health:
            Current hit points. Systems should clamp this to ``[0, max_health]``.
        max_health:
            Upper bound for ``health``; may be used to normalize UI or compute
            proportional rewards.
    """

    health: int
    max_health: int
