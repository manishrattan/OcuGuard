# MIT License
# Copyright (c) 2026 The OcuGuard Project

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from plugin_interface import OcuGuardSubAgentPlugin
from schemas import TelemetryFrame, StreamResponseData

logger = logging.getLogger("OcuGuard.ErgonomicSchedule")


class ErgonomicScheduleAgent(OcuGuardSubAgentPlugin):
    """Postural Habit Tracking and Wellness Routine Monitoring Assistant.
    
    Monitors time-series posture data to help users maintain self-directed 
    wellness routines and detect ergonomic habit thresholds.
    """

    POSTURE_THRESHOLDS = {
        "excessive_head_tilt": -35.0,      # Pitch angle (forward bending) threshold
        "sustained_duration_warning": 1800.0,  # Seconds: 30 minutes
        "sustained_duration_critical": 3600.0  # Seconds: 60 minutes
    }

    def __init__(self):
        """Initializes the ErgonomicScheduleAgent."""
        pass

    @property
    def condition_id(self) -> str:
        """Returns the unique condition tracking ID."""
        return "USER_TIMED_HABIT_TRACKING"

    def validate_safety_envelope(self, telemetry_frame: Dict[str, Any]) -> Dict[str, Any]:
        """Plugin Interface implementation."""
        try:
            frame = TelemetryFrame(**telemetry_frame)
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            raise ValueError(f"Invalid telemetry format: {e}")

        timestamp = datetime.now(timezone.utc).isoformat()
        response_data = self.evaluate_posture(frame, timestamp)
        return response_data.model_dump()

    def evaluate_posture(self, frame: TelemetryFrame, timestamp: str) -> StreamResponseData:
        """Evaluates postural habits and wellness routine adherence.

        Args:
            frame: TelemetryFrame with posture metrics.
            timestamp: ISO 8601 timestamp.

        Returns:
            StreamResponseData with habit tracking guidance.
        """
        status = "STANDARD_LOG"
        action = "Postural metrics within normal parameters. Continue current wellness routine."
        reasoning = "Ergonomic tracking active."
        confidence = 0.85

        # Check for excessive forward bending
        if frame.pitch < self.POSTURE_THRESHOLDS["excessive_head_tilt"]:
            status = "ELEVATED_ALERT"
            action = "Ergonomic Notice: Extended forward-facing posture detected. Consider adjusting your workstation or taking a postural break."
            reasoning = f"Head pitch {frame.pitch}° exceeds ergonomic threshold {self.POSTURE_THRESHOLDS['excessive_head_tilt']}°."
            confidence = 0.92

        # Check for sustained posture duration (suggests lack of movement breaks)
        if frame.posture_hold_duration >= self.POSTURE_THRESHOLDS["sustained_duration_critical"]:
            status = "ELEVATED_ALERT"
            action = "Ergonomic Alert: Sustained posture for 1+ hour detected. Stand, stretch, or move to break the habit cycle."
            reasoning = f"Posture held for {frame.posture_hold_duration}s (critical: {self.POSTURE_THRESHOLDS['sustained_duration_critical']}s)."
            confidence = 0.95

        elif frame.posture_hold_duration >= self.POSTURE_THRESHOLDS["sustained_duration_warning"]:
            status = "ELEVATED_ALERT"
            action = "Ergonomic Cue: Postural hold duration approaching 30+ minutes. Consider a movement break."
            reasoning = f"Posture held for {frame.posture_hold_duration}s (warning: {self.POSTURE_THRESHOLDS['sustained_duration_warning']}s)."
            confidence = 0.88

        # Check if user has defined wellness goals
        if frame.history.workplace_ergonomic_goals:
            action += " [Habit Tracking Active] Your wellness goals are being monitored."

        return StreamResponseData(
            status=status,
            action_required=action,
            confidence_score=confidence,
            reasoning=reasoning,
            timestamp=timestamp
        )

    def _evaluate_local(self, frame: TelemetryFrame, timestamp: str) -> StreamResponseData:
        """Fallback local evaluation (same as evaluate_posture for this agent)."""
        return self.evaluate_posture(frame, timestamp)
