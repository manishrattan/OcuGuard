# OcuGuard: Recovery-Support Exploration

OcuGuard is an open-source project exploring how accessible, user-controlled software might help people use recovery instructions already provided by their care team and access optional encouragement. The long-term idea may include approved wearable devices as an interface, but the current repository is a software prototype, not a recovery product.

**Status: prototype/demo only.** This repository does not currently integrate with Meta glasses or another manufacturer SDK, capture camera or microphone streams from a wearable, render output on eyewear, or establish a live human-helper connection. Inputs are supplied to its APIs or simulator; do not describe the project as an operational wearable product.

---

## Purpose and scope

### Why the project exists

The idea was motivated by a anonymous person's experience after retinal-detachment surgery: their doctor gave them a specific instruction about limiting head movement. That personal story points to a possible support problem - remembering and living with care-team instructions can be difficult - but it is not a universal recovery protocol. Instructions vary by procedure and person; only the treating care team can set or change them.

### Proposed long-term purpose

> **OcuGuard explores a patient-controlled recovery companion that makes care-team instructions easier to access and remember, while offering optional, non-clinical encouragement. It does not create, interpret, change, or replace medical instructions.**

The first research scope should be narrow: people who have received a specific recovery instruction from their own care team and want help accessing that instruction. Do not frame OcuGuard as an app for "anyone struggling" until separate user needs, risks, and intended uses have been studied.

The safest first product hypothesis is **non-sensing**: let a person view an instruction they already received, choose whether and when to receive a reminder, and optionally see a supportive message. A future OEM device could provide an approved display or input surface. Sensor-based posture monitoring or feedback is a later, separate research question; a device reading must never be treated as proof that a person is following instructions or is medically safe.

### What "agentic" should mean here

If agentic features are developed later, agents should coordinate a user-approved plan, not make care decisions:

| Future role concept | Appropriate boundary |
|---|---|
| Instruction presenter | Show clinician-authored content faithfully; never invent or revise a position or movement restriction. |
| Reminder coordinator | Let the user choose, pause, snooze, or stop reminders. A missed acknowledgment is not a clinical finding. |
| Encouragement companion | Offer optional, reviewed, non-clinical messages. Do not claim to provide therapy, assess emotions, or reassure someone that a symptom is safe. |
| Wearable adapter | Handle supported device connection, permissions, signal availability, and output capabilities; it is not a clinical authority. |
| Human-support option | Offer a user-selected contact path only with clear consent and confirmation; do not imply an automatic clinician or helper connection. |

The ten REST modes in this repository are experiments, not this recovery workflow. Their names and current behavior do not establish that these future roles exist or are safe.

### What the repository does today

The code currently provides a Flask REST API, a FastAPI MCP/SSE server, a browser/Streamlit simulator, prototype agent modes, and an experimental recovery-companion workflow. Users can save instruction cards with their exact supplied wording, schedule and pause reminders, and optionally read card text through their browser's speech engine. These features are not clinical care, and source labels are user-entered rather than verified. Recovery records are stored in a local, unencrypted SQLite database for development; use synthetic text only.

The device-session page exercises only a synthetic lifecycle contract. It does not discover, pair with, or connect to Meta glasses or other hardware. Do not use the software to decide post-operative positioning or provide care advice. Any use with real patient information, live sensors, or patient-facing care would require separate design, accessibility and safety testing, and qualified clinical, privacy, security, legal, and regulatory review. No wording or disclaimer can guarantee freedom from liability.

---

## Current Architecture and Data Flow

The system orchestrates stream data across an extensible, decoupled plugin architecture:

```mermaid
flowchart LR
    U["Developer, simulator, or API client<br/>supplies text and telemetry"]
    REST["Flask REST API<br/>app.py"]
    REC["Recovery API<br/>instruction cards and user schedules"]
    DB["Local SQLite prototype store<br/>unencrypted"]
    DEVICE["Synthetic device-session adapter<br/>no hardware"]
    SUP["SupervisorAgent<br/>limited token checks and regex redaction"]
    ROUTER{"agent_mode router"}
    AGENTS["Ten REST modes<br/>orientation, gaze, layout,<br/>environment, and transforms"]
    RESP["REST response<br/>status and data"]
    MCP["FastAPI MCP/SSE server<br/>mcp_sse_server.py"]
    FRAME["evaluate_wearable_stream<br/>calls the REST frame processor"]
    TOOLS["Direct MCP tools<br/>vision calibration and anxiety"]
    SIM["Static browser simulator<br/>serve.py"]
    LLM["External LLM path<br/>used by selected agents"]
    LOCAL["Local rule/math paths<br/>used by selected agents"]

    U --> REST --> SUP --> ROUTER --> AGENTS --> RESP
    REST --> REC --> DB
    REST --> DEVICE
    MCP --> FRAME --> SUP
    MCP --> TOOLS
    AGENTS --> LLM
    AGENTS --> LOCAL
    SIM -. "manual demo inputs" .-> U
```

