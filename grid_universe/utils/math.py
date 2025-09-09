from typing import Any

from pyrsistent import pvector
from pyrsistent.typing import PVector

from grid_universe.components import Position


def vector_dot_product(vec1: PVector[int], vec2: PVector[int]) -> int:
    if len(vec1) != len(vec2):
        msg = "Vectors must be of the same length"
        raise ValueError(msg)
    return sum([vec1[i] * vec2[i] for i in range(len(vec1))])


def vector_substract(vec1: PVector[int], vec2: PVector[int]) -> PVector[int]:
    if len(vec1) != len(vec2):
        msg = "Vectors must be of the same length"
        raise ValueError(msg)
    return pvector([vec1[i] - vec2[i] for i in range(len(vec1))])


def position_to_vector(position: Position) -> PVector[int]:
    return pvector(
        [getattr(position, field) for field in position.__dataclass_fields__],
    )


def argmax(x: list[Any]) -> int:
    return max(range(len(x)), key=lambda i: x[i])
