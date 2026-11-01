"""OcuGuard Studio dashboard page."""

from __future__ import annotations

import hashlib
import html
import io
import json
import math
import struct
import time
import uuid
import wave
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

from glasses_widget import GLASSES_COMPONENT


API_TIMEOUT_SECONDS = 15
DEFAULT_API_URL = "http://127.0.0.1:5000"
DEFAULT_MCP_MESSAGES_URL = "http://127.0.0.1:3000/messages"
DEMO_VALUES_PATH = Path(__file__).with_name("demo_values.json")
ORIENTATION_DEMO_THRESHOLD = -30.0
DRAG_MCP_TIMEOUT_SECONDS = 3.0
MCP_SEVERITY_COLORS = {
    "GREEN": "#42d392",
    "YELLOW": "#f5b942",
    "URGENT": "#ff6670",
    "UNKNOWN": "#94a3b8",
}
WARNING_STATUSES = {
    "VIOLATION",
    "ESCALATION",
    "ELEVATED_ALERT",
    "CRITICAL_ALERT",
}

MODE_DETAILS = {
    "EYE_SENTINEL": {
        "agent": "Eye Sentinel",
        "title": "Text pattern experiment",
        "description": "Legacy-named text and telemetry response path. Not symptom assessment.",
        "strength": "Processes supplied text and telemetry patterns into a prototype status and explanation.",
    },
    "OCUGUARD_CORE": {
        "agent": "OcuGuard Core (built-in rules)",
        "title": "Orientation thresholds",
        "description": "Applies prototype rules to supplied orientation values.",
        "strength": "Checks supplied pitch values against configured demo thresholds.",
    },
    "GAZE_COMPASS": {
        "agent": "Gaze Compass",
        "title": "Coordinate alignment",
        "description": "Uses supplied coordinates; it does not track objects from a camera.",
        "strength": "Maps supplied target and blind-spot coordinates to an experimental direction cue.",
    },
    "TABULAR_LAYOUT_SPEECH": {
        "agent": "Tabular Layout Speech",
        "title": "Text and table structure",
        "description": "Transforms supplied text into an audio-oriented outline; no OCR or audio playback.",
        "strength": "Structures supplied text into a layout-oriented outline for downstream assistive presentation.",
    },
    "ERGONOMIC_SCHEDULE": {
        "agent": "Ergonomic Schedule",
        "title": "Posture-duration experiment",
        "description": "Processes a supplied posture-hold duration.",
        "strength": "Evaluates a supplied duration against prototype posture-prompt rules; it does not track posture.",
    },
    "AMBIENT_LUMINANCE": {
        "agent": "Ambient Luminance",
        "title": "Light and contrast experiment",
        "description": "Processes supplied environment values; it does not control lenses or displays.",
        "strength": "Combines supplied light and contrast values into an experimental text suggestion.",
    },
    "BE_MY_EYES": {
        "agent": "Be My Eyes (local prototype mode)",
        "title": "Supplied-frame processing",
        "description": "No live human-helper connection is implemented.",
        "strength": "Processes supplied frame metadata; it does not open a human-helper session.",
    },
    "ANISEIKONIA_SCALING": {
        "agent": "Aniseikonia Scaling",
        "title": "Text scaling transform",
        "description": "Returns an experimental transform from a supplied size-difference value.",
        "strength": "Produces a text-scale transform from a supplied perceived-size value.",
    },
    "METAMORPHOPSIA_GRID_REMAPPER": {
        "agent": "Metamorphopsia Grid Remapper",
        "title": "Grid transform",
        "description": "Returns an experimental layout transform from a supplied waviness value.",
        "strength": "Produces an experimental grid/layout transform from a supplied waviness value.",
    },
    "BIOFEEDBACK_ANXIETY_SENTINEL": {
        "agent": "Biofeedback Anxiety Sentinel",
        "title": "Text and score experiment",
        "description": "Processes supplied text and a score; it is not a health assessment.",
        "strength": "Processes supplied text and a numeric demo score; it does not assess health or anxiety.",
    },
}

MODE_VALUE_FIELDS = {
    "EYE_SENTINEL": (),
    "OCUGUARD_CORE": ("pitch", "roll", "yaw"),
    "GAZE_COMPASS": (
        "gaze_x",
        "gaze_y",
        "target_x",
        "target_y",
        "blind_x",
        "blind_y",
        "blind_r",
    ),
    "TABULAR_LAYOUT_SPEECH": (),
    "ERGONOMIC_SCHEDULE": ("posture_hold_duration",),
    "AMBIENT_LUMINANCE": ("ambient_light_intensity", "contrast_adaptation_mode"),
    "BE_MY_EYES": (),
    "ANISEIKONIA_SCALING": ("perceived_size_delta",),
    "METAMORPHOPSIA_GRID_REMAPPER": ("text_wavy_index",),
    "BIOFEEDBACK_ANXIETY_SENTINEL": ("vocal_stress_score",),
}

CONTRAST_MODES = ("standard", "high_contrast", "low_contrast")


