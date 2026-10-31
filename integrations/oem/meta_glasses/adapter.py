from collections.abc import Mapping
from typing import Any

from core.schemas import TelemetryFrame


class MetaGlassesExampleAdapter:
    """Map a synthetic, normalized demo frame to OcuGuard's shared schema.

    The input shape is an OcuGuard example, not a Meta SDK contract.
    """

    def to_telemetry_frame(
        self, vendor_frame: Mapping[str, Any]
    ) -> TelemetryFrame:
        missing_fields = [
            field
            for field in ("user_id", "input_string", "orientation")
            if field not in vendor_frame
        ]
        if missing_fields:
            raise ValueError(
                f"Missing required example fields: {', '.join(missing_fields)}"
            )

        orientation = vendor_frame["orientation"]
        if not isinstance(orientation, Mapping):
            raise ValueError("orientation must be a mapping")

        angle_fields = ("pitch_degrees", "yaw_degrees", "roll_degrees")
        missing_angles = [
            field for field in angle_fields if field not in orientation
        ]
        if missing_angles:
            raise ValueError(
                f"Missing required orientation fields: {', '.join(missing_angles)}"
            )

        return TelemetryFrame(
            user_id=vendor_frame["user_id"],
            input_string=vendor_frame["input_string"],
            pitch=orientation["pitch_degrees"],
            yaw=orientation["yaw_degrees"],
            roll=orientation["roll_degrees"],
            oem_platform="meta_glasses_example",
        )
