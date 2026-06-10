# OcuGuard AI Enterprise — Adaptive Spatial Computing Middleware

OcuGuard AI is an open-source, stateless spatial computing and ergonomic telemetry pipeline engineered for consumer smart eyewear (such as Meta Orion, Apple Vision, and Google Ambient systems). The system acts as a high-frequency orientation translator, transforming raw inertial sensor matrices (IMU data) and OCR transcripts into localized audio-haptic cues to maximize user workplace productivity and spatial navigation adherence.

---

## 💡 Project Genesis & Hackathon Focus

OcuGuard AI was inspired by a technical contributor’s personal journey navigating visual adaptation challenges following a complex ophthalmic recovery process. During high-stakes situational intervals (such as strict posture constraints or lengthy community waitlists), mass-market consumer wearables remain entirely passive—requiring explicit user triggers to react. 

OcuGuard AI closes this structural gap. It acts as an autonomous background framework that maps live orientation streams against user-calibrated baseline goals, ensuring consumer wearables can actively assist individuals during critical physical adaptation windows.

---

## 🛠️ Network Architecture & Multi-Agent Mesh

The system orchestrates stream data across an extensible, decoupled plugin architecture:

```mermaid
flowchart LR
    U[User Wearable Stream<br/>Orientation / Audio Data]
    API[REST Evaluation Gateway<br/>/v1/stream/evaluate]
    SUP[Supervisor Agent<br/>Stateless PII Redaction]
    ES[Eye Sentinel Agent]
    GC[Gaze Compass Agent]
    TL[Tabular Layout Agent]
    ER[Ergonomic Schedule Agent]
    AL[Ambient Luminance Agent]
    BME[Be My Eyes Proxy Node]
    
    LLM[OpenAI GPT Cloud Path]
    LOCAL[Deterministic Math Engine]

    U --> API
    API --> SUP
    SUP --> |"EYE_SENTINEL"| ES
    SUP --> |"GAZE_COMPASS"| GC
    SUP --> |"TABULAR_LAYOUT_SPEECH"| TL
    SUP --> |"ERGONOMIC_SCHEDULE"| ER
    SUP --> |"AMBIENT_LUMINANCE"| AL
    SUP --> |"BE_MY_EYES"| BME

    ES & GC & TL & BME --> LLM
    ER & AL --> LOCAL

### Active Core Plugins
1. Supervisor Agent (SupervisorAgent): The operational firewall. Enforces stateless edge boundaries, scrubs PII via high-speed regex tracking, and triggers immediate fallback mechanics during network drops.

2. Eye Sentinel Agent (EyeSentinelAgent): Tracks strict, high-frequency orientation boundaries. If a user's head pitch drifts from a configured threshold, it dispatches rapid structural remediation guidelines.

3. Gaze Compass Agent (GazeCompassAgent): Visual workspace layout tool. Continuously tracks coordinate matrices, mapping central scotomas relative to target vectors to yield real-time 3D stereo-panning cues to shift items into the Preferred Retinal Locus (PRL).

4. Tabular Layout Speech Agent (TabularLayoutSpeechAgent): Productivity enhancer. Translates messy OCR text or document tables into structured, hands-free verbal layouts for users dealing with blurry visual profiles.

5. Ergonomic Schedule Agent (ErgonomicScheduleAgent): Passive tracking engine that uses time-series telemetry to detect sustained, frozen postural shapes, prompting movement cues.

6. Ambient Luminance Agent (AmbientLuminanceAgent): Contrast assessment tool evaluating ambient lux environments to prompt electronic glass tint adaptations or high-contrast screen profiles.

7. Be My Eyes Escalation Agent (BeMyEyesAgent): High-reliability proxy that bridges to a live human helper if AI frame processing confidence slips below 82%.

### ⚖️ Strict Product Boundaries & Liability Notice
OcuGuard AI is classified strictly as an abstract cognitive assistive framework and non-diagnostic orientation aid.

NOT A MEDICAL DEVICE: This software does NOT provide medical triage, diagnostic evaluations, or medical treatment plans. It has NOT been reviewed, cleared, or approved by the FDA or any global regulatory body.

USER-CONFIGURED PARAMETERS: All orientation limits, sensor guidelines, and alert baselines are configured manually by the operator to align with personal ergonomic preferences.

NO WARRANTY: Provided under the open-source MIT License "AS IS". Users deploy this stream processing framework completely at their own risk.

### 🚀 Getting Started
Quick Start (Local Demo Dashboard)
You don't need smart glasses to test or present this project. OcuGuard includes a high-fidelity web-based hardware simulator.

1. Clone this repository and navigate to the project directory.

2. Spin up the localized application daemon:
python serve.py

3. Open http://localhost:8000/index.html in your browser to interactively manipulate the 3D head-pitch metrics and gaze scotoma matrix vectors.

### Running the Production REST API Backend
Ensure Python 3.10+ is installed. Clone the workspace, copy environment parameters, and install dependencies:

copy .env.example .env
# Set your OPENAI_API_KEY and API_KEY in .env

python -m pip install -r requirements.txt
python app_2.py

The endpoint will actively stream, validate, and serialize payload data at: POST /v1/stream/evaluate.

### Running Automated Test Suites
Verify all 36 local mathematical evaluation routines completely offline using mocked responses:

pytest test_triage_agent.py -q




### How it works

- Clients send telemetry and agent mode selection to `POST /v1/triage`.
- `app.py` validates requests, enforces rate limiting, and delegates to `SupervisorAgent`.
- The supervisor redacts sensitive data and routes each request to the selected sub-agent.
- Most agents use an LLM analysis path with secure OpenAI integration and a local fallback for safety.
- `OCUGUARD_CORE` uses deterministic local rules and posture checks.
- Results are returned as a structured `TriageResponse`, including confidence, action guidance, and escalation triggers.

---

## 2. API Schema Specification

### 2.1 Single Telemetry Analysis
* **Endpoint:** `POST /v1/triage`
* **Request Body:**
  ```json
  {
    "user_id": "patient_uuid",
    "input_string": "I see a black curtain in my left eye",
    "agent_mode": "EYE_SENTINEL",
    "client_id": "OCUGUARD_CLIENT",
    "user_token": "OCUGUARD_TOKEN",
    "history": {
      "cataract_surgery": true,
      "age_over_50": true
    }
  }
  ```
* **Supported `agent_mode` Values:** `EYE_SENTINEL`, `OCUGUARD_CORE`, `GAZE_COMPASS`, `PRE_OP_BRIDGE`, `BE_MY_EYES`

### 2.2 Batch Telemetry Analysis
* **Endpoint:** `POST /v1/triage/batch`
* **Request Body:** Contains an array of requests under `{"requests": [...]}`. Max batch size is 10.

### 2.3 Service Info & Health Checks
* **Endpoint:** `GET /v1/triage/info` - Service details and supported keywords.
* **Endpoint:** `GET /health` - Returns `{"status": "healthy"}` for load balancers.
* **Protected Endpoints:** `/v1/system/config` and `/v1/system/stats` require the `X-API-Key` header matching the `API_KEY` environment variable.

---

## 3. Getting Started

### 3.1 Installation & Dependencies
Ensure Python 3.10+ is installed. Clone the workspace, copy environment parameters, and install dependencies:
```bash
copy .env.example .env
# Set your OPENAI_API_KEY and API_KEY in .env

python -m pip install -r requirements.txt
```

### 3.2 Running the REST Daemon
Start the Flask application:
```bash
python app.py
```
By default, the server runs on `http://localhost:5000`.

### 3.3 Running Automated Tests
Run the comprehensive test suite with 36 unit tests:
```bash
pytest test_triage_agent.py -q
```
All tests are configured to run completely offline using mocked LLM responses.

### 🤝 Contributing & Hackathons
This repository is optimized for open-source presentation at Accessibility Hackathons, Ophthalmic Innovation Summits, and Assistive Tech Forums. We welcome community contributions to build out this non-diagnostic framework!

# How to Help:
- Plugin Expansion: Build custom agents inheriting from OcuGuardSubAgentPlugin to map new wearable sensor profiles.
- Telemetry Simulation: Enhance our WebGL/Canvas spatial visualizers to simulate diverse environmental conditions.
- Audio Engineering: Implement Web Audio API extensions to refine real-time stereo pan-localization velocity.

Feel free to open an issue or discussion thread to get involved. Let's make smart eyewear actively helpful together!
