from dataclasses import dataclass


@dataclass(frozen=True)
class Phasing:
    """Effect component: entity ignores blocking collisions.

    When present, movement systems treat the entity as *non-blocking* for the
    purpose of traversing tiles that would normally be obstructed (e.g.
    walls or other blocking entities). Other entities may still collide with
    this entity unless they also have logic that skips blocked checks.

    Typically combined with a :class:`TimeLimit` or :class:`UsageLimit` to make
    the phasing temporary.
    """

    pass