def _load_demo_values() -> tuple[str, dict[str, dict[str, object]]]:
    try:
        raw_values = json.loads(DEMO_VALUES_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError(f"Demo values file not found: {DEMO_VALUES_PATH}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Demo values file is not valid JSON: {DEMO_VALUES_PATH}"
        ) from error

    if not isinstance(raw_values, dict):
        raise ValueError("Demo values JSON must contain an object.")

    default_mode = raw_values.get("default_mode")
    if not isinstance(default_mode, str) or default_mode not in MODE_DETAILS:
        raise ValueError("Demo values default_mode must name a supported mode.")

    modes = raw_values.get("modes")
    if not isinstance(modes, dict) or set(modes) != set(MODE_DETAILS):
        raise ValueError("Demo values must define exactly the supported API modes.")

    presets: dict[str, dict[str, object]] = {}
    for mode, required_fields in MODE_VALUE_FIELDS.items():
        preset = modes[mode]
        if not isinstance(preset, dict):
            raise ValueError(f"Demo values for {mode} must be an object.")

        input_text = preset.get("input_string")
        values = preset.get("values")
        if not isinstance(input_text, str) or not isinstance(values, dict):
            raise ValueError(
                f"Demo values for {mode} require input_string and values fields."
            )

        missing_fields = [field for field in required_fields if field not in values]
        if missing_fields:
            raise ValueError(
                f"Demo values for {mode} are missing: {', '.join(missing_fields)}."
            )
        for field in required_fields:
            value = values[field]
            if field == "contrast_adaptation_mode":
                if not isinstance(value, str) or value not in CONTRAST_MODES:
                    raise ValueError(
                        f"Demo value {mode}.{field} must be a supported contrast mode."
                    )
            elif isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Demo value {mode}.{field} must be numeric.")

        presets[mode] = {"input_string": input_text, "values": values}

    return default_mode, presets


DEFAULT_MODE, DEMO_PRESETS = _load_demo_values()


def _preset_number(mode: str, field: str) -> float:
    preset_values = DEMO_PRESETS[mode]["values"]
    if not isinstance(preset_values, dict):
        raise ValueError(f"Demo values for {mode} are malformed.")
    value = preset_values.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Demo value {mode}.{field} must be numeric.")
    return float(value)


def _preset_text(mode: str) -> str:
    value = DEMO_PRESETS[mode]["input_string"]
    if not isinstance(value, str):
        raise ValueError(f"Demo input_string for {mode} must be text.")
    return value


def _preset_values(mode: str) -> dict[str, object]:
    values = DEMO_PRESETS[mode]["values"]
    if not isinstance(values, dict):
        raise ValueError(f"Demo values for {mode} are malformed.")
    return values


def _orientation_demo_is_dangerous(pitch: float) -> bool:
    return pitch < ORIENTATION_DEMO_THRESHOLD


def _mcp_severity(status: object) -> str:
    normalized_status = str(status).strip().upper()
    if normalized_status in {"SAFE", "GREEN", "INFORMATION", "STANDARD_LOG"}:
        return "GREEN"
    if normalized_status in {"URGENT", "ESCALATION", "CRITICAL_ALERT"}:
        return "URGENT"
    if normalized_status in {
        "WARN",
        "WARNING",
        "VIOLATION",
        "ELEVATED_ALERT",
        "SCHEDULED_HABIT",
        "ENVIRONMENTAL_OPTIMIZATION",
        "ADAPTIVE_GUIDANCE",
    }:
        return "YELLOW"
    return "UNKNOWN"


def _handle_glasses_orientation_change() -> None:
    event = st.session_state.get("glasses_orientation")
    if not isinstance(event, dict) or event.get("source") != "drag":
        return

    session_id = event.get("sessionId")
    sequence = event.get("sequence")
    if not isinstance(session_id, str) or not session_id:
        st.session_state["mcp_error"] = "The glasses simulator sent an invalid session."
        return
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        st.session_state["mcp_error"] = "The glasses simulator sent an invalid update."
        return

    previous_session = st.session_state.get("glasses_session_id")
    previous_sequence = st.session_state.get("glasses_sequence", 0)
    if session_id == previous_session and sequence <= previous_sequence:
        return

    orientation: dict[str, int] = {}
    for axis, minimum, maximum in (
        ("pitch", -90, 90),
        ("roll", -180, 180),
        ("yaw", -180, 180),
    ):
        value = event.get(axis)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not minimum <= value <= maximum
        ):
            st.session_state["mcp_error"] = (
                f"The glasses simulator sent an invalid {axis} value."
            )
            return
        orientation[axis] = round(value)

    st.session_state["glasses_session_id"] = session_id
    st.session_state["glasses_sequence"] = sequence
    st.session_state["demo_pitch"] = orientation["pitch"]
    st.session_state["demo_roll"] = orientation["roll"]
    st.session_state["demo_yaw"] = orientation["yaw"]
    st.session_state["pending_glasses_orientation"] = orientation


def _elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 1)


