from __future__ import annotations

import base64
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


API_TIMEOUT_SECONDS = 15
DEFAULT_API_URL = "http://127.0.0.1:5000"
DEMO_VALUES_PATH = Path(__file__).with_name("demo_values.json")
ORIENTATION_DEMO_THRESHOLD = -30.0
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


def _glasses_simulation_html(pitch: float, roll: float, yaw: float) -> str:
    grid_rays = "\n".join(
        f'<line x1="400" y1="326" x2="{x}" y2="497"/>'
        for x in range(0, 801, 80)
    )
    grid_rows = []
    for y in (343, 363, 389, 424, 469):
        ratio = (y - 326) / (497 - 326)
        edge = 400 * ratio
        grid_rows.append(
            f'<line x1="{400 - edge:.1f}" y1="{y}" '
            f'x2="{400 + edge:.1f}" y2="{y}"/>'
        )
    grid = "\n".join((*grid_rays, *grid_rows))
    dangerous = _orientation_demo_is_dangerous(pitch)
    accent = "#ff6670" if dangerous else "#61d69a"
    status_background = "#3b1d25" if dangerous else "#15372b"
    initial_zone = "danger" if dangerous else "green"
    styles = """
    <style>
      * { box-sizing: border-box; }
      html, body { margin: 0; width: 100%; background: #080d18; }
      body { overflow: hidden; font-family: system-ui, sans-serif; }
      #wearable-stage {
        position: relative; width: 100%; aspect-ratio: 8 / 5;
        overflow: hidden; border: 1px solid #26334a; border-radius: 14px;
        background: #080d18;
      }
      #wearable-scene {
        position: absolute; inset: 0; display: block; width: 100%; height: 100%;
      }
      #interaction-surface {
        position: absolute; inset: 0; perspective: 1050px;
        perspective-origin: 50% 48%; transform-style: preserve-3d;
        pointer-events: none;
      }
      #draggable-glasses {
        --frame-accent: #61d69a;
        position: absolute; z-index: 2; left: 50%; top: 49.5%;
        width: 64%; aspect-ratio: 4 / 1;
        transform-style: preserve-3d; transform-origin: center;
        pointer-events: auto; touch-action: none; user-select: none;
        cursor: grab; outline: none;
        filter: drop-shadow(0 0 14px var(--frame-accent));
      }
      #draggable-glasses:focus-visible {
        outline: 2px solid #dce8f3; outline-offset: 8px; border-radius: 18px;
      }
      .glasses-temple {
        position: absolute; top: 47%; width: 20%; height: 8px;
        border-radius: 8px;
        background: linear-gradient(90deg, #10243a, var(--frame-accent));
        box-shadow: 0 0 8px rgba(97, 214, 154, .22);
      }
      .glasses-temple.left {
        left: -15%; transform-origin: right center;
        transform: rotateY(-42deg) translateZ(-18px);
      }
      .glasses-temple.right {
        right: -15%; transform-origin: left center;
        transform: rotateY(42deg) translateZ(-18px);
      }
      .glasses-lens {
        position: absolute; top: 10%; width: 43%; height: 80%;
        border: 8px solid var(--frame-accent); border-radius: 25% / 30%;
        background: linear-gradient(145deg, rgba(28, 63, 91, .94), rgba(8, 20, 36, .96));
        box-shadow: inset 0 0 25px rgba(116, 199, 222, .12),
                    0 0 14px rgba(80, 207, 177, .18);
        transform: translateZ(18px); backface-visibility: hidden;
      }
      .glasses-lens::after {
        content: ""; position: absolute; left: 13%; right: 13%; top: 16%;
        height: 2px; border-radius: 2px; background: rgba(232, 249, 255, .36);
      }
      .glasses-lens.left { left: 4%; }
      .glasses-lens.right { right: 4%; }
      .glasses-bridge {
        position: absolute; left: 42%; top: 41%; width: 16%; height: 12px;
        border: 5px solid var(--frame-accent); border-bottom: 0;
        border-radius: 50% 50% 0 0; transform: translateZ(21px);
      }
    </style>
    """
    stage = f"""
    <div id="wearable-stage">
      <svg id="wearable-scene" viewBox="0 0 800 500" role="img"
           aria-label="Synthetic demo scene with a simulated orientation threshold"
           preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id="scene" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stop-color="#070b14"/>
            <stop offset="1" stop-color="#0b1425"/>
          </linearGradient>
        </defs>
        <rect width="800" height="500" fill="url(#scene)"/>
        <rect x="0" y="0" width="800" height="285" fill="#35b778" opacity=".025"/>
        <rect id="danger-zone" x="0" y="285" width="800" height="215"
              fill="#ef4444" opacity=".055"/>
        <text x="30" y="38" fill="#70d7cf" font-size="13" font-weight="700"
              letter-spacing="2">SYNTHETIC WEARABLE VIEW</text>
        <text x="770" y="38" fill="#8796ad" font-size="12" text-anchor="end">
          DRAG TO ROTATE · DEMO ONLY
        </text>
        <rect id="zone-status" data-initial-zone="{initial_zone}"
              x="254" y="53" width="292" height="34" rx="17"
              fill="{status_background}" stroke="{accent}" stroke-width="1.5"/>
        <text id="zone-status-label" x="400" y="75" fill="{accent}" font-size="12"
              font-weight="700" text-anchor="middle">DRAG INTERACTION LOADING</text>
        <path d="M0 285 H800" stroke="#ff6670" stroke-width="1.5"
              stroke-dasharray="7 7" opacity=".75"/>
        <text x="778" y="303" fill="#ff9da3" font-size="10" text-anchor="end">
          CORE DEMO THRESHOLD: -30°
        </text>
        <path d="M0 326 H800" stroke="#30405a" stroke-width="2"/>
        <g stroke="#26364f" stroke-width="1" opacity=".78">{grid}</g>
        <path d="M400 326 V500" stroke="#42536c" stroke-width="1.5" opacity=".8"/>
        <ellipse cx="400" cy="248" rx="190" ry="94" fill="#10182a"
                 fill-opacity=".12" stroke="#42516b" stroke-width="2"
                 stroke-dasharray="6 9"/>
        <text id="orientation-readout" x="400" y="483" fill="#dce8f3" font-size="15"
              text-anchor="middle">
          Demo pitch {pitch:.0f}° · roll {roll:.0f}° · yaw {yaw:.0f}°
        </text>
      </svg>
      <div id="interaction-surface">
        <div id="draggable-glasses" role="group" tabindex="0"
             aria-label="3D glasses model. Drag to adjust simulated pitch and yaw; use arrow keys to adjust them with a keyboard."
             aria-describedby="zone-status-label orientation-readout"
             style="--frame-accent:{accent}">
          <div class="glasses-temple left"></div>
          <div class="glasses-temple right"></div>
          <div class="glasses-lens left"></div>
          <div class="glasses-lens right"></div>
          <div class="glasses-bridge"></div>
        </div>
      </div>
    </div>
    """
    script = """
    <script>
      (() => {
        const glasses = document.getElementById("draggable-glasses");
        const scene = document.getElementById("wearable-scene");
        const statusBox = document.getElementById("zone-status");
        const statusLabel = document.getElementById("zone-status-label");
        const readout = document.getElementById("orientation-readout");
        const threshold = Number("__THRESHOLD__");
        const roll = Number("__ROLL__");
        let pitch = Number("__PITCH__");
        let yaw = Number("__YAW__");
        let dragOrigin = null;

        const clamp = (value, minimum, maximum) =>
          Math.max(minimum, Math.min(maximum, value));

        const render = () => {
          const danger = pitch < threshold;
          const accent = danger ? "#ff6670" : "#61d69a";
          const background = danger ? "#3b1d25" : "#15372b";
          const downward = clamp(-pitch, 0, 60);
          const xOffset = clamp(yaw, -45, 45) * 0.32;
          const yOffset = downward * 0.42;
          const pitchRotation = downward * 0.32;
          const yawRotation = clamp(yaw, -45, 45) * 0.55;
          const rollRotation = clamp(roll, -30, 30) * 0.7;
          glasses.style.setProperty("--frame-accent", accent);
          glasses.style.transform =
            `translate(-50%, -50%) translate3d(${xOffset.toFixed(1)}px, ` +
            `${yOffset.toFixed(1)}px, 0) rotateX(${pitchRotation.toFixed(1)}deg) ` +
            `rotateY(${yawRotation.toFixed(1)}deg) rotateZ(${rollRotation.toFixed(1)}deg)`;
          statusBox.setAttribute("fill", background);
          statusBox.setAttribute("stroke", accent);
          statusLabel.setAttribute("fill", accent);
          statusLabel.textContent = danger
            ? "RED - DEMO THRESHOLD CROSSED"
            : "GREEN - WITHIN DEMO ZONE";
          readout.textContent =
            `Demo pitch ${pitch.toFixed(0)}° · roll ${roll.toFixed(0)}° · ` +
            `yaw ${yaw.toFixed(0)}°`;
          scene.setAttribute(
            "aria-label",
            `Synthetic glasses demo, pitch ${pitch.toFixed(0)} degrees, ` +
              (danger ? "red demo threshold crossed" : "green demo zone")
          );
        };

        glasses.addEventListener("pointerdown", (event) => {
          if (event.button !== 0) return;
          dragOrigin = { x: event.clientX, y: event.clientY, pitch, yaw };
          glasses.setPointerCapture(event.pointerId);
          glasses.style.cursor = "grabbing";
          event.preventDefault();
        });

        glasses.addEventListener("pointermove", (event) => {
          if (!dragOrigin) return;
          pitch = clamp(dragOrigin.pitch - (event.clientY - dragOrigin.y) * 0.65, -60, 0);
          yaw = clamp(dragOrigin.yaw + (event.clientX - dragOrigin.x) * 0.5, -45, 45);
          render();
        });

        const finishDrag = () => {
          dragOrigin = null;
          glasses.style.cursor = "grab";
        };
        glasses.addEventListener("pointerup", finishDrag);
        glasses.addEventListener("pointercancel", finishDrag);
        glasses.addEventListener("keydown", (event) => {
          if (event.key === "ArrowDown") pitch = clamp(pitch - 2, -60, 0);
          else if (event.key === "ArrowUp") pitch = clamp(pitch + 2, -60, 0);
          else if (event.key === "ArrowLeft") yaw = clamp(yaw - 2, -45, 45);
          else if (event.key === "ArrowRight") yaw = clamp(yaw + 2, -45, 45);
          else return;
          event.preventDefault();
          render();
        });
        render();
      })();
    </script>
    """
    script = (
        script.replace("__THRESHOLD__", f"{ORIENTATION_DEMO_THRESHOLD:.1f}")
        .replace("__PITCH__", f"{pitch:.1f}")
        .replace("__ROLL__", f"{roll:.1f}")
        .replace("__YAW__", f"{yaw:.1f}")
    )
    document = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>3D synthetic glasses visualization</title>"
        f"{styles}</head><body>{stage}{script}</body></html>"
    )
    encoded_document = base64.b64encode(document.encode("utf-8")).decode("ascii")
    return f"data:text/html;base64,{encoded_document}"


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
if not -60.0 <= default_pitch <= 0.0:
    raise ValueError("OCUGUARD_CORE pitch preset must be between -60 and 0 degrees.")