The diagram describes code paths, not safety certification or real-time sensor integration. Some agents use external model calls; others use local rules or calculations. Do not assume every mode is offline or that all failures have a safe fallback.

## Sample screenshots

### Unsafe Head Movement detected
![alt text](img-unsafe-position.png)

### Safe Head Movement 
![alt text](img-safe-position.png)

### Be My Eyes escalation
![alt text](img-be-myeyes.png)

### Agent modules
1. Supervisor Agent (`SupervisorAgent`): Shared REST ingestion and routing code. It performs limited token checks and regex redaction; it is not comprehensive privacy protection or an authentication layer.

2. Eye Sentinel Agent (`EyeSentinelAgent`): Keyword-based symptom and positioning response path with local and cloud-backed branches; not clinically validated.

3. Gaze Compass Agent (`GazeCompassAgent`): Computes low-vision alignment cues from supplied target and blind-spot coordinates; it does not track objects from a glasses camera.

4. Tabular Layout Speech Agent (`TabularLayoutSpeechAgent`): Converts supplied text/layout content into an audio-oriented outline; it does not capture OCR from a wearable.

5. Ergonomic Schedule Agent (`ErgonomicScheduleAgent`): Evaluates supplied posture-hold telemetry and returns wellness-oriented prompts.

6. Ambient Luminance Agent (`AmbientLuminanceAgent`): Evaluates supplied ambient-light and contrast values and returns suggestions; no lens tint integration is present.

7. Be My Eyes Agent (`BeMyEyesAgent`): Evaluates input through a local/cloud agent path. A live Be My Eyes connection is not implemented here.

8. **Aniseikonia Scaling Agent**: Produces a text scale factor and transformation matrix from supplied size-difference metrics.

9. **Metamorphopsia Grid Remapper Agent**: Produces a simplified warp matrix from a supplied waviness index.

10. **Biofeedback Anxiety Sentinel Agent**: Matches transcript phrases and stress scores and returns reassurance text; it is not a clinical assessment.

The descriptions above summarize code modules, not connected hardware features. In particular, Gaze Compass works from coordinates supplied in telemetry; it does not continuously track objects from a glasses camera.

The REST router currently recognizes these ten `agent_mode` values: `EYE_SENTINEL`, `OCUGUARD_CORE`, `GAZE_COMPASS`, `TABULAR_LAYOUT_SPEECH`, `ERGONOMIC_SCHEDULE`, `AMBIENT_LUMINANCE`, `BE_MY_EYES`, `ANISEIKONIA_SCALING`, `METAMORPHOPSIA_GRID_REMAPPER`, and `BIOFEEDBACK_ANXIETY_SENTINEL`. `SupervisorAgent` is a shared routing component, not a mode. `PreOpWaitlistAgent` is present in source but is not routed; `PRE_OP_BRIDGE` is advertised by the MCP schema but is not implemented by the REST router. The MCP mode enum omits the three newer REST modes.

### Safety, Privacy, and Intended Use
This project is a software prototype. This README does not determine the product's regulatory classification.

Do not use the software for diagnosis, triage, treatment, emergency response, or post-operative positioning, or to make care decisions or delay contacting a qualified clinician or emergency service.

The API accepts health-related content. This repository does not establish production-grade consent, authentication, encryption, retention, or privacy controls. Do not send real patient data or identifiable transcripts to a demo deployment.

A disclaimer or open-source license does not determine regulatory status or eliminate legal obligations. Obtain jurisdiction-specific clinical, privacy, security, and regulatory review before any patient-facing use. No Meta, Apple, Google, or Be My Eyes partnership or endorsement is implied.

## Quick start

### Static simulator

