# Repository structure

```text
agents/                 Agent implementations, including experimental agents
core/                   Shared schemas and plugin abstractions
docs/                   Product and contributor documentation
integrations/
  oem/                  Vendor-neutral OEM adapter contract and future adapters
tests/                  Automated tests
app.py                  Flask REST entry point
mcp_sse_server.py       FastAPI MCP/SSE entry point
mcp_agent_server.py     MCP stdio entry point
serve.py                Static browser simulator
```

## Boundaries

- Agent modules consume shared contracts from `core/`; they should not import OEM SDKs.
- OEM adapters normalize manufacturer-specific data into `core.schemas.TelemetryFrame`.
- The REST and MCP entry points remain at the repository root for compatibility with existing launch configurations and containers.
- [Spec.md](Spec.md) and [contributing.md](contributing.md) contain the longer-form specification and contribution guidance. The root `README.md` is the user-facing project overview.

There are no manufacturer-specific integrations in this repository yet. Add one only when an approved SDK, supported-device scope, consent flow, and privacy/security review are available.