if not -30.0 <= default_roll <= 30.0 or not -45.0 <= default_yaw <= 45.0:
    raise ValueError("OCUGUARD_CORE roll/yaw presets exceed simulator limits.")

for key, value in (
    ("demo_pitch_down", int(abs(default_pitch))),
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
                -float(st.session_state["demo_pitch_down"]),
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
            "Synthetic input text",
            value=_preset_text(selected_mode),
            height=82,
            key=f"sample-text-{selected_mode}",
            help="Synthetic content only. Some configured backend modes may call an external model.",
        )

        preset_columns = st.columns(2)
        if preset_columns[0].button("Neutral demo", use_container_width=True):
            st.session_state["demo_pitch_down"] = 0
        if preset_columns[1].button("Threshold demo", use_container_width=True):
            st.session_state["demo_pitch_down"] = 35

        head_pitch_down = st.slider(
            "Downward pitch",
            min_value=0,
            max_value=60,
            step=1,
            key="demo_pitch_down",
            help="Maps to a negative pitch value. The illustration updates immediately.",
        )
        pitch = -float(head_pitch_down)
        roll = float(
            st.slider(
                "Roll",
                min_value=-30,
                max_value=30,
                step=1,
                key="demo_roll",
            )
        )
        yaw = float(
            st.slider(
                "Yaw",
                min_value=-45,
                max_value=45,
                step=1,
                key="demo_yaw",
            )
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
            value=False,
            help="After submission only: one short tone for selected API status labels. It is not a real-world alert.",
        )
        evaluate_clicked = st.button(
            "Evaluate synthetic frame",
            type="primary",
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

with scene_column:
    result = st.session_state.get("last_api_result")
    last_api_mode = st.session_state.get("last_api_mode")
    last_signature = st.session_state.get("last_evaluation_signature")
    is_stale = result is not None and last_signature != frame_signature
    with st.container(border=True):
        st.subheader("Interactive 3D glasses demo")
        st.iframe(
            _glasses_simulation_html(pitch, roll, yaw),
            height=505,
        )
        st.caption(
            "Drag the 3D glasses to adjust the simulated pitch and yaw, or focus them "
            "and use the arrow keys. The red/green OcuGuard Core threshold is a demo "
            "only (red below -30°). Dragging changes only this illustration; sliders "
            "set API values, and the selected agent runs only when you evaluate."
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
