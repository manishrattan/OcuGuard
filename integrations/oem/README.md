# OEM integration boundary

This package is an adapter boundary for future wearable integrations. It contains no Meta or other manufacturer SDK implementation. The `meta_glasses/` subpackage is a synthetic contract example only; it does not connect to Meta glasses or describe an official SDK payload.

An OEM-specific adapter should:

1. Keep vendor SDK imports and permission handling inside its own subpackage.
2. Obtain explicit user permission before accessing sensors, camera, or microphone data.
3. Convert only the minimum required vendor data into the vendor-neutral `TelemetryFrame` using `OEMTelemetryAdapter`.
4. Avoid placing vendor SDK objects, credentials, or raw media into agent code or persistent logs.
5. Provide tests using synthetic SDK-shaped frames; do not require hardware for unit tests.
6. Document supported hardware, SDK versions, permissions, data flows, and known limitations without implying manufacturer partnership or endorsement.

No adapter should send sensor data to a service or invoke patient-facing guidance until privacy, security, accessibility, and regulatory reviews are complete.
