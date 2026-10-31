from collections.abc import Mapping
from typing import Any, Protocol

from core.schemas import TelemetryFrame


class OEMTelemetryAdapter(Protocol):
    """Translate a vendor SDK frame into OcuGuard's vendor-neutral input."""

    def to_telemetry_frame(
        self, vendor_frame: Mapping[str, Any]
    ) -> TelemetryFrame:
        """Normalize one vendor frame without retaining vendor SDK objects."""
        ...