def _evaluate_mcp_frame(
    messages_url: str,
    frame_payload: dict[str, object],
    timeout_seconds: float = API_TIMEOUT_SECONDS,
) -> tuple[dict[str, object] | None, str | None, float]:
    request_payload = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex,
        "method": "tools/call",
        "params": {
            "name": "evaluate_wearable_stream",
            "arguments": frame_payload,
        },
    }
    started_at = time.perf_counter()
    try:
        response = requests.post(
            messages_url.strip(),
            json=request_payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.Timeout:
        return None, "MCP request timed out.", _elapsed_ms(started_at)
    except requests.exceptions.HTTPError as error:
        code = error.response.status_code if error.response is not None else "unknown"
        return None, f"MCP endpoint returned HTTP {code}.", _elapsed_ms(started_at)
    except requests.exceptions.JSONDecodeError:
        return None, "MCP endpoint returned invalid JSON.", _elapsed_ms(started_at)
    except requests.exceptions.RequestException as error:
        return (
            None,
            f"Could not reach MCP endpoint ({type(error).__name__}).",
            _elapsed_ms(started_at),
        )

    if not isinstance(payload, dict):
        return None, "MCP endpoint returned an invalid JSON-RPC response.", _elapsed_ms(started_at)
    error_payload = payload.get("error")
    if isinstance(error_payload, dict):
        message = error_payload.get("message", "MCP request failed.")
        return None, str(message), _elapsed_ms(started_at)
    result = payload.get("result")
    if not isinstance(result, dict):
        return None, "MCP response did not contain a result object.", _elapsed_ms(started_at)
    if result.get("isError") is True:
        return None, "MCP tool reported an execution error.", _elapsed_ms(started_at)
    structured = result.get("structuredContent")
    if not isinstance(structured, dict):
        return None, "MCP tool response did not contain structured output.", _elapsed_ms(started_at)
    data = structured.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("status"), str):
        return None, "MCP tool response did not contain a status.", _elapsed_ms(started_at)
    return data, None, _elapsed_ms(started_at)


def _warning_tone_wav() -> bytes:
    sample_rate = 22050
    samples = bytearray()
    for frequency, duration in ((740.0, 0.16), (0.0, 0.08), (520.0, 0.22)):
        sample_count = int(sample_rate * duration)
        for index in range(sample_count):
            if frequency == 0:
                sample = 0
            else:
                fade = min(1.0, index / 180.0, (sample_count - index) / 260.0)
                amplitude = int(
                    0.22
                    * 32767
                    * fade
                    * math.sin(2 * math.pi * frequency * index / sample_rate)
                )
                sample = max(-32768, min(32767, amplitude))
            samples.extend(struct.pack("<h", sample))

    output = io.BytesIO()
    with wave.open(output, "wb") as tone:
        tone.setnchannels(1)
        tone.setsampwidth(2)
        tone.setframerate(sample_rate)
        tone.writeframes(samples)
    return output.getvalue()


