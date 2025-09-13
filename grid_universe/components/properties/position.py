"""Position component.

Immutable integer grid coordinates. Stored in ``State.position`` keyed by
entity id. The ``prev_position`` store records the prior turn's component for
trail / cross detection.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    """Grid coordinate.

    Attributes:
        x: Column index (0 at left).
        y: Row index (0 at top).
    """

    x: int
    y: int
