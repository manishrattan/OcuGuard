# OcuGuard Agent FAQ & Capabilities

This directory documents the current prototype behavior. Start with the [FAQ & Capabilities page](../../pages/1_FAQ_and_Capabilities.py) in Streamlit for a browsable, searchable guide.

## Studio agents

These ten modes can be selected in OcuGuard Studio:

- [Eye Sentinel](./eye-sentinel.md)
- [OcuGuard Core](./ocuguard-core.md)
- [Gaze Compass](./gaze-compass.md)
- [Tabular Layout Speech](./tabular-layout-speech.md)
- [Ergonomic Schedule](./ergonomic-schedule.md)
- [Ambient Luminance](./ambient-luminance.md)
- [Be My Eyes](./be-my-eyes.md)
- [Aniseikonia Scaling](./aniseikonia-scaling.md)
- [Metamorphopsia Grid Remapper](./metamorphopsia-grid-remapper.md)
- [Biofeedback Anxiety Sentinel](./biofeedback-anxiety-sentinel.md)

## Platform and experimental modules

- [Supervisor](./supervisor.md) is used by the REST request path; it is not a selectable Studio mode.
- [Pre-Op Waitlist](./preop-waitlist.md) exists as a code module but is not currently registered in the main API or selectable in Studio.

All descriptions are based on the checked-in implementation. These prototypes are not validated medical or safety systems. Text and numeric inputs are supplied by the demo; an agent does not imply camera, microphone, wearable, live helper, or lens-control integration.