def _check_api(api_url: str) -> tuple[bool, str]:
    try:
        response = requests.get(
            f"{api_url.rstrip('/')}/health",
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        health = response.json()
    except requests.exceptions.Timeout:
        return False, "Health check timed out."
    except requests.exceptions.HTTPError as error:
        code = error.response.status_code if error.response is not None else "unknown"
        return False, f"Health check returned HTTP {code}."
    except requests.exceptions.JSONDecodeError:
        return False, "Health endpoint returned invalid JSON."
    except requests.exceptions.RequestException as error:
        return False, f"Could not reach REST API ({type(error).__name__})."

    if isinstance(health, dict) and health.get("status") == "healthy":
        return True, "REST API is reachable."
    return False, "Health endpoint returned an unexpected response."


def _evaluate_frame(
    api_url: str, payload: dict[str, object]
) -> tuple[dict[str, object] | None, str | None, float]:
    start_time = time.perf_counter()
    try:
        response = requests.post(
            f"{api_url.rstrip('/')}/v1/stream/evaluate",
            json=payload,
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.Timeout:
        error_message = "REST API request timed out."
    except requests.exceptions.HTTPError as error:
        code = error.response.status_code if error.response is not None else "unknown"
        error_message = f"REST API returned HTTP {code}; review the selected mode and values."
    except requests.exceptions.JSONDecodeError:
        error_message = "REST API response was not valid JSON."
    except requests.exceptions.RequestException as error:
        error_message = f"REST API request failed ({type(error).__name__})."
    else:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
        if not isinstance(result, dict) or not isinstance(result.get("data"), dict):
            return None, "REST API response did not match the expected JSON shape.", elapsed_ms
        return result, None, elapsed_ms

    return None, error_message, round((time.perf_counter() - start_time) * 1000, 1)


def _append_activity(
    mode: str,
    status: str,
    pitch: float,
    roll: float,
    yaw: float,
    latency_ms: float | None = None,
) -> None:
    events = st.session_state.setdefault("activity_events", [])
    event = {
        "time": datetime.now().astimezone().strftime("%H:%M:%S"),
        "mode": mode,
        "status": status,
        "pitch": pitch,
        "roll": roll,
        "yaw": yaw,
        "latency_ms": latency_ms,
    }
    events.insert(0, event)
    del events[8:]


st.set_page_config(
    page_title="OcuGuard Studio",
    page_icon="O",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(ellipse at 18% 0%, rgba(35, 91, 130, .2), transparent 34%),
            #080d18;
        color: #f1f5f9;
    }
    [data-testid="stAppViewContainer"] h1,
    [data-testid="stAppViewContainer"] h2,
    [data-testid="stAppViewContainer"] h3,
    [data-testid="stAppViewContainer"] h4,
    [data-testid="stAppViewContainer"] h5,
    [data-testid="stAppViewContainer"] h6,
    [data-testid="stAppViewContainer"] label,
    [data-testid="stAppViewContainer"] [data-testid="stWidgetLabel"],
    [data-testid="stAppViewContainer"] [data-testid="stMetricLabel"],
    [data-testid="stAppViewContainer"] [data-testid="stMetricValue"],
    [data-testid="stAppViewContainer"] [data-testid="stMetricDelta"] {
        color: #f1f5f9 !important;
    }
    [data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] {
        color: #d3deec !important;
        opacity: 1;
    }
    [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] li {
        color: #e2e8f0 !important;
    }
    [data-testid="stAppViewContainer"] [data-testid="stTextInput"] input,
    [data-testid="stAppViewContainer"] [data-testid="stTextArea"] textarea,
    [data-testid="stAppViewContainer"] [data-testid="stNumberInput"] input {
        background-color: #10182a !important;
        border: 1px solid #53677f !important;
        color: #f8fafc !important;
        caret-color: #70d7cf;
    }
    [data-testid="stAppViewContainer"] [data-testid="stTextInput"] input::placeholder,
    [data-testid="stAppViewContainer"] [data-testid="stTextArea"] textarea::placeholder {
        color: #b0bfd3 !important;
        opacity: 1;
    }
    [data-testid="stAppViewContainer"] button[data-testid="stBaseButton-secondary"] {
        background-color: #1b2b40 !important;
        border: 1px solid #53677f !important;
        color: #f8fafc !important;
    }
    [data-testid="stAppViewContainer"] button[data-testid="stBaseButton-secondary"]:hover {
        background-color: #263b52 !important;
        border-color: #70d7cf !important;
    }
    [data-testid="stAppViewContainer"] button[data-testid="stBaseButton-primary"] {
        background-color: #2563eb !important;
        border: 1px solid #60a5fa !important;
        color: #ffffff !important;
    }
    [data-testid="stAppViewContainer"] button[data-testid="stBaseButton-primary"]:hover {
        background-color: #1d4ed8 !important;
    }
    [data-testid="stAppViewContainer"] button[data-testid="stBaseButton-secondary"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stAppViewContainer"] button[data-testid="stBaseButton-primary"] [data-testid="stMarkdownContainer"] p {
        color: #f8fafc !important;
    }
    [data-testid="stAppViewContainer"] button[data-testid="stBaseButton-secondary"]:focus-visible,
    [data-testid="stAppViewContainer"] button[data-testid="stBaseButton-primary"]:focus-visible,
    [data-testid="stAppViewContainer"] [data-testid="stTextInput"] input:focus,
    [data-testid="stAppViewContainer"] [data-testid="stTextArea"] textarea:focus,
    [data-testid="stAppViewContainer"] [data-testid="stNumberInput"] input:focus {
        outline: 2px solid #70d7cf !important;
        outline-offset: 2px;
    }
    [data-testid="stAppViewContainer"] [data-testid="stAlert"] {
        background: #142238;
        border: 1px solid #334b67;
        color: #f1f5f9;
    }
    [data-testid="stAppViewContainer"] [data-testid="stAlert"] p {
        color: #f1f5f9 !important;
    }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1680px; padding: 1.4rem 1.5rem 2rem; }
    div[data-testid="stMetric"] {
        background: rgba(16, 24, 42, .78);
        border: 1px solid rgba(148, 163, 184, .17);
        border-radius: .7rem;
        padding: .65rem .85rem;
    }
    .brand-mark {
        display: inline-flex; align-items: center; justify-content: center;
        width: 2.45rem; height: 2.45rem; border-radius: .72rem;
        color: #07121e; background: linear-gradient(135deg,#70d7cf,#5b8dff);
        font-weight: 900; font-size: 1rem; margin-right: .65rem;
        vertical-align: middle;
    }
    .brand-subtitle {
        color: #b0bfd3; font-size: .73rem; letter-spacing: .14em;
        text-transform: uppercase; margin-left: 3.2rem; margin-top: -.25rem;
    }
    .status-pill {
        display: inline-block; border-radius: 999px; padding: .42rem .75rem;
        background: #111a2b; border: 1px solid #28364d;
        color: #d7e1ef; font: 700 .73rem ui-monospace, monospace;
        letter-spacing: .06em; text-transform: uppercase;
    }
    .status-dot {
        display: inline-block; width: .5rem; height: .5rem; border-radius: 50%;
        margin-right: .4rem; background: #8796ad;
    }
    .status-dot.connected { background: #70d7cf; }
    .status-dot.error { background: #f0ad68; }
    .warning-strip {
        border: 1px solid rgba(112, 215, 207, .24);
        border-left: 4px solid #70d7cf; border-radius: .65rem;
        background: rgba(16, 24, 42, .85); padding: .72rem .95rem;
        color: #dce8f3; margin: .45rem 0 1.15rem;
    }
    .result-label {
        border-radius: .55rem; padding: .65rem .8rem; font-weight: 800;
        letter-spacing: .08em; text-align: center; text-transform: uppercase;
        background: #14283a; color: #a7e6df; border: 1px solid #2c5e65;
    }
    .result-label.warning {
        background: #33241f; color: #ffd2ad; border-color: #895b3e;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "demo_user_id" not in st.session_state:
    st.session_state["demo_user_id"] = f"demo-{uuid.uuid4().hex[:8]}"
if "api_health_state" not in st.session_state:
    st.session_state["api_health_state"] = "not-checked"
if "last_api_result" not in st.session_state:
    st.session_state["last_api_result"] = None
if "last_api_mode" not in st.session_state:
    st.session_state["last_api_mode"] = None
if "play_demo_warning_cue" not in st.session_state:
    st.session_state["play_demo_warning_cue"] = False
if "mcp_result" not in st.session_state:
    st.session_state["mcp_result"] = None
if "mcp_error" not in st.session_state:
    st.session_state["mcp_error"] = None
if "mcp_frame_signature" not in st.session_state:
    st.session_state["mcp_frame_signature"] = None
if "play_mcp_demo_cue" not in st.session_state:
    st.session_state["play_mcp_demo_cue"] = False
if "glasses_session_id" not in st.session_state:
    st.session_state["glasses_session_id"] = None
if "glasses_sequence" not in st.session_state:
    st.session_state["glasses_sequence"] = 0

header_brand, header_status = st.columns([4, 1], vertical_alignment="center")
with header_brand:
    st.markdown(
        '<span class="brand-mark">OG</span><strong>OcuGuard Studio</strong>'
        '<div class="brand-subtitle">Accessibility prototype lab</div>',
        unsafe_allow_html=True,
    )
with header_status:
    api_state = st.session_state["api_health_state"]
    if api_state == "connected":
        dot_class, label = "connected", "Rest API connected"
    elif api_state == "unavailable":
        dot_class, label = "error", "Rest API unavailable"
    else:
        dot_class, label = "", "Rest API not checked"
    st.markdown(
        f'<div style="text-align:right"><span class="status-pill">'
        f'<span class="status-dot {dot_class}"></span>{label}</span></div>',
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="warning-strip"><strong>Simulation only.</strong> '
    "No wearable or patient is connected. Use synthetic values; outputs and sound cues "
    "are unvalidated demo behavior, not care or safety guidance.</div>",
    unsafe_allow_html=True,
)
default_pitch = _preset_number("OCUGUARD_CORE", "pitch")
default_roll = _preset_number("OCUGUARD_CORE", "roll")
default_yaw = _preset_number("OCUGUARD_CORE", "yaw")
if not -90.0 <= default_pitch <= 90.0:
    raise ValueError("OCUGUARD_CORE pitch preset must be between -90 and 90 degrees.")
if not -180.0 <= default_roll <= 180.0 or not -180.0 <= default_yaw <= 180.0:
    raise ValueError("OCUGUARD_CORE roll/yaw presets exceed simulator limits.")

for key, value in (
    ("demo_pitch", int(default_pitch)),
    ("demo_roll", int(default_roll)),
    ("demo_yaw", int(default_yaw)),
):
    if key not in st.session_state:
        st.session_state[key] = value

control_column, scene_column, insight_column = st.columns(
    [0.26, 0.49, 0.25], gap="medium"
)

with control_column:
    with st.container(border=True):
        st.subheader("Simulation controls")
        api_url = st.text_input(
            "REST API URL",
            value=DEFAULT_API_URL,
            key="api_base_url",
            help="The Flask API base address. Default: http://127.0.0.1:5000",
        )
        if st.button("Check API connection", use_container_width=True):
            is_connected, health_message = _check_api(api_url)
            st.session_state["api_health_state"] = (
                "connected" if is_connected else "unavailable"
            )
            _append_activity(
                "HEALTH_CHECK",
                "CONNECTED" if is_connected else "UNAVAILABLE",
                float(st.session_state["demo_pitch"]),
                float(st.session_state["demo_roll"]),
                float(st.session_state["demo_yaw"]),
            )
            if is_connected:
                st.success(health_message)
            else:
                st.warning(health_message)

        st.divider()
        selected_mode = st.selectbox(
            "Agent to evaluate",
            options=list(MODE_DETAILS),
            index=list(MODE_DETAILS).index(DEFAULT_MODE),
            format_func=lambda mode: MODE_DETAILS[mode]["agent"],
        )
        st.caption(f"Mode: `{selected_mode}`")
        st.caption(MODE_DETAILS[selected_mode]["description"])

        sample_text = st.text_area(
            "Synthetic OCR / text payload",
            value=_preset_text(selected_mode),
            height=82,
            key=f"sample-text-{selected_mode}",
            help="Synthetic text only; no camera or OCR is connected. Some modes may call an external model.",
        )

        preset_columns = st.columns(2)
        if preset_columns[0].button("Neutral demo", use_container_width=True):
            st.session_state["demo_pitch"] = 0
            st.session_state["demo_roll"] = 0
            st.session_state["demo_yaw"] = 0
        if preset_columns[1].button("Threshold demo", use_container_width=True):
            st.session_state["demo_pitch"] = -35
            st.session_state["demo_roll"] = 0
            st.session_state["demo_yaw"] = 0

        pitch = float(
            st.slider(
            "Pitch (X-axis)",
            min_value=-90,
            max_value=90,
            step=1,
            key="demo_pitch",
            help="Simulated pitch orientation from -90° to +90°.",
            )
        )
        roll = float(
            st.slider(
                "Roll (Z-axis)",
                min_value=-180,
                max_value=180,
                step=1,
                key="demo_roll",
                help="Full 360° roll range (-180° to +180°).",
            )
        )
        yaw = float(
            st.slider(
                "Yaw (Y-axis)",
                min_value=-180,
                max_value=180,
                step=1,
                key="demo_yaw",
                help="Full 360° rotation range (-180° to +180°).",
            )
        )
        st.caption("Orientation coverage: pitch ±90° · roll 360° · yaw 360°.")

        st.markdown("**Synthetic profile flags**")
        risk_left, risk_right = st.columns(2)
        cataract_surgery = risk_left.checkbox(
            "cataract_surgery",
            key="synthetic-cataract-surgery",
            help="Synthetic test flag only; not a medical risk assessment.",
        )
        retinal_disease = risk_right.checkbox(
            "retinal_disease",
            key="synthetic-retinal-disease",
            help="Synthetic test flag only; not a medical risk assessment.",
        )
        history_flags = {
            "cataract_surgery": cataract_surgery,
            "retinal_disease": retinal_disease,
        }
        st.caption("Flags are sent only with the synthetic MCP request.")
        mcp_messages_url = st.text_input(
            "MCP /messages endpoint",
            value=DEFAULT_MCP_MESSAGES_URL,
            key="mcp_messages_url",
            help="Stateless JSON-RPC endpoint. Default: http://127.0.0.1:3000/messages",
        )

        extra_fields: dict[str, object] = {}
        values = _preset_values(selected_mode)
        if selected_mode == "GAZE_COMPASS":
            st.markdown("**Coordinate inputs**")
            gaze_column, target_column = st.columns(2)
            extra_fields["gaze_x"] = gaze_column.number_input(
                "Gaze X", value=_preset_number(selected_mode, "gaze_x"), step=0.1, key="gaze-x"
            )
            extra_fields["gaze_y"] = gaze_column.number_input(
                "Gaze Y", value=_preset_number(selected_mode, "gaze_y"), step=0.1, key="gaze-y"
            )
            extra_fields["target_x"] = target_column.number_input(
                "Target X", value=_preset_number(selected_mode, "target_x"), step=0.1, key="target-x"
            )
            extra_fields["target_y"] = target_column.number_input(
                "Target Y", value=_preset_number(selected_mode, "target_y"), step=0.1, key="target-y"
            )
            extra_fields["blind_x"] = st.number_input(
                "Blind-spot X", value=_preset_number(selected_mode, "blind_x"), step=0.1, key="blind-x"
            )
            extra_fields["blind_y"] = st.number_input(
                "Blind-spot Y", value=_preset_number(selected_mode, "blind_y"), step=0.1, key="blind-y"
            )
            extra_fields["blind_r"] = st.number_input(
                "Blind-spot radius",
                min_value=0.0,
                value=_preset_number(selected_mode, "blind_r"),
                step=0.05,
                key="blind-radius",
            )
        elif selected_mode == "ERGONOMIC_SCHEDULE":
            extra_fields["posture_hold_duration"] = st.number_input(
                "Demo duration (seconds)",
                min_value=0.0,
                value=_preset_number(selected_mode, "posture_hold_duration"),
                step=5.0,
                key="posture-duration",
            )
        elif selected_mode == "AMBIENT_LUMINANCE":
            extra_fields["ambient_light_intensity"] = st.slider(
                "Ambient light (demo scale)",
                min_value=0.0,
                max_value=100.0,
                value=_preset_number(selected_mode, "ambient_light_intensity"),
                key="ambient-light",
            )
            contrast_value = values["contrast_adaptation_mode"]
            if not isinstance(contrast_value, str) or contrast_value not in CONTRAST_MODES:
                raise ValueError("AMBIENT_LUMINANCE contrast preset is unsupported.")
            extra_fields["contrast_adaptation_mode"] = st.selectbox(
                "Contrast mode",
                options=list(CONTRAST_MODES),
                index=CONTRAST_MODES.index(contrast_value),
                key="contrast-mode",
            )
        elif selected_mode == "ANISEIKONIA_SCALING":
            extra_fields["perceived_size_delta"] = st.number_input(
                "Size difference (demo value)",
                value=_preset_number(selected_mode, "perceived_size_delta"),
                step=0.05,
                key="size-delta",
            )
        elif selected_mode == "METAMORPHOPSIA_GRID_REMAPPER":
            extra_fields["text_wavy_index"] = st.number_input(
                "Grid variation (demo value)",
                min_value=0.0,
                value=_preset_number(selected_mode, "text_wavy_index"),
                step=0.05,
                key="grid-variation",
            )
        elif selected_mode == "BIOFEEDBACK_ANXIETY_SENTINEL":
            extra_fields["vocal_stress_score"] = st.number_input(
                "Demo score",
                min_value=0.0,
                value=_preset_number(selected_mode, "vocal_stress_score"),
                step=0.1,
                key="demo-score",
            )

        play_warning_cue = st.toggle(
            "Play demo sound for warning labels",
            value=True,
            help="When enabled, plays a short demo tone after a warning response, including during glasses dragging. It is not a real-world alert.",
        )
        evaluate_clicked = st.button(
            "Evaluate synthetic frame",
            type="primary",
            use_container_width=True,
        )
        mcp_clicked = st.button(
            "Send synthetic OCR to MCP",
            use_container_width=True,
        )

frame_payload: dict[str, object] = {
    "user_id": st.session_state["demo_user_id"],
    "input_string": sample_text,
    "agent_mode": selected_mode,
    "pitch": pitch,
    "roll": roll,
    "yaw": yaw,
    **extra_fields,
}
frame_signature = hashlib.sha256(
    json.dumps(frame_payload, sort_keys=True, default=str).encode("utf-8")
).hexdigest()
mcp_frame_payload = {**frame_payload, "history": history_flags}
mcp_frame_signature = hashlib.sha256(
    json.dumps(
        {"endpoint": mcp_messages_url.strip(), "frame": mcp_frame_payload},
        sort_keys=True,
        default=str,
    ).encode("utf-8")
).hexdigest()

if evaluate_clicked:
    if not sample_text.strip():
        st.session_state["last_api_result"] = None
        st.session_state["last_api_mode"] = None
        st.session_state["last_api_error"] = "Enter synthetic input text before evaluation."
        st.session_state["play_demo_warning_cue"] = False
        _append_activity(selected_mode, "INVALID_INPUT", pitch, roll, yaw)
    else:
        result, api_error, latency_ms = _evaluate_frame(api_url, frame_payload)
        st.session_state["last_api_result"] = result
        st.session_state["last_api_error"] = api_error
        if result is not None:
            st.session_state["api_health_state"] = "connected"
            st.session_state["last_evaluation_signature"] = frame_signature
            st.session_state["last_response_latency_ms"] = latency_ms
            result_data = result.get("data")
            if not isinstance(result_data, dict):
                st.session_state["last_api_result"] = None
                st.session_state["last_api_mode"] = None
                st.session_state["last_api_error"] = (
                    "REST API response did not contain a data object."
                )
                st.session_state["last_evaluation_signature"] = None
                st.session_state["play_demo_warning_cue"] = False
                _append_activity(
                    selected_mode, "API_ERROR", pitch, roll, yaw, latency_ms
                )
            else:
                st.session_state["last_api_mode"] = selected_mode
                status_value = result_data.get("status", "UNKNOWN")
                status = str(status_value)
                st.session_state["play_demo_warning_cue"] = (
                    play_warning_cue and status in WARNING_STATUSES
                )
                _append_activity(
                    selected_mode, status, pitch, roll, yaw, latency_ms
                )
        else:
            st.session_state["api_health_state"] = "unavailable"
            st.session_state["last_api_mode"] = None
            st.session_state["last_evaluation_signature"] = None
            st.session_state["play_demo_warning_cue"] = False
            _append_activity(
                selected_mode, "API_ERROR", pitch, roll, yaw, latency_ms
            )

drag_orientation = st.session_state.pop("pending_glasses_orientation", None)
drag_evaluation = isinstance(drag_orientation, dict)
if mcp_clicked or drag_evaluation:
    if not sample_text.strip():
        st.session_state["mcp_result"] = None
        st.session_state["mcp_error"] = "Enter synthetic OCR/text before sending to MCP."
        st.session_state["mcp_frame_signature"] = None
        st.session_state["play_mcp_demo_cue"] = False
        _append_activity("MCP", "INVALID_INPUT", pitch, roll, yaw)
    elif not mcp_messages_url.strip():
        st.session_state["mcp_result"] = None
        st.session_state["mcp_error"] = "Enter an MCP /messages endpoint URL."
        st.session_state["mcp_frame_signature"] = None
        st.session_state["play_mcp_demo_cue"] = False
        _append_activity("MCP", "INVALID_ENDPOINT", pitch, roll, yaw)
    else:
        mcp_data, mcp_error, mcp_latency_ms = _evaluate_mcp_frame(
            mcp_messages_url,
            mcp_frame_payload,
            timeout_seconds=(
                DRAG_MCP_TIMEOUT_SECONDS if drag_evaluation else API_TIMEOUT_SECONDS
            ),
        )
        st.session_state["mcp_result"] = mcp_data
        st.session_state["mcp_error"] = mcp_error
        st.session_state["mcp_frame_signature"] = (
            mcp_frame_signature if mcp_data is not None else None
        )
        severity = (
            _mcp_severity(mcp_data.get("status"))
            if mcp_data is not None
            else "UNKNOWN"
        )
        st.session_state["play_mcp_demo_cue"] = (
            play_warning_cue and severity in {"YELLOW", "URGENT"}
        )
        _append_activity(
            f"MCP:{selected_mode}" if not drag_evaluation else f"DRAG:{selected_mode}",
            severity if mcp_data is not None else "MCP_ERROR",
            pitch,
            roll,
            yaw,
            mcp_latency_ms,
        )

with scene_column:
    result = st.session_state.get("last_api_result")
    last_api_mode = st.session_state.get("last_api_mode")
    last_signature = st.session_state.get("last_evaluation_signature")
    is_stale = result is not None and last_signature != frame_signature
    mcp_result = st.session_state.get("mcp_result")
    mcp_signature = st.session_state.get("mcp_frame_signature")
    mcp_is_stale = isinstance(mcp_result, dict) and mcp_signature != mcp_frame_signature
    mcp_severity = (
        _mcp_severity(mcp_result.get("status"))
        if isinstance(mcp_result, dict) and not mcp_is_stale
        else "UNKNOWN"
    )
    with st.container(border=True):
        st.subheader("Interactive 3D glasses demo")
        GLASSES_COMPONENT(
            pitch=pitch,
            roll=roll,
            yaw=yaw,
            severity=mcp_severity,
            key="glasses_orientation",
            default=None,
            on_change=_handle_glasses_orientation_change,
        )
        st.caption(
            "Drag to update pitch/yaw and the axis controls; each drag update is sent "
            "to MCP, with a final check when you release. Demo only."
        )
        pitch_metric, roll_metric, yaw_metric = st.columns(3)
        pitch_metric.metric("Request pitch", f"{pitch:.0f}°")
        roll_metric.metric("Request roll", f"{roll:.0f}°")
        yaw_metric.metric("Request yaw", f"{yaw:.0f}°")

    with st.container(border=True):
        st.subheader("Latest agent response")
        st.caption(
            "Unvalidated prototype output. Never use this response for health, safety, or care decisions."
        )
        if st.session_state.pop("play_demo_warning_cue", False):
            st.audio(_warning_tone_wav(), format="audio/wav", autoplay=True)
            st.caption(
                "A short demo tone was requested. Browser autoplay may be blocked; use the audio control if needed."
            )

        latest_error = st.session_state.get("last_api_error")
        if latest_error:
            st.error(latest_error)
        if isinstance(result, dict):
            result_data = result.get("data", {})
            if isinstance(result_data, dict):
                status = str(result_data.get("status", "UNKNOWN"))
                status_class = (
                    "warning" if status in WARNING_STATUSES else ""
                )
                st.markdown(
                    f'<div class="result-label {status_class}">'
                    f'{html.escape(status)}</div>',
                    unsafe_allow_html=True,
                )
                if last_api_mode in MODE_DETAILS:
                    response_agent = MODE_DETAILS[last_api_mode]
                    st.caption(
                        f"Last evaluated by: {response_agent['agent']} "
                        f"({last_api_mode})."
                    )
                if is_stale:
                    st.warning(
                        "Controls have changed since this response. Evaluate again to refresh it."
                    )
                st.markdown("**Agent output**")
                st.text(str(result_data.get("action_required", "No text output returned.")))
                transformations = result_data.get("ui_transformations")
                if isinstance(transformations, dict) and transformations:
                    with st.expander("Inspect experimental transform"):
                        st.json(transformations)
            else:
                st.error("The API result did not contain a data object.")
        elif not latest_error:
            st.info(
                "Choose a mode and submit a synthetic frame to see its API response."
            )

        st.divider()
        st.subheader("Live MCP response map")
        st.caption(
            "Color reflects the returned prototype status only; it is not a clinical "
            "risk assessment or patient alert."
        )
        mcp_error = st.session_state.get("mcp_error")
        if mcp_error:
            st.error(str(mcp_error))
        if isinstance(mcp_result, dict):
            severity_color = MCP_SEVERITY_COLORS[mcp_severity]
            st.markdown(
                f'<div class="result-label" style="color:{severity_color};'
                f'border-color:{severity_color};background:#10182a">'
                f'{html.escape(mcp_severity)} · {html.escape(str(mcp_result.get("status", "UNKNOWN")))}</div>',
                unsafe_allow_html=True,
            )
            st.caption("Response source: MCP `tools/call` over `/messages`.")
            if mcp_is_stale:
                st.warning(
                    "The MCP response is from earlier values. Send the synthetic frame again to refresh the map."
                )
            st.text(str(mcp_result.get("action_required", "No text output returned.")))
            if st.session_state.pop("play_mcp_demo_cue", False):
                st.audio(_warning_tone_wav(), format="audio/wav", autoplay=True)
                st.caption(
                    "Optional demo tone for a returned YELLOW/URGENT map. It is not a real-world alert."
                )
        else:
            st.info("Send synthetic OCR/text to the MCP endpoint to populate the response map.")

with insight_column:
    with st.container(border=True):
        selected_agent = MODE_DETAILS[selected_mode]
        st.subheader("Selected agent")
        st.markdown(f"**{selected_agent['agent']}**")
        st.caption(f"Mode: `{selected_mode}`")
        st.write(selected_agent["strength"])
        st.caption("This agent runs only after you submit a frame.")
        st.divider()
        st.subheader("Latest response")
        if (
            isinstance(result, dict)
            and isinstance(result.get("data"), dict)
            and last_api_mode in MODE_DETAILS
        ):
            result_data = result["data"]
            response_agent = MODE_DETAILS[last_api_mode]
            st.caption(f"Produced by {response_agent['agent']} (`{last_api_mode}`).")
            if is_stale:
                st.warning(
                    "This response is from the last submission, not the current selection or values."
                )
            reasoning = result_data.get("reasoning")
            if reasoning:
                st.text(str(reasoning))
            response_latency = st.session_state.get("last_response_latency_ms")
            if response_latency is not None:
                st.metric("API round-trip", f"{response_latency:.1f} ms")
        else:
            st.info(
                "No response yet. The selected agent is ready for a synthetic evaluation."
            )

    with st.container(border=True):
        with st.expander("Explore strengths of all 10 prototype agents"):
            for mode, details in MODE_DETAILS.items():
                st.markdown(f"**{details['agent']}**")
                st.caption(f"`{mode}` · {details['title']} - {details['strength']}")

    with st.container(border=True):
        st.subheader("Session activity")
        st.caption("Recent metadata only; the log omits input text and user IDs.")
        if st.button("Clear activity", use_container_width=True):
            st.session_state["activity_events"] = []
        events = st.session_state.get("activity_events", [])
        if events:
            for event in events[:6]:
                latency = event.get("latency_ms")
                suffix = f" · {latency:.1f} ms" if latency is not None else ""
                st.code(
                    f"{event['time']}  {event['mode']}  {event['status']}"
                    f"  P{event['pitch']:.0f} R{event['roll']:.0f} Y{event['yaw']:.0f}"
                    f"{suffix}",
                    language=None,
                )
        else:
            st.caption("No events yet.")

st.caption(
    "OcuGuard Studio is a local demo interface, not a wearable connection or a validated patient-facing product."
)
