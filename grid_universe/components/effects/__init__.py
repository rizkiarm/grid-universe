"""Effect component aggregates.

This sub-package defines **effect** components: temporary or conditional
modifiers that decorate entities (e.g. immunity, phasing, speed changes) as
well as limiting wrappers (usage / time limits). Effects are modeled as plain
data objects which systems interpret each step; they do not mutate themselves.

``Effect`` is provided as a convenience union of the *runtime modifying*
effects (currently :class:`Immunity`, :class:`Phasing`, :class:`Speed`). Limit
wrappers (:class:`TimeLimit`, :class:`UsageLimit`) are kept separate because
they can apply to any effect type and are processed by status / GC systems.

Importing::

    from grid_universe.components.effects import Effect, Speed

or via the top-level components package::

    from grid_universe.components import Speed

"""

from typing import Union
from .immunity import Immunity
from .phasing import Phasing
from .speed import Speed
from .time_limit import TimeLimit
from .usage_limit import UsageLimit

Effect = Union[Immunity, Phasing, Speed]

__all__ = [
    "Effect",
    "Immunity",
    "Phasing",
    "Speed",
    "TimeLimit",
    "UsageLimit",
]
