# Eye Sentinel

**Studio mode:** `EYE_SENTINEL`  
**Code:** `agents/eye_sentinel.py`  
**Collection:** Studio agents

## What it does

Eye Sentinel is a prototype text-and-telemetry classifier. Its local rules look for supplied text patterns associated with acute, urgent, or routine visual discomfort. If an LLM is configured, the implementation can also send the supplied text and flags to that provider; otherwise it uses the local keyword matcher.

The code contains separate post-operative examples: phrases such as “face down” or the `post_op_recovery` flag can select a position-message path, and an orientation check uses a configured -55° pitch boundary when its specific post-op context is present.

## Inputs and outputs

- Supplied text, history flags, multimodal flags, and telemetry in the request.
- Prototype statuses such as `CRITICAL_ALERT`, `ELEVATED_ALERT`, `STANDARD_LOG`, or `ADAPTIVE_GUIDANCE`.
- A text explanation and, for some paths, structured post-op fields.

## FAQ

### Does this diagnose an eye condition?

No. Keyword matches and model-generated classifications are experimental and cannot determine the cause or urgency of a symptom.

### Does it watch my eyes or head?

No. It only evaluates values and text included in a request. The Studio does not connect a camera or motion sensor to this agent.

### Should I follow the post-op positioning text?

No. The position rotation and posture messages are unvalidated sample behavior, not an individualized surgeon's instruction. Follow the care team's actual instructions and contact them with questions.

### Does the Studio send the `post_op_recovery` flag?

The current Studio exposes `cataract_surgery` and `retinal_disease` synthetic history flags; it does not expose a `post_op_recovery` control. Do not infer the specific post-op branch from those flags.

### Can I enter a transcript by voice?

The Studio offers optional browser speech-to-text for this text-oriented mode. The browser's speech service may process audio outside this app; only the resulting transcript is added to the text field. Typed input remains available.

## Boundaries

The -55° rule is hard-coded demo logic, not a medical threshold. An LLM may be used when configured. No camera, microphone, alert service, or validated clinical protocol is implemented here.
