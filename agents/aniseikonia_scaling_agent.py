from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from core.plugin_interface import OcuGuardSubAgentPlugin
from core.schemas import OrchestratorPayload, TelemetryFrame

logger = logging.getLogger("OcuGuard.AniseikoniaScalingAgent")

class AniseikoniaScalingAgent(OcuGuardSubAgentPlugin):
    """Dynamic text scaling assistant for perceived size asymmetry.

    This agent evaluates a user's perceived size delta and returns a calibrated UI
    transformation payload to normalize text rendering dimensions for the brain's
    binocular fusion loop.
    """

    def calibrate(self, payload: Dict[str, Any]) -> OrchestratorPayload:
        try:
            frame = TelemetryFrame(**payload)
        except Exception as exc:  # pragma: no cover
            logger.error("Aniseikonia calibration payload invalid: %s", exc)
            return self._safe_default()

        try:
            return self._build_payload(frame)
        except Exception as exc:
            logger.error("Aniseikonia calibration failed: %s", exc)
            return self._safe_default()

    def _build_payload(self, frame: TelemetryFrame) -> OrchestratorPayload:
        scale_factor = 1.0
        if frame.perceived_size_delta > 0.0:
            scale_factor = 1.0 / (1.0 + min(frame.perceived_size_delta, 0.75))
        elif frame.perceived_size_delta < 0.0:
            scale_factor = 1.0 - max(frame.perceived_size_delta, -0.25)

        scale_factor = round(max(0.75, min(1.15, scale_factor)), 4)

        css_warp_matrix: List[List[float]] = [
            [scale_factor, 0.0, 0.0],
            [0.0, scale_factor, 0.0],
            [0.0, 0.0, 1.0]
        ]

        status = "SAFE" if abs(frame.perceived_size_delta) <= 0.15 else "WARN"
        reason = (
            "Text rendering dimensions are within an acceptable fusion range."
            if status == "SAFE"
            else "Perceived size delta is elevated; apply inverse scaling to normalize text geometry."
        )

        reassurance = (
            "Visual calibration is stable. The display matrix is adjusting to preserve your fusion loop "
            "and help text remain aligned during natural binocular adaptation."
            if status == "SAFE"
            else "Applying a calibrated inverse scale factor to preserve fusion comfort while you track through the display field."
        )

        if frame.oem_platform:
            reassurance += f" OEM platform: {frame.oem_platform}."

        return OrchestratorPayload(
            status=status,
            ui_transformations={
                "scale_factor": scale_factor,
                "css_warp_matrix": css_warp_matrix,
                "visual_field_clearance": round(frame.visual_field_clearance, 4)
            },
            cognitive_reassurance_string=reassurance
        )

    @property
    def condition_id(self) -> str:
        return "ANISEIKONIA_SCALING"

    def validate_safety_envelope(self, telemetry_frame: Dict[str, Any]) -> Dict[str, Any]:
        return self.calibrate(telemetry_frame).model_dump()

    def _safe_default(self) -> OrchestratorPayload:
        return OrchestratorPayload(
            status="SAFE",
            ui_transformations={
                "scale_factor": 1.0,
                "css_warp_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                "visual_field_clearance": 1.0
            },
            cognitive_reassurance_string=(
                "Calibration fallback engaged. Default text scaling is active to keep the rendering path stable "
                "while the system waits for validated visual metrics."
            )
        )
