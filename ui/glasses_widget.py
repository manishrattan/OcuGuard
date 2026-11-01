from pathlib import Path

import streamlit.components.v1 as components


GLASSES_COMPONENT = components.declare_component(
    "ocuguard_glasses",
    path=str(Path(__file__).with_name("glasses_component")),
)
