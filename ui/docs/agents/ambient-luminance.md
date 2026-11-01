# Ambient Luminance

**Studio mode:** `AMBIENT_LUMINANCE`  
**Code:** `agents/ambient_luminance.py`  
**Collection:** Studio agents

## What it does

Ambient Luminance evaluates a caller-supplied light-intensity value and returns a simple contrast or glare suggestion. In the current implementation, values above 80 trigger a high-glare suggestion, below 30 trigger a low-light suggestion, and values in between receive an “optimal” baseline message. Text containing “contrast,” “bright,” or “dark” adds a request-detected note.

## Inputs and outputs

- A synthetic `ambient_light_intensity` value from 0 to 100.
- A `contrast_adaptation_mode` and supplied text.
- Returns a status and text suggestion.

## FAQ

### Does it measure the room's light?

No. The value comes from the form; no camera or light sensor is connected.

### Does it change lens tint or screen contrast?

No. Recommendations are returned as text only. No electrochromic lens, display, or wearable control is implemented.

### Is the “optimal” range medically defined?

No. It is an illustrative code range (30–80), not a personalized or clinically validated threshold.

## Boundaries

Lighting varies by device, task, and person. Do not treat this mode as an accessibility calibration or vision-care recommendation.
