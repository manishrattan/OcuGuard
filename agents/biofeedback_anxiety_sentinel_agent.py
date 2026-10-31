from __future__ import annotations

import logging
from typing import Any, Dict

from core.plugin_interface import OcuGuardSubAgentPlugin
from core.schemas import OrchestratorPayload, TelemetryFrame

logger = logging.getLogger("OcuGuard.BiofeedbackAnxietySentinelAgent")

PANIC_PHRASES = ["wavy lines", "will i be okay", "panicking", "terrified", "anxious", "cannot breathe"]

class BiofeedbackAnxietySentinelAgent(OcuGuardSubAgentPlugin):
    """Biofeedback anxiety sentinel for vocal stress and verbal panic cues.

    This agent uses voice stress metrics and transcript signals to surface support
    wording tied to standard 12-to-18 month neuroadaptation milestones.
    """

    def evaluate(self, payload: Dict[str, Any]) -> OrchestratorPayload:
        try:
            frame = TelemetryFrame(**payload)
        except Exception as exc:  # pragma: no cover
            logger.error("Biofeedback anxiety payload invalid: %s", exc)
            return self._safe_default()

        try:
            return self._build_payload(frame)
        except Exception as exc:
            logger.error("Biofeedback anxiety evaluation failed: %s", exc)
            return self._safe_default()

    def _build_payload(self, frame: TelemetryFrame) -> OrchestratorPayload:
        input_lower = frame.input_string.lower()
        has_panic_phrase = any(phrase in input_lower for phrase in PANIC_PHRASES)
        elevated = frame.vocal_stress_score >= 0.8 or has_panic_phrase

        status = "WARN" if elevated else "SAFE"
        reassurance = (
            "Your visual system is within stable adaptation bounds. Continue gradual reconditioning and maintain your current perceptual pacing."
            if not elevated
            else (
                "The signal indicates heightened stress during the 12-to-18 month neuroadaptation phase. "
                "That is a common window for vitrectomy-like spatial recalibration. Breathe slowly, anchor on a neutral target, "
                "and allow the cortical fusion pathways to settle with repeated, gentle exposures."
            )
        )

        if elevated and frame.oem_platform:
            reassurance += f" This reassurance is tuned for {frame.oem_platform} display dynamics."

        return OrchestratorPayload(
            status=status,
            ui_transformations={
                "scale_factor": 1.0,
                "css_warp_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                "vocal_stress_score": round(frame.vocal_stress_score, 4),
                "panic_phrase_detected": has_panic_phrase
            },
            cognitive_reassurance_string=reassurance
        )

    @property
    def condition_id(self) -> str:
        return "BIOFEEDBACK_ANXIETY_SENTINEL"

    def validate_safety_envelope(self, telemetry_frame: Dict[str, Any]) -> Dict[str, Any]:
        return self.evaluate(telemetry_frame).model_dump()

    def _safe_default(self) -> OrchestratorPayload:
        return OrchestratorPayload(
            status="SAFE",
            ui_transformations={
                "scale_factor": 1.0,
                "css_warp_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                "vocal_stress_score": 0.0,
                "panic_phrase_detected": False
            },
            cognitive_reassurance_string=(
                "Biofeedback fallback engaged. Default calm-state guidance is active while the system re-synchronizes audio and transcript metrics."
            )
        )
