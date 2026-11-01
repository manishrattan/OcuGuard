# OcuGuard Core

**Studio mode:** `OCUGUARD_CORE`  
**Code:** Built-in branch in `app.py`  
**Collection:** Studio agents

## What it does

OcuGuard Core is the Studio's small built-in pitch-threshold example. It returns `VIOLATION` when supplied pitch is below -30° and `SAFE` otherwise. The current code has an additional `< -45°` branch, but it produces the same result; effectively the decision boundary is -30°.

## Inputs and outputs

- Pitch, roll, and yaw are included in the submitted frame.
- The current Core rule evaluates pitch only; roll and yaw do not affect its result.
- Returns a demo `SAFE` or `VIOLATION` status and explanatory text. It does not produce a clinical confidence estimate.

## FAQ

### Does the result tell me whether a head movement is medically safe?

No. The threshold is for exercising the demo response path only. It is not derived from an individual's procedure or care plan.

### Does dragging the glasses update the request?

Yes. The Studio updates pitch and yaw from the drag, then submits those synthetic values to the configured MCP endpoint. That UI behavior does not turn the threshold into a clinical rule.

### Does OcuGuard Core control wearable hardware?

No. It only returns a response payload for the demo UI.

## Boundaries

No sensor calibration, patient-specific threshold, physician configuration, or hardware output is implemented. Do not use the labels or sound as a real-world warning system.
