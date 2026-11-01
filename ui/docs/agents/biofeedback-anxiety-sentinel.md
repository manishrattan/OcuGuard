# Biofeedback Anxiety Sentinel

**Studio mode:** `BIOFEEDBACK_ANXIETY_SENTINEL`  
**Code:** `agents/biofeedback_anxiety_sentinel_agent.py`  
**Collection:** Studio agents

## What it does

This mode combines a caller-supplied vocal-stress score with a small set of supplied text phrases. In the current code, a score of 0.8 or higher or a matching phrase such as “anxious” or “cannot breathe” returns `WARN`; otherwise it returns `SAFE`.

## Inputs and outputs

- A synthetic `vocal_stress_score` and text.
- Returns a status, a phrase-detected flag, the supplied score, and reassurance text.

## FAQ

### Does it listen to a microphone or analyze a voice?

No. The score and text are supplied values. The Studio does not capture audio or run voice analysis.

### Does it assess anxiety or breathing problems?

No. Phrase matching and a numeric threshold are not a mental-health, respiratory, or emergency assessment.

### Can the reassurance text tell me what to do medically?

No. It is prototype copy, not care guidance. For urgent symptoms or distress, use appropriate human or emergency support.

## Boundaries

The threshold and phrase list are experimental, and output text is not validated for clinical use. No biometric sensor or intervention is implemented.
