# Metamorphopsia Grid Remapper

**Studio mode:** `METAMORPHOPSIA_GRID_REMAPPER`  
**Code:** `agents/metamorphopsia_grid_remapper_agent.py`  
**Collection:** Studio agents

## What it does

This mode maps a supplied text-waviness index to a simplified warp-matrix payload. The current code clamps the input to 0–1 and labels values above 0.1 `WARN`; it does not render a warped grid.

## Inputs and outputs

- A synthetic `text_wavy_index`.
- Returns `SAFE` or `WARN`, reassurance text, and a simplified `css_warp_matrix`.
- The prototype formula describes a maximum 5% vertical distortion amplitude.

## FAQ

### Does it detect wavy lines?

No. The waviness value is supplied by the user or caller; no image processing is implemented.

### Does the demo actually remap text?

No. It returns a sample transformation payload only. The UI does not run a shader or modify the displayed text.

### Is this a vision test?

No. Neither the input nor the output is a diagnostic measurement.

## Boundaries

The matrix is a simplified experiment, not a corrective visual aid or a validated treatment for metamorphopsia.
