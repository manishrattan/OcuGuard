# Gaze Compass

**Studio mode:** `GAZE_COMPASS`  
**Code:** `agents/gaze_compass.py`  
**Collection:** Studio agents

## What it does

Gaze Compass is a coordinate-based prototype for exploring target placement relative to a supplied blind-spot center and radius. Its local calculation compares target and blind-spot coordinates, then returns a horizontal pan value clamped to -1.0 through +1.0.

## Inputs and outputs

- Supplied `target_x`, `target_y`, `blind_x`, `blind_y`, and `blind_r`.
- The request schema also includes `gaze_x` and `gaze_y`; the local fallback calculation currently bases its distance and pan on the target and blind-spot coordinates.
- Returns `SAFE` or `VIOLATION`, a text cue, and `pan_localization`.

## FAQ

### Does it track my gaze or find objects?

No. Coordinates are supplied by the caller. There is no live eye tracker, camera, or object detector in this Studio mode.

### Does the pan value move an object on screen?

No. It is response metadata for a possible future renderer. This demo displays the response but does not apply the returned pan to wearable content.

### Is this a scotoma assessment?

No. The supplied coordinates and radius are synthetic inputs; the calculation is an experiment, not an assessment of an individual's vision.

## Boundaries

The output is not calibrated to a person's Preferred Retinal Locus and must not be used as navigation or safety guidance.
