from typing import Any, List
from pyrsistent import pvector
from pyrsistent.typing import PVector

from grid_universe.components import Position


def vector_dot_product(vec1: PVector[int], vec2: PVector[int]) -> int:
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must be of the same length")
    return sum([vec1[i] * vec2[i] for i in range(len(vec1))])


def vector_subtract(vec1: PVector[int], vec2: PVector[int]) -> PVector[int]:
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must be of the same length")
    return pvector([vec1[i] - vec2[i] for i in range(len(vec1))])


def position_to_vector(position: Position) -> PVector[int]:
    return pvector(
        [getattr(position, field) for field in position.__dataclass_fields__]
    )


def argmax(x: List[Any]) -> int:
    return max(range(len(x)), key=lambda i: x[i])
