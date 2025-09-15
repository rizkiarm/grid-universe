import os
from typing import Optional
import streamlit.components.v1 as components

script_dir: str = os.path.dirname(os.path.realpath(__file__))
component_name: str = os.path.split(script_dir)[-1]
frontend_dir: str = os.path.join(script_dir, "frontend")

component = components.declare_component(component_name, path=frontend_dir)


def keyup(
    default_text: str = "Default",
    focused_text: str = "Focused",
    key: Optional[str] = None,
    auto_clear: bool = True,
    clear_delay_ms: int = 200,
):
    """Return the last key pressed (once) and then clear it.

    By default Streamlit custom components keep returning the last value that
    was set via ``setComponentValue`` until a new value is provided. This means
    a polling style call pattern will repeatedly receive the same key even if
    no new key was pressed.

    To emulate an event / edge-triggered behavior we optionally (``auto_clear``)
    schedule a second message that sets the component value to ``None`` a short
    time (``clear_delay_ms``) after a key press. This causes subsequent reruns
    of the script to see ``None`` until another key is pressed.

    Args:
        default_text: str
            Text shown when the component is not focused.
        focused_text: str
            Text shown when the window has focus (gives key usage hints).
        key: Optional[str]
            Streamlit widget key (unrelated to keyboard key pressed).
        auto_clear: bool
            Whether to automatically reset the component value to ``None`` after
            emitting a key press. Defaults to True.
        clear_delay_ms: int
            Delay in milliseconds before clearing. Needs to be long enough so the
            first (actual key) message is processed by Streamlit before the clear
            message arrives.
    """
    return component(
        default_text=default_text,
        focused_text=focused_text,
        key=key,
        auto_clear=auto_clear,
        clear_delay_ms=clear_delay_ms,
    )
