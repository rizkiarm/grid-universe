from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type

from grid_universe.gym_env import GridUniverseEnv


@dataclass
class LevelSource:
    """Plugin describing a level family.

    Attributes:
        name: Human‑readable name shown in UI select box.
        config_type: Dataclass (or similar) type representing this source's config.
        initial_config: Zero‑arg callable returning a default config instance.
        build_config: (current_config) -> new_config, renders Streamlit widgets.
        make_env: (config) -> GridUniverseEnv instance (unreset; caller will reset).
    """

    name: str
    config_type: Type[Any]
    initial_config: Callable[[], Any]
    build_config: Callable[[Any], Any]
    make_env: Callable[[Any], GridUniverseEnv]


_LEVEL_SOURCE_REGISTRY: List[LevelSource] = []
_NAME_INDEX: Dict[str, LevelSource] = {}


def register_level_source(source: LevelSource) -> None:
    if source.name in _NAME_INDEX:
        # Allow overriding for hot‑reload dev convenience; replace entry.
        existing_idx = next(
            i for i, s in enumerate(_LEVEL_SOURCE_REGISTRY) if s.name == source.name
        )
        _LEVEL_SOURCE_REGISTRY[existing_idx] = source
    else:
        _LEVEL_SOURCE_REGISTRY.append(source)
    _NAME_INDEX[source.name] = source


def all_level_sources() -> List[LevelSource]:
    """Return registered sources sorted by name for stable UI ordering."""
    return sorted(_LEVEL_SOURCE_REGISTRY, key=lambda s: s.name.lower())


def find_level_source_by_config(config: object) -> Optional[LevelSource]:
    for src in _LEVEL_SOURCE_REGISTRY:
        if isinstance(config, src.config_type):
            return src
    return None


def find_level_source_by_name(name: str) -> Optional[LevelSource]:
    return _NAME_INDEX.get(name)
