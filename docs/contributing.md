# Contributing to OcuGuard

Welcome! OcuGuard is an open-source prototype for exploring accessible ways to present user-supplied text and simulated telemetry. We especially welcome developers, designers, accessibility practitioners, researchers, and people with lived experience who want to make the project easier to use, test, and understand.

**New here?** Pick a small demo-sized problem, use synthetic data, and ask questions early. You do not need smart glasses, a cloud account, or an AI API key to contribute to the simulator, tests, schemas, or documentation.

[Project overview](../README.md) · [Product and engineering brief](./Spec.md) · [Architecture](./architecture.md)

## Good first contributions

| Track | Starter idea | Where to look |
|---|---|---|
| Accessible UI | Add keyboard navigation, visible focus, screen-reader labels, or a contrast control to the simulator. | `index.html` |
| Streamlit console | Improve API connection feedback, demo presets, or response presentation in OcuGuard Studio. | `ui/streamlit_app.py` |
| Demo experience | Add a synthetic demo scenario with clear labels, reset behavior, and no health data. | `index.html`, `serve.py` |
| API contracts | Test malformed frames, defaults, batch limits, and unsupported `agent_mode` values. | `app.py`, `core/schemas.py`, `tests/` |
| Agent reliability | Add deterministic boundary and error-path tests; mock external calls. | `agents/`, `tests/` |
| MCP interoperability | Make tool schemas and results consistent, then add client-independent contract tests. | `mcp_sse_server.py`, `mcp_agent_server.py` |
| OEM groundwork | Add fake-adapter contract tests without importing a manufacturer SDK. | `integrations/oem/`, `core/schemas.py` |
| Docs and privacy | Improve setup steps, map data flows, or make prototype limitations easier to see. | `README.md`, `docs/` |

For a hackathon, aim for a focused contribution that can be demonstrated with a short, synthetic scenario. Avoid implying a hardware, human-helper, or care capability that the code does not provide.

## Get set up

Requirements: Python 3.10 or newer and Git. From the repository root:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest
```

On macOS or Linux, create and activate the environment with:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest
```

The dependency list does not currently include pytest. Installing it into a virtual environment keeps the production/runtime dependency list unchanged.

### Run the project

To run the optional Streamlit console, install `requirements-ui.txt`, start `python app.py` in one terminal, and run `python -m streamlit run ui/streamlit_app.py` in another. See the [UI guide](../ui/README.md).

Start the browser simulator:

```bash
python serve.py
```

Open `http://localhost:8000/index.html`.

To try the APIs, start each server in its own terminal:

```bash
python app.py
```

The Flask API listens on port `5000`. The MCP/SSE server listens on port `3000`:

```bash
python mcp_sse_server.py
```

Both servers bind to all interfaces by default. Keep them on a trusted development machine; do not expose them publicly. External model credentials are optional for local and test work. If you choose to configure one, keep it in an untracked local `.env`, never in a fixture, screenshot, issue, or pull request. Never send real patient data.

### Run tests

```bash
python -m pytest -q tests
```

The existing suite is not yet a clean release baseline: parts of `tests/test_triage_agent.py` expect legacy `/v1/triage*` routes, while the current Flask API exposes `/v1/stream/*`. Pytest is not installed by `requirements.txt`. If the full suite fails, include the failing test names and distinguish pre-existing route-contract drift from failures introduced by your change. For new work, prefer focused tests that demonstrate the intended current contract.

## How to contribute

1. **Find or open an issue.** Describe the user-facing problem, the smallest useful outcome, and how you will demo it. For larger ideas, get feedback before building.
2. **Create a focused branch.** Keep one change per pull request where possible.
3. **Build within the repository boundaries.**
   - Agent and routing behavior belongs under `agents/` and `app.py`.
   - Shared request/response contracts belong under `core/`.
   - Manufacturer-specific code belongs under `integrations/oem/`; agent modules must not import an OEM SDK directly.
   - Keep demos usable without physical hardware or cloud credentials.
4. **Test the behavior.** Use synthetic inputs and mock network, model, and device dependencies. Include expected behavior for invalid input and unavailable services.
5. **Update the docs.** Mark behavior as implemented, experimental, or proposed. Keep product claims in sync with what can actually be run.
6. **Open a pull request.** Explain why the change matters, what changed, how to test it, and any known limitations. Include screenshots or a short demo clip for visual changes, with synthetic content only.

## Safety, privacy, and scope

- This repository is a software prototype, not a validated healthcare product. Do not add diagnosis, treatment, emergency triage, medication decisions, or post-operative instructions.
- Do not make claims that an agent is clinically accurate, legally cleared, privacy-compliant, or safe for patient use.
- Use synthetic or public-domain test data. Never commit personal, health, biometric, or otherwise identifying data.
- Some optional agent paths use an external model provider. Make outbound data flows explicit, mock those calls in tests, and do not assume every mode has an offline fallback.
- Do not claim that `BE_MY_EYES` opens a live human connection or that any mode reads a glasses camera/microphone.
- A disclaimer, renamed feature, or open-source license does not remove legal or regulatory obligations. Requests that cross into care decisions or patient-facing use need appropriate expert review.
- For a proposed OEM integration, follow the [wearable integration action plan](./wearable-integration-action-plan.md): identify the approved SDK and device scope, permissions/consent model, local processing options, disable path, and test strategy before adding dependencies.

These are scope and product-quality boundaries, not legal advice. See the [product and engineering brief](./Spec.md) for the longer context.

## Pull request checklist

- [ ] The change addresses a specific issue or documented use case.
- [ ] New behavior has focused tests; network/model/device calls are mocked.
- [ ] The demo uses synthetic data and can be reset or disabled.
- [ ] No secrets or personal/health data are included.
- [ ] Documentation accurately labels current behavior and limitations.
- [ ] Accessibility, error handling, and privacy implications were considered.
- [ ] The pull request description includes test commands/results and known gaps.

Thanks for helping make the prototype more useful, accessible, and trustworthy.
