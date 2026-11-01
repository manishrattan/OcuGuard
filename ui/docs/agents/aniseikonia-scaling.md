# Aniseikonia Scaling

**Studio mode:** `ANISEIKONIA_SCALING`  
**Code:** `agents/aniseikonia_scaling_agent.py`  
**Collection:** Studio agents

## What it does

Aniseikonia Scaling converts a supplied perceived-size delta into a bounded experimental scale factor and a simple 2D matrix. The result is a proposed UI transform payload; the Studio does not apply it to text or a wearable display.

## Inputs and outputs

- A synthetic `perceived_size_delta`.
- Returns `SAFE` when the absolute delta is at most 0.15, otherwise `WARN`.
- Returns a `scale_factor` (bounded in the current code from 0.75 to 1.15) and a `css_warp_matrix`.

## FAQ

### Does it measure differences between my eyes?

No. The value is supplied by the caller; there is no eye exam, camera, or calibration workflow.

### Does the returned matrix change the UI?

No. It is metadata for experimentation. The Studio displays the response but does not apply the transform.

### Is the scale factor a prescription?

No. The formula is a software demonstration and is not clinically validated.

## Boundaries

Do not use the output to adjust a prescription, lens, or patient-facing display without appropriate clinical and engineering validation.
