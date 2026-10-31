from __future__ import annotations

import logging
import math
from typing import Any, Dict, List

from core.plugin_interface import OcuGuardSubAgentPlugin
from core.schemas import OrchestratorPayload, TelemetryFrame

logger = logging.getLogger("OcuGuard.MetamorphopsiaGridRemapperAgent")

class MetamorphopsiaGridRemapperAgent(OcuGuardSubAgentPlugin):
    """Geometric grid remapping assistant for text waviness (metamorphopsia).

    This agent evaluates a user's perceived text waviness index and generates a
    calibrated 2D geometric warping transformation matrix to stabilize digital
    text layouts on smart eyewear or monitors.
    """

    def remap(self, payload: Dict[str, Any]) -> OrchestratorPayload:
        try:
            frame = TelemetryFrame(**payload)
        except Exception as exc:  # pragma: no cover
            logger.error("Metamorphopsia remap payload invalid: %s", exc)
            return self._safe_default()

        try:
            return self._build_payload(frame)
        except Exception as exc:
            logger.error("Metamorphopsia remap evaluation failed: %s", exc)
            return self._safe_default()

    def _build_payload(self, frame: TelemetryFrame) -> OrchestratorPayload:
        # Generate a sinusoidal warp for the y-axis based on the waviness index
        # This is a simplified model; a real implementation might use more complex mesh warping
        waviness = max(0.0, min(1.0, frame.text_wavy_index))
        amplitude = 0.05 * waviness  # Max 5% vertical distortion
        frequency = 2.0 * math.pi * (1.0 + waviness)

        # This matrix is a simplified representation. A real CSS transform might use `matrix3d`
        # or a GLSL shader for a true per-pixel warp.
        css_warp_matrix: List[List[float]] = [
            [1.0, math.sin(frequency) * amplitude, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ]

        status = "WARN" if waviness > 0.1 else "SAFE"
        reassurance = (
            "Text geometry is stable. The display matrix is maintaining a linear text grid."
            if status == "SAFE"
            else "Applying a geometric warp transform to counteract perceived text waviness and stabilize the visual field."
        )

        return OrchestratorPayload(
            status=status,
            ui_transformations={"scale_factor": 1.0, "css_warp_matrix": css_warp_matrix},
            cognitive_reassurance_string=reassurance
        )

    @property
    def condition_id(self) -> str:
        return "METAMORPHOPSIA_GRID_REMAPPER"

    def validate_safety_envelope(self, telemetry_frame: Dict[str, Any]) -> Dict[str, Any]:
        return self.remap(telemetry_frame).model_dump()

    def _safe_default(self) -> OrchestratorPayload:
        return OrchestratorPayload(
            status="SAFE",
            ui_transformations={
                "scale_factor": 1.0,
                "css_warp_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
            },
            cognitive_reassurance_string="Grid remapping fallback engaged. Default linear text geometry is active."
        )