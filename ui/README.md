# OcuGuard Studio

OcuGuard Studio is an optional Streamlit developer console for exercising the Flask REST API with synthetic text and telemetry. It is separate from the static browser simulator in the repository root.

The UI reads `demo_values.json` from this folder at launch. It contains a default mode and one synthetic preset for each supported REST mode. Preset text and numbers populate the form and can be edited before submission. The UI validates the JSON structure at startup and reports missing, invalid, or unsupported values instead of silently substituting numbers.

The three-panel dashboard provides pitch, roll, and yaw controls, an interactive 3D glasses illustration, selected-agent details, and a session activity log. Drag the glasses with a mouse, touch, or stylus to adjust the simulated pitch and yaw; keyboard users can focus the model and use the arrow keys. Perspective, frame depth, and temples provide a 3D-style view, but this is a generic illustration—not a preview of a real wearable. The local green/red indicator reflects only the OcuGuard Core demo threshold (red below -30 degrees). Dragging changes only the illustration; the sliders provide the values sent to the API. The selected agent runs only after you submit a synthetic frame. Use the "Explore strengths of all 10 prototype agents" panel to compare the current modes and their input-based strengths.

The threshold demo preset sets a sample pitch that exercises the orientation rule. The optional sound toggle is off by default; when enabled, it plays one short, nonverbal demo tone after the API returns one of the configured warning-like status labels. Dragging or moving sliders alone never triggers an agent or sound. The green/red indicator is a prototype threshold visualization, not an assessment of danger or patient safety. Browser autoplay may be blocked, in which case the audio control can be used manually. The tone is not a real-world alert.

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

In a second terminal, start the UI:

```powershell
python -m streamlit run ui/streamlit_app.py
```

Open the local Streamlit URL printed in the terminal (normally `http://localhost:8501`). Set the API base URL in the sidebar if Flask is running somewhere other than `http://127.0.0.1:5000`.

The UI has no device integration or user authentication. Keep it and the API on a trusted development machine. Use synthetic data only; some configured backend modes may send text to an external model provider. The output is unvalidated and must not be used for health or care decisions.
