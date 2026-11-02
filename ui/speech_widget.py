from pathlib import Path

import streamlit.components.v1 as components


SPEECH_COMPONENT = components.declare_component(
    "ocuguard_speech_input",
    path=str(Path(__file__).with_name("speech_component")),
)
