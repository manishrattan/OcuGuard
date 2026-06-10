# MIT License
# Copyright (c) 2026 The OcuGuard Project
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import re
import logging
from typing import Dict, Any, Tuple
from schemas import TelemetryFrame

logger = logging.getLogger("OcuGuard.Supervisor")

class SupervisorAgent:
    """Gateway Security, Data Redaction, and Ingestion Router.

    This agent acts as the primary gatekeeper for incoming wearer telemetry streams.
    It scrubs PII and validates security tokens before passing payloads.
    """

    # PII scrubbing regexes
    EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    PHONE_REGEX = re.compile(r"\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b")
    SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

    def __init__(self, expected_client_id: str = "OCUGUARD_CLIENT", expected_user_token: str = "OCUGUARD_TOKEN"):
        """Initializes the SupervisorAgent.

        Args:
            expected_client_id: The client identifier string expected in validation.
            expected_user_token: The user token string expected in validation.
        """
        self.expected_client_id = expected_client_id
        self.expected_user_token = expected_user_token

    def redact_pii(self, input_text: str) -> str:
        """Scrubs identifiable data (PII) from strings (email, phone, ssn).

        Args:
            input_text: Raw input string from the client stream.

        Returns:
            A redacted string where sensitive matches are replaced with [REDACTED].
        """
        if not input_text:
            return ""
        text = self.EMAIL_REGEX.sub("[REDACTED_EMAIL]", input_text)
        text = self.PHONE_REGEX.sub("[REDACTED_PHONE]", text)
        text = self.SSN_REGEX.sub("[REDACTED_SSN]", text)
        return text

    def validate_and_route(self, frame: TelemetryFrame) -> Tuple[bool, str, TelemetryFrame]:
        """Inspects telemetry tokens and routes request.

        If validation parameters drop out, network drops are flagged,
        or tokens are invalid, it instructs downstream systems to slip into
        local mathematical fallback loop.

        Args:
            frame: The incoming TelemetryFrame object.

        Returns:
            Tuple containing:
            - is_valid: bool indicating if validation was successful.
            - route_mode: str ("CLOUD_HYBRID" or "LOCAL_FALLBACK").
            - redacted_frame: TelemetryFrame with redacted input_string.
        """
        # Scrub PII first
        scrubbed_input = self.redact_pii(frame.input_string)
        
        # Construct updated redacted telemetry frame
        redacted_frame = TelemetryFrame(
            user_id=frame.user_id,
            input_string=scrubbed_input,
            multimodal_flags=frame.multimodal_flags.copy(),
            history=frame.history,
            pitch=frame.pitch,
            yaw=frame.yaw,
            roll=frame.roll,
            gaze_x=frame.gaze_x,
            gaze_y=frame.gaze_y,
            target_x=frame.target_x,
            target_y=frame.target_y,
            blind_x=frame.blind_x,
            blind_y=frame.blind_y,
            blind_r=frame.blind_r,
            confidence=frame.confidence,
            client_id=frame.client_id,
            user_token=frame.user_token
        )

        # Force local fallback if network drop is explicitly flagged
        if "network_drop" in frame.multimodal_flags:
            logger.warning("Network drop flag detected. Routing to fast local mathematical loop.")
            return False, "LOCAL_FALLBACK", redacted_frame

        # Validate security tokens
        if not frame.client_id or not frame.user_token:
            logger.warning("Structural token parameters missing. Routing to local mathematical loop.")
            return False, "LOCAL_FALLBACK", redacted_frame

        if frame.client_id != self.expected_client_id or frame.user_token != self.expected_user_token:
            logger.warning("Token verification failed. Routing to local mathematical loop.")
            return False, "LOCAL_FALLBACK", redacted_frame

        return True, "CLOUD_HYBRID", redacted_frame
