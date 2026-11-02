# Be My Eyes (local prototype mode)

**Studio mode:** `BE_MY_EYES`  
**Code:** `agents/be_my_eyes.py`  
**Collection:** Studio agents

## What it does

This mode demonstrates a text-and-confidence escalation rule. Its local fallback returns `ESCALATION` when supplied confidence is below 82% or the supplied text contains one of its help-related phrases. Otherwise it returns `SAFE`. The Studio exposes confidence as a manual synthetic percentage; it does not calculate confidence from an image. If configured, an LLM may process the text and confidence value.

## Inputs and outputs

- Supplied text and a manually entered confidence percentage from 0 to 100.
- Returns `SAFE` or `ESCALATION`, explanation text, and an escalation marker when applicable.

## FAQ

### Does this connect me to a sighted helper?

No. The code does not start a video call, connect to Be My Eyes, or open a human-helper session.

### Does the confidence score come from computer vision?

No. It is supplied by the caller; this UI does not calculate it from an image or camera. Optional browser speech-to-text can enter a transcript, but it does not produce or change the confidence value.

### What happens when escalation is detected?

The prototype returns an escalation status and message. A real person is not notified.

## Boundaries

Do not rely on this mode for emergency response, medication or dosage checks, or tasks requiring human verification. No live video gateway or staffed support service is implemented.
