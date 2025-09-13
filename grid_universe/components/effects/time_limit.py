from dataclasses import dataclass


@dataclass(frozen=True)
class TimeLimit:
    """Decorator effect specifying a maximum number of remaining steps.

    Systems decrement the remaining ``amount`` each global step; when it
    reaches zero the wrapped effect (or status) is removed. This enables
    temporary power-ups (e.g. phasing for 5 turns).

    Attributes:
        amount:
            Number of *future* steps for which the associated effect/status is
            still active. Implementations should treat ``amount <= 0`` as expired.
    """

    amount: int
