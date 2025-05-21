import os
from typing import Optional
import streamlit.components.v1 as components

script_dir: str = os.path.dirname(os.path.realpath(__file__))
component_name: str = os.path.split(script_dir)[-1]
frontend_dir: str = os.path.join(script_dir, "frontend")

component = components.declare_component(component_name, path=frontend_dir)


def keyup(
    default_text: str = "Click here to use keyboard",
    focused_text: str = "W,A,S,D to move, E to collect, F to use key, and Q to wait",
    key: Optional[str] = None,
):
    return component(default_text=default_text, focused_text=focused_text, key=key)
