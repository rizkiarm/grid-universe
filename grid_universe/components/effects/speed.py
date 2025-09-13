"""Speed effect component.

Multiplies the number of movement sub‑steps performed for a movement action.
Each sub‑step triggers post‑movement interaction systems, allowing rapid chain
effects (e.g. portal + damage) within a single logical action.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Speed:
    """Movement multiplier.

    Attributes:
        multiplier: Positive integer factor applied to base 1 movement steps.
    """

    multiplier: int
