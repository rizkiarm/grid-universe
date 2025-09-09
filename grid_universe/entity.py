from collections.abc import Iterator
from dataclasses import dataclass

from grid_universe.types import EntityID


@dataclass(frozen=True)
class Entity:
    pass


"""
Entity ID management for ECS.

- Entities are always integer IDs.
- This module provides a simple, globally unique entity ID generator and helper functions.
"""


# Simple auto-incrementing integer ID generator
def entity_id_generator() -> Iterator[EntityID]:
    eid = 0
    while True:
        yield eid
        eid += 1


# Create a global generator instance
_entity_id_gen = entity_id_generator()


def new_entity_id() -> EntityID:
    """Get a new unique entity ID."""
    return next(_entity_id_gen)


def new_entity_ids(n: int) -> list[EntityID]:
    return [new_entity_id() for _ in range(n)]


# Example usage for ECS systems and level initialization:
# agent_id = new_entity_id()
# box_id, key_id = new_entity_ids(2)
