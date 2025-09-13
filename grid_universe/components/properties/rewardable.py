from dataclasses import dataclass


@dataclass(frozen=True)
class Rewardable:
    """Specifies a scalar reward granted upon satisfying a condition.

    Systems can award the ``amount`` (e.g., reinforcement learning signal)
    when the entity is collected, reached, or otherwise triggered by an agent.

    Attributes:
        amount:
            Numeric reward value to emit; magnitude and sign semantics are up to
            the environment integration.
    """

    amount: int
