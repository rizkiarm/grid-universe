"""Entity primitives & ID generation.

The engine models each *thing* as an ``EntityID`` (an integer) plus zero or
more component dataclasses stored in persistent maps on :class:`State`.

This module provides:
* ``Entity``: Thin marker/dataclass – future extension point (metadata,
  debugging hooks). Currently empty by design.
* Deterministic, process‑local monotonic ID generator utilities.

Examples
--------
>>> from grid_universe.entity import new_entity_id, new_entity_ids
>>> eid = new_entity_id()  # allocate a single ID
>>> eids = new_entity_ids(3)  # allocate batch

IDs are *not* recycled; a simple incrementing counter is sufficient because
``State`` is typically short‑lived within an episode/run. If you need stable
serialization across processes, inject your own ID strategy.
"""

from typing import Iterator, List

from grid_universe.types import EntityID


def entity_id_generator() -> Iterator[EntityID]:
    """Yield an infinite sequence of monotonically increasing entity IDs."""
    eid = 0
    while True:
        yield eid
        eid += 1


_entity_id_gen = entity_id_generator()


def new_entity_id() -> EntityID:
    """Return a newly allocated unique entity ID."""
    return next(_entity_id_gen)


def new_entity_ids(n: int) -> List[EntityID]:
    """Return ``n`` fresh entity IDs as a list."""
    return [new_entity_id() for _ in range(n)]


# Example:
# agent_id = new_entity_id()
# box_id, key_id = new_entity_ids(2)
