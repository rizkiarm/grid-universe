"""Dead marker component (post-mortem)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Dead:
    """Marker set by health/damage logic when HP reaches zero or lethal hit."""

    pass
