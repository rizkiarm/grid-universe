from dataclasses import dataclass


@dataclass(frozen=True)
class UsageLimit:
    """Decorator effect counting down discrete consumptions.

    Rather than expiring with time, a ``UsageLimit`` is decremented by a
    system whenever the wrapped effect is *used* (domain-specific). Typical
    use cases include limited charges (e.g. three teleports) or a fixed number
    of phasing moves.

    Attributes:
        amount:
            Remaining number of uses. When it reaches zero the effect/status
            should be removed.
    """

    amount: int
