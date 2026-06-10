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
from schemas import TelemetryFrame, StreamResponseData

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

logger = logging.getLogger("OcuGuard.BeMyEyes")

class BeMyEyesAgent(OcuGuardSubAgentPlugin):
    """Acoustic Layout Optimizer & Human-in-the-Loop Escalation Proxy.

    Continuously monitors system confidence and user input streams.
    Initiates escalation protocol if confidence falls below 82% or if user indicates
    need for human assistance.
    """

    PANIC_KEYWORDS = [
        "confused", "lost", "help", "person", "human", 
        "operator", "don't know", "cannot read", "need help", "connect me"
    ]

    def __init__(self, openai_api_key: Optional[str] = None):
        """Initializes the BeMyEyesAgent."""
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
        return "ACOUSTIC_LAYOUT_ESCALATION_GATEWAY"

    def validate_safety_envelope(self, telemetry_frame: Dict[str, Any]) -> Dict[str, Any]:
        """Validates critical confidence threshold and user intent.

        Args:
            telemetry_frame: Dict matching TelemetryFrame.

        Returns:
            Dict containing escalation parameters.
        """
        try:
            frame = TelemetryFrame(**telemetry_frame)
        except Exception as e:
            logger.error(f"Validation failed for Acoustic Layout Optimizer: {e}")
            raise ValueError(f"Invalid telemetry format: {e}")

        timestamp = datetime.now(timezone.utc).isoformat()
        response = self.evaluate_safety(frame, timestamp)
        return response.model_dump()

    def evaluate_safety(self, frame: TelemetryFrame, timestamp: str) -> StreamResponseData:
        """Analyzes system confidence and user input for escalation.

        Args:
            frame: TelemetryFrame dataset.
            timestamp: ISO 8601 timestamp.

        Returns:
            StreamResponseData.
        """
        local_result = self._evaluate_local(frame, timestamp)

        if not self.llm:
            return local_result

        system_prompt = (
            "You are the Acoustic Layout Optimizer and Escalation Protocol Engine. "
            "You monitor audio/text input streams for safety-critical user needs.\n"
            "Decision Rules:\n"
            "- If confidence score is below 82% OR user input contains escalation keywords "
            "(confused, lost, help, person, human, operator, etc.): respond with ESCALATION status.\n"
            "- Otherwise, return status SAFE.\n\n"
            "Format the output strictly as a JSON payload:\n"
            "{\n"
            "  \"status\": \"ESCALATION|SAFE\",\n"
            "  \"action_required\": \"Guidance or escalation notification\",\n"
            "  \"confidence_score\": 0.0-1.0,\n"
            "  \"reasoning\": \"Explanation for decision\"\n"
            "}"
        )

        user_content = f"Confidence: {frame.confidence}%. User Input: '{frame.input_string}'"

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

                return StreamResponseData(
                    status=status,
                    action_required=action,
                    confidence_score=frame.confidence / 100.0,
                    reasoning=reasoning,
                    timestamp=timestamp,
                    escalation_trigger="Human Escalation Protocol" if status == "ESCALATION" else None
                )
            except Exception as e:
                logger.warning(f"BeMyEyes LLM attempt {attempt + 1} failed: {e}")
                if attempt == 1:
                    logger.error("LLM failure cascade. Using BeMyEyes local fallback.")
                    return local_result

        return local_result

    def _evaluate_local(self, frame: TelemetryFrame, timestamp: str) -> StreamResponseData:
        """Local threshold and keyword matcher fallback."""
        input_lower = frame.input_string.lower()
        has_escalation_kw = any(kw in input_lower for kw in self.PANIC_KEYWORDS)
        low_confidence = frame.confidence < 82.0

        if low_confidence or has_escalation_kw:
            status = "ESCALATION"
            action = "System Notice: Confidence threshold or user escalation request detected. Initiating human operator connection protocol."
            reasoning = f"Escalation triggered. Low confidence: {low_confidence} (Score: {frame.confidence}%). Escalation keywords: {has_escalation_kw}."
            trigger = "Human Escalation Protocol"
        else:
            status = "SAFE"
            action = "System Status: Confidence within safe parameters. Monitoring for user support requests."
            reasoning = f"Confidence {frame.confidence}% is within acceptable bounds and no escalation keywords detected."
            trigger = None

        return StreamResponseData(
            status=status,
            action_required=action,
            confidence_score=round(frame.confidence / 100.0, 4),
            reasoning=reasoning,
            timestamp=timestamp,
            escalation_trigger=trigger
        )
