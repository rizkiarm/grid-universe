from __future__ import annotations
from typing import Protocol
import streamlit as st
from grid_universe.renderer.texture import TEXTURE_MAP_REGISTRY, TextureMap


class HasTextureMap(Protocol):
    render_texture_map: TextureMap  # attribute contract for texture selection


def seed_section(key: str) -> int:
    st.subheader("Random seed")
    return st.number_input("Random seed", min_value=0, value=0, key=key)


def texture_map_section(current: HasTextureMap) -> TextureMap:
    st.subheader("Texture Map")
    names = list(TEXTURE_MAP_REGISTRY.keys())
    # Fallback to first if current map missing (defensive during hot reload)
    try:
        current_key = next(
            k
            for k, v in TEXTURE_MAP_REGISTRY.items()
            if v is current.render_texture_map
        )
    except StopIteration:
        current_key = names[0]
    label = st.selectbox(
        "Texture Map",
        names,
        index=names.index(current_key),
        key="texture_map",
    )
    return TEXTURE_MAP_REGISTRY[label]


__all__ = ["seed_section", "texture_map_section", "HasTextureMap"]
