# Biofeedback Anxiety Sentinel

**Studio mode:** `BIOFEEDBACK_ANXIETY_SENTINEL`  
**Code:** `agents/biofeedback_anxiety_sentinel_agent.py`  
**Collection:** Studio agents

## What it does

This mode combines a manually supplied synthetic stress score with a small set of supplied text phrases. In the current code, a score of 0.8 or higher or a matching phrase such as “anxious” or “cannot breathe” returns `WARN`; otherwise it returns `SAFE`.

## Inputs and outputs

- A manually entered synthetic `vocal_stress_score` from 0 to 1 and text.
- Returns a status, a phrase-detected flag, the supplied score, and reassurance text.

## FAQ

### Does it measure vocal stress from a microphone?

No. The score is entered manually and is not inferred from speech. The Studio offers optional browser speech-to-text for entering a transcript; the browser's speech service may process audio outside this app. Only the transcript is added to the text field, and no raw audio is analyzed by OcuGuard.

### Does it assess anxiety or breathing problems?

No. Phrase matching and a numeric threshold are not a mental-health, respiratory, or emergency assessment.

### Can the reassurance text tell me what to do medically?

No. It is prototype copy, not care guidance. For urgent symptoms or distress, use appropriate human or emergency support.

## Boundaries

The threshold and phrase list are experimental, and output text is not validated for clinical use. No biometric sensor or intervention is implemented.
