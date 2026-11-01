# Ergonomic Schedule

**Studio mode:** `ERGONOMIC_SCHEDULE`  
**Code:** `agents/ergonomic_schedule.py`  
**Collection:** Studio agents

## What it does

Ergonomic Schedule evaluates supplied posture telemetry and a duration value against simple habit-prompt thresholds. It can return a reminder to consider a movement break or adjust a workstation.

## Inputs and outputs

- Supplied pitch and `posture_hold_duration` in seconds.
- Optional `workplace_ergonomic_goals` history flag.
- Returns a status, text prompt, and basic reasoning.

The current rules flag pitch below -35°, duration at 30 minutes or more, and duration at 60 minutes or more. The duration checks use the same `ELEVATED_ALERT` status but different text.

## FAQ

### Does this monitor posture continuously?

No. The mode evaluates the values in one submitted frame. It has no continuous sensor connection or timer.

### Is this a post-surgery positioning coach?

No. These are general ergonomic demo prompts, not instructions for retinal surgery recovery or any other care plan.

### Can I change the thresholds for a patient?

Not through this prototype UI. The current thresholds are code constants and have not been clinically validated.

## Boundaries

It does not establish a safe posture, measure movement, or replace workplace ergonomics advice or a clinician's instructions.