The browser simulator serves local static files. It does not connect to smart glasses or capture camera/microphone streams.

1. Clone this repository and navigate to the project directory.

2. Spin up the localized application daemon:
```bash
python serve.py
```

3. Open [http://localhost:8000/index.html](http://localhost:8000/index.html) to try the simulated controls.

### Streamlit developer console

For an interactive, API-connected demo UI, install the optional dependencies:

```bash
python -m pip install -r requirements-ui.txt
```

Start the REST API in one terminal:

```bash
python app.py
```

Start OcuGuard Studio in a second terminal:

```bash
python -m streamlit run ui/streamlit_app.py
```

Open the local URL printed by Streamlit (normally [http://localhost:8501](http://localhost:8501)). The Studio page sends synthetic frames to the Flask API at `http://127.0.0.1:5000` by default; change the API URL in its controls if needed. The Recovery Companion page adds local prototype instruction cards, user-scheduled reminders, browser speech output, data deletion controls, and a synthetic device-session lifecycle demo. It does not connect to glasses or send audio to the API; browser/OS speech processing can vary, so use synthetic text only. See [application configuration](config/app.json) for UI defaults and configurable limits.

### Start the APIs

Use Python 3.10 or newer. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Optionally copy `.env.example` to `.env` and configure credentials for any external integrations. Never commit secrets. `API_KEY` protects the new recovery and device endpoints when configured; it is a shared service key, not per-user authentication or authorization. `OCUGUARD_ENVIRONMENT=production` intentionally fails startup until per-user authentication, encrypted persistent storage, transport security, and operational controls are implemented. The current local SQLite store is not suitable for real patient data or public deployment.

The application settings live in [config/app.json](config/app.json). Override the settings file with `OCUGUARD_CONFIG_FILE`, the SQLite path with `OCUGUARD_DATABASE_PATH`, and the UI's API base URL with `OCUGUARD_API_URL`. Keep feature flags, recurrence limits, field-size limits, timezones, and simulator capabilities in configuration rather than editing runtime code.

Start each server in a separate terminal:

```bash
# REST API at http://localhost:5000
python app.py
```

```bash
# MCP/SSE server at http://localhost:3000
python mcp_sse_server.py
```

Both servers bind to all interfaces by default. Keep them on a trusted development environment; do not expose them publicly as-is.

### Running Automated Test Suites
The existing test module is a starting point, not a verified release baseline. Some API tests reference older `/v1/triage*` routes, while the current Flask app exposes `/v1/stream/*`; reconcile those tests before relying on their results. Pytest is not currently declared in the project dependencies.

```bash
python -m pip install pytest
python -m pytest -q tests
```

See the [unit and integration test strategy](AGENTS.md#testing-strategy) for the planned coverage and known gaps.

## Repository layout

```text
config/                 JSON application settings
agents/                 Agent implementations
core/                   Shared schemas, configuration, and recovery persistence
docs/                   Specification, contributor guide, architecture
integrations/oem/        OEM contracts and synthetic device-session adapter only
tests/                  Unit and API tests
ui/                     Optional Streamlit developer console and recovery page
app.py                  Flask REST entry point
mcp_sse_server.py       MCP/SSE entry point
mcp_agent_server.py     MCP stdio entry point
serve.py                Static simulator
```

Future manufacturer-specific adapters belong under `integrations/oem/`. The current device-session contract is synthetic; it does not implement or imply a Meta or other OEM integration. A real SDK adapter still needs confirmed official SDK access, supported-device scope, consent, and privacy/security review. See the [OEM integration notes](integrations/oem/README.md), [architecture guide](docs/architecture.md), and [wearable integration action plan](docs/wearable-integration-action-plan.md).

Use the [store and developer-program readiness checklist](docs/store-readiness.md) for a draft listing and release gates. It is not an official Meta checklist or an assertion of eligibility.

## API overview

### Flask REST API

| Route | Purpose |
|---|---|
| `GET /health` | Basic process health response. |
| `GET /v1/stream/info` | Service metadata and a supported-agent list; the current list omits newer routed modes, so consult the mode list below. |
| `POST /v1/stream/evaluate` | Validates and routes a single telemetry frame. |
| `POST /v1/stream/evaluate/batch` | Evaluates up to 10 frames. |
| `GET /v1/system/config` | Configuration endpoint protected by `X-API-Key` when `API_KEY` is configured. |
| `GET /v1/system/stats` | Aggregate statistics endpoint protected by `X-API-Key` when `API_KEY` is configured. |
| `GET/POST /v1/recovery/instructions` | List or save user-entered instruction cards. `PUT` and `DELETE /v1/recovery/instructions/<id>` update or remove a card. |
| `GET/POST /v1/recovery/reminders` | List or schedule reminders. `PATCH /v1/recovery/reminders/<id>` pauses, resumes, snoozes, or acknowledges a reminder; `DELETE` removes it. |
| `DELETE /v1/recovery/data` | Deletes a user's prototype cards and reminders; request must include `"confirm": true`. |
| `GET /v1/device/capabilities` | Returns configured synthetic adapter capabilities; all physical hardware capabilities are false. |
| `POST /v1/device/sessions` | Starts a synthetic session only. `POST /v1/device/sessions/<id>/actions` pauses, resumes, or stops it. |

Recovery and device endpoints accept `X-API-Key` when `API_KEY` is set. In local development with no key configured, these routes are unauthenticated; do not expose them outside a trusted local environment. A shared key is not a substitute for end-user identity, consent management, or per-user authorization.

`POST /v1/stream/evaluate` requires `user_id` and `input_string`; `agent_mode` defaults to `EYE_SENTINEL`. The ten implemented modes are `EYE_SENTINEL`, `OCUGUARD_CORE`, `GAZE_COMPASS`, `TABULAR_LAYOUT_SPEECH`, `ERGONOMIC_SCHEDULE`, `AMBIENT_LUMINANCE`, `BE_MY_EYES`, `ANISEIKONIA_SCALING`, `METAMORPHOPSIA_GRID_REMAPPER`, and `BIOFEEDBACK_ANXIETY_SENTINEL`.

### MCP tools

| Tool | Inputs | Current limitation |
|---|---|---|
| `evaluate_wearable_stream` | Frame fields including `user_id`, `input_string`, `agent_mode`, `pitch`, and `yaw`. | MCP schema's mode enum is incomplete: it advertises `PRE_OP_BRIDGE` but omits three REST modes. |
| `ocuguard_calibrate_vision` | `visual_field_clearance`, `perceived_size_delta`, `text_wavy_index`. | The schema requires both calibration metrics, but the handler chooses one agent based on the presence of `perceived_size_delta`; the remapping branch is therefore not reachable with a schema-valid call. The handler currently returns text, not the documented structured transform payload. |
| `ocuguard_triage_anxiety` | `input_string`, `vocal_stress_score`. | Returns plain text status/reassurance; it is not medical triage or a clinical assessment. |

The MCP handlers currently format results as text rather than returning a typed structured payload. Validate the server's discovery and session behavior against the MCP clients you intend to support; the stateless compatibility routes do not implement every MCP method.

---

## Request paths and limitations

1. **Flask REST (`app.py`):** `/v1/stream/evaluate` validates the frame, passes it through `SupervisorAgent`, and selects a handler by `agent_mode`. Some modes use an external LLM path; behavior depends on the selected agent and fallback.
2. **MCP/SSE (`mcp_sse_server.py`):** `evaluate_wearable_stream` calls the REST frame processor. The two direct tools call their agent modules directly and bypass the REST supervisor path. The current implementation returns text content from tool calls, not the structured payload described by some older docs.
3. **MCP stdio (`mcp_agent_server.py`):** Provides a separate stdio transport for MCP clients.
4. **Static simulator (`serve.py`):** Serves the local browser files. It does not provide a glasses SDK or itself stream sensor data to either API.

These are separate processes. Do not assume network failures always fall back locally, that all calls are stateless, or that API/MCP results are suitable for patient care.

---

## Contributing
Contributions are welcome. Keep pull requests aligned with the prototype's documented scope, avoid implying clinical or hardware capabilities that are not implemented, and include tests for behavior changes.

### How to help
- Test coverage: Add deterministic unit tests and REST/MCP integration tests; see [AGENTS.md](AGENTS.md#testing-strategy).
- Simulator: Improve the browser demo and clearly label simulated data and limitations.
- Integrations: Propose device or audio integrations only against a documented, approved platform API, with user consent and a safe disable path.

Open an issue or discussion to propose a change.
