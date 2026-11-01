# OcuGuard Studio

OcuGuard Studio is an optional Streamlit developer console for exercising the Flask REST API and MCP `/messages` endpoint with synthetic text and telemetry. It is separate from the static browser simulator in the repository root.

Use **FAQ / Capabilities** in the Studio or its Streamlit page navigation to browse an overview and one Markdown FAQ for each of the ten selectable modes, plus the Supervisor and Pre-Op Waitlist code modules. The guides describe current prototype behavior and explicitly call out integrations that are not implemented.

The UI reads `demo_values.json` from this folder at launch. It contains a default mode and one synthetic preset for each supported REST mode. Preset text and numbers populate the form and can be edited before submission. The UI validates the JSON structure at startup and reports missing, invalid, or unsupported values instead of silently substituting numbers.

The three-panel dashboard provides pitch, roll, and yaw controls, an interactive Three.js/WebGL glasses illustration, selected-agent details, and a session activity log. Pitch spans -90° to +90°; roll and yaw each span -180° to +180° (a full 360° range). Dragging the glasses updates pitch and yaw, their sliders and readouts, and submits the resulting orientation to the MCP endpoint. Requests are throttled to about one every 400 ms while dragging, with a final update on release; roll remains controlled by its slider. The model is generic—not a preview of a real wearable. Three.js is loaded from the pinned jsDelivr URL in the browser, so the browser needs network access to that CDN and WebGL support.

The "Synthetic OCR / text payload" field is user-entered demo text; it does not run OCR or connect to a camera. The `cataract_surgery` and `retinal_disease` toggles are synthetic profile flags. "Send synthetic OCR to MCP" submits a JSON-RPC `tools/call` request to the configured MCP `/messages` URL, defaulting to `http://127.0.0.1:3000/messages`. Dragging submits the same synthetic frame with its latest orientation, using a shorter 3-second timeout so a slow endpoint does not hold up the demo. Both paths send the selected mode, pitch/yaw/roll, text, and the two flags. Start the MCP endpoint as described below. The returned status is displayed as a GREEN, YELLOW, URGENT, or UNKNOWN response map; unrecognized or missing statuses stay UNKNOWN. These colors only summarize prototype output and are not clinical severity, patient risk, or safety guidance.

The demo sound toggle is on by default. When enabled, it plays a short nonverbal tone after a returned YELLOW or URGENT MCP map, including a warning received during a drag, or an applicable REST warning status. It is not a real-world alert; browser autoplay may be blocked. Dragging can submit multiple demo requests. Use the "Explore strengths of all 10 prototype agents" panel to compare current modes and their input-based strengths.

## Launch locally

From the repository root, create and activate a Python 3.10+ virtual environment, then install the UI dependencies:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-ui.txt
```

In one terminal, start the REST API:

```powershell
python app.py
```

In another terminal, start the MCP/SSE API:

```powershell
python mcp_sse_server.py
```

In a third terminal, start the UI:

```powershell
python -m streamlit run ui/streamlit_app.py
```

Open the local Streamlit URL printed in the terminal (normally `http://localhost:8501`). Set the REST API base URL or MCP `/messages` endpoint in the controls if either server is running at a different address.

The UI has no device integration or user authentication. Keep it and the APIs on a trusted development machine. Use synthetic data only; some configured backend modes may send text to an external model provider. The output is unvalidated and must not be used for health or care decisions. The WebGL library is fetched by the browser from a public CDN; the app does not send its synthetic text or profile flags to that CDN.
