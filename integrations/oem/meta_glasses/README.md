# Meta glasses-shaped adapter example

**Placeholder only:** this is a small example of the `OEMTelemetryAdapter` boundary using synthetic input. It does not import, wrap, or implement a Meta SDK; the payload below is an OcuGuard-defined demo shape, not a Meta API contract. No glasses, camera, microphone, or live sensor data is accessed.

The adapter maps only an application-supplied `user_id`, `input_string`, and explicit orientation angles into `core.schemas.TelemetryFrame`. All values must be provided; the example does not invent a neutral orientation when sensor data is missing.

```python
from integrations.oem.meta_glasses import MetaGlassesExampleAdapter

frame = MetaGlassesExampleAdapter().to_telemetry_frame({
    "user_id": "synthetic-demo-user",
    "input_string": "",
    "orientation": {
        "pitch_degrees": -4.5,
        "yaw_degrees": 3.2,
        "roll_degrees": 0.0,
    },
})
```

Before replacing this placeholder with a real integration:

1. Select and verify an officially supported SDK and device scope; do not infer APIs from this example.
2. Document platform permissions and obtain informed user permission before sensor access.
3. Keep SDK-specific code inside this subpackage and map only the minimum approved data.
4. Define behavior for missing, stale, or invalid sensor values; never silently substitute measurements.
5. Add synthetic contract tests and device tests where authorized. Do not commit credentials, raw media, or personal data.
6. Complete privacy, security, accessibility, and applicable clinical/regulatory/legal review before any patient-facing use.

No Meta partnership, endorsement, compatibility, or product integration is implied.
