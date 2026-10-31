# Repository structure

```text
agents/                 Agent implementations, including experimental agents
core/                   Shared schemas and plugin abstractions
docs/                   Product and contributor documentation
integrations/
  oem/                  Vendor-neutral OEM adapter contract and future adapters
tests/                  Automated tests
ui/                     Optional Streamlit developer console; calls the REST API
app.py                  Flask REST entry point
mcp_sse_server.py       FastAPI MCP/SSE entry point
mcp_agent_server.py     MCP stdio entry point
serve.py                Static browser simulator
```

## Boundaries

- Agent modules consume shared contracts from `core/`; they should not import OEM SDKs.
- OEM adapters normalize manufacturer-specific data into `core.schemas.TelemetryFrame`.
- The REST and MCP entry points remain at the repository root for compatibility with existing launch configurations and containers.
- The Streamlit UI is a separate optional process that calls the Flask REST API; it does not import agents or connect to wearable hardware directly.
- [Spec.md](Spec.md) and [contributing.md](contributing.md) contain the longer-form specification and contribution guidance. The [wearable integration action plan](wearable-integration-action-plan.md) describes a gated path for future device work. The root `README.md` is the user-facing project overview.

There is no live manufacturer SDK integration in this repository. `integrations/oem/meta_glasses/` is a synthetic mapping example only. Add a real adapter only after an approved SDK, supported-device scope, consent flow, and privacy/security review are available.
