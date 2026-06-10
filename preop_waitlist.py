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

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from plugin_interface import OcuGuardSubAgentPlugin
from schemas import TelemetryFrame, TriageResponseData

# Try importing langchain components safely
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    ChatOpenAI = None
    class SystemMessage:
        def __init__(self, content: str):
            self.content = content
    class HumanMessage:
        def __init__(self, content: str):
            self.content = content
    LANGCHAIN_AVAILABLE = False

logger = logging.getLogger("OcuGuard.PreOpWaitlist")

class PreOpWaitlistAgent(OcuGuardSubAgentPlugin):
    """Healthcare Access Gap Bridge (Pre-Surgery Contrast Support).

    Supports patients on surgical lists for cataracts or corneal clouding.
    Converts low-contrast text structures and tables into high-priority structural audio descriptions.
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        """Initializes the PreOpWaitlistAgent."""
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.llm = None
        if LANGCHAIN_AVAILABLE and self.openai_api_key:
            try:
                self.llm = ChatOpenAI(
                    model="gpt-4",
                    openai_api_key=self.openai_api_key,
                    temperature=0.0,
                    request_timeout=2.0,
                    max_retries=1
                )
            except Exception as e:
                logger.error(f"Failed to initialize ChatOpenAI: {e}. Fallback active.")

    @property
    def condition_id(self) -> str:
        """Returns the unique condition identifier."""
        return "PRE_OP_WAITLIST_CONTRAST_COMPENSATION"

    def validate_safety_envelope(self, telemetry_frame: Dict[str, Any]) -> Dict[str, Any]:
        """Validates low-contrast document telemetry.

        Args:
            telemetry_frame: Dict matching TelemetryFrame.

        Returns:
            Dict containing parsed structural audio description.
        """
        try:
            frame = TelemetryFrame(**telemetry_frame)
        except Exception as e:
            logger.error(f"Validation failed for Pre-Op Bridge: {e}")
            raise ValueError(f"Invalid telemetry format: {e}")

        timestamp = datetime.now(timezone.utc).isoformat()
        response = self.evaluate_contrast(frame, timestamp)
        return response.model_dump()

    def evaluate_contrast(self, frame: TelemetryFrame, timestamp: str) -> TriageResponseData:
        """Converts text streams into sequential audio outlines.

        Args:
            frame: TelemetryFrame dataset.
            timestamp: ISO 8601 timestamp.

        Returns:
            TriageResponseData.
        """
        local_result = self._evaluate_local(frame, timestamp)

        if not self.llm:
            return local_result

        system_prompt = (
            "You are the Pre-Op Waitlist Contrast Assistant. You assist patients with cataract-induced vision cloudiness.\n"
            "Analyze the low-contrast raw OCR text stream and convert it into a structured, high-priority, "
            "hands-free verbal description for workplace productivity.\n"
            "Format the output strictly as a JSON payload:\n"
            "{\n"
            "  \"status\": \"WAITLIST\",\n"
            "  \"action_required\": \"Verbal description of the document or table structure\",\n"
            "  \"confidence_score\": 0.0-1.0,\n"
            "  \"reasoning\": \"Brief layout classification\"\n"
            "}"
        )

        user_content = f"Raw Document Text:\n{frame.input_string}"

        for attempt in range(2):
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_content)
                ]
                response = self.llm.invoke(messages)
                parsed = json.loads(response.content)

                status = parsed["status"]
                action = parsed["action_required"]
                reasoning = parsed["reasoning"]

                return TriageResponseData(
                    status=status,
                    action_required=action,
                    confidence_score=0.95,
                    reasoning=reasoning,
                    timestamp=timestamp
                )
            except Exception as e:
                logger.warning(f"PreOpWaitlist LLM attempt {attempt + 1} failed: {e}")
                if attempt == 1:
                    logger.error("LLM failure cascade. Using PreOpWaitlist local fallback.")
                    return local_result

        return local_result

    def _evaluate_local(self, frame: TelemetryFrame, timestamp: str) -> TriageResponseData:
        """Local rule-based table and text parser fallback."""
        text = frame.input_string.strip()
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        if not lines:
            action = "Pre-Op Waiting List Assistant Active. Mature cataract clouding context detected. Converting blurred visual table matrices into sequential audio readouts hands-free."
            reasoning = "Empty document stream."
            return TriageResponseData(
                status="WAITLIST",
                action_required=action,
                confidence_score=0.60,
                reasoning=reasoning,
                timestamp=timestamp
            )

        # Detect csv/tsv/pipe tabular structures
        delimiter = None
        first_line = lines[0]
        if '|' in first_line:
            delimiter = '|'
        elif ',' in first_line and len(first_line.split(',')) > 1:
            delimiter = ','
        elif '\t' in first_line:
            delimiter = '\t'

        if delimiter:
            # Table-like structure detected
            headers = [h.strip() for h in first_line.split(delimiter) if h.strip()]
            col_count = len(headers)
            row_count = len(lines) - 1
            
            rows_desc = []
            for idx, line in enumerate(lines[1:], start=1):
                cells = [c.strip() for c in line.split(delimiter)]
                cell_pairs = []
                for c_idx, cell in enumerate(cells):
                    header_name = headers[c_idx] if c_idx < len(headers) else f"Column {c_idx + 1}"
                    cell_pairs.append(f"{header_name}: {cell}")
                rows_desc.append(f"Row {idx}: " + ", ".join(cell_pairs))

            action = (
                f"Warning: Office document contains a table with {col_count} columns: "
                f"{', '.join(headers)}. " + " ".join(rows_desc)
            )
            reasoning = f"Local rule-based delimiter '{delimiter}' parser matched tabular matrix."
        else:
            # Bullet/Text layout structure
            action = (
                f"Pre-Op Contrast Assistant: Document contains {len(lines)} structured lines. "
                f"First line reads: '{lines[0]}'. Description follows: " + "; ".join(lines[1:4])
            )
            reasoning = f"Local sequential line reader parsed {len(lines)} text elements."

        return TriageResponseData(
            status="WAITLIST",
            action_required=action,
            confidence_score=0.80,
            reasoning=reasoning,
            timestamp=timestamp
        )
