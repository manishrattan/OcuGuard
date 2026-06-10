# MIT License
# Copyright (c) 2026 The OcuGuard Project

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from plugin_interface import OcuGuardSubAgentPlugin
from schemas import TelemetryFrame, StreamResponseData

logger = logging.getLogger("OcuGuard.AmbientLuminance")


class AmbientLuminanceAgent(OcuGuardSubAgentPlugin):
    """Environmental Contrast Optimization and Adaptive Lighting Assistant.
    
    Ingests environmental light metadata and provides non-diagnostic optimization
    tips for smart lens features and acoustic descriptions.
    """

    LIGHTING_PROFILES = {
        "high_glare": {"threshold": 80, "recommendation": "High glare detected. Consider enabling adaptive lens tinting or adjusting viewing angle."},
        "low_light": {"threshold": 30, "recommendation": "Low ambient light detected. Enhance contrast settings or increase acoustic description detail."},
        "optimal": {"threshold_min": 30, "threshold_max": 80, "recommendation": "Ambient lighting conditions optimal for current task."}
    }

    def __init__(self):
        """Initializes the AmbientLuminanceAgent."""
        pass

    @property
    def condition_id(self) -> str:
        """Returns the unique condition tracking ID."""
        return "ENVIRONMENTAL_CONTRAST_ASSIST"

    def validate_safety_envelope(self, telemetry_frame: Dict[str, Any]) -> Dict[str, Any]:
        """Plugin Interface implementation."""
        try:
            frame = TelemetryFrame(**telemetry_frame)
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            raise ValueError(f"Invalid telemetry format: {e}")

        timestamp = datetime.now(timezone.utc).isoformat()
        response_data = self.evaluate_environment(frame, timestamp)
        return response_data.model_dump()

    def evaluate_environment(self, frame: TelemetryFrame, timestamp: str) -> StreamResponseData:
        """Evaluates environmental lighting and provides optimization guidance.

        Args:
            frame: TelemetryFrame with environmental metadata.
            timestamp: ISO 8601 timestamp.

        Returns:
            StreamResponseData with environmental optimization guidance.
        """
        status = "STANDARD_LOG"
        action = "Environmental baseline recorded."
        reasoning = "Ambient lighting parameters within acceptable range."
        confidence = 0.80

        # Parse ambient light intensity if provided
        ambient_light = frame.ambient_light_intensity
        contrast_mode = frame.contrast_adaptation_mode

        # Check for high glare conditions
        if ambient_light is not None and ambient_light > self.LIGHTING_PROFILES["high_glare"]["threshold"]:
            status = "ELEVATED_ALERT"
            action = self.LIGHTING_PROFILES["high_glare"]["recommendation"]
            reasoning = f"Ambient light intensity {ambient_light}% exceeds high-glare threshold {self.LIGHTING_PROFILES['high_glare']['threshold']}%."
            confidence = 0.90

        # Check for low light conditions
        elif ambient_light is not None and ambient_light < self.LIGHTING_PROFILES["low_light"]["threshold"]:
            status = "ELEVATED_ALERT"
            action = self.LIGHTING_PROFILES["low_light"]["recommendation"]
            reasoning = f"Ambient light intensity {ambient_light}% below low-light threshold {self.LIGHTING_PROFILES['low_light']['threshold']}%."
            confidence = 0.88

        # Optimal lighting range
        elif ambient_light is not None:
            status = "STANDARD_LOG"
            action = self.LIGHTING_PROFILES["optimal"]["recommendation"]
            reasoning = f"Ambient light {ambient_light}% in optimal range ({self.LIGHTING_PROFILES['optimal']['threshold_min']}-{self.LIGHTING_PROFILES['optimal']['threshold_max']}%)."
            confidence = 0.92

        # Check for explicit contrast mode requests in input string
        if "contrast" in frame.input_string.lower() or "bright" in frame.input_string.lower() or "dark" in frame.input_string.lower():
            action += " [User Contrast Request Detected] Adaptive mode activated."
            confidence = max(confidence, 0.85)

        return StreamResponseData(
            status=status,
            action_required=action,
            confidence_score=confidence,
            reasoning=reasoning,
            timestamp=timestamp
        )

    def _evaluate_local(self, frame: TelemetryFrame, timestamp: str) -> StreamResponseData:
        """Fallback local evaluation (same as evaluate_environment for this agent)."""
        return self.evaluate_environment(frame, timestamp)
