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

logger = logging.getLogger("OcuGuard.TabularLayoutSpeech")

class TabularLayoutSpeechAgent(OcuGuardSubAgentPlugin):
    """OCR Matrix Optimization and Visual-to-Acoustic Layout Enhancer.

    Supports users navigating low-contrast document structures for workplace
    productivity during visual adaptation challenges. Converts tabular and 
    textual layouts into accessible acoustic descriptions.
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        """Initializes the TabularLayoutSpeechAgent."""
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
        return "OCR_MATRIX_OPTIMIZATION_SPEECH"

    def validate_safety_envelope(self, telemetry_frame: Dict[str, Any]) -> Dict[str, Any]:
        """Validates document and layout telemetry.

        Args:
            telemetry_frame: Dict matching TelemetryFrame.

        Returns:
            Dict containing parsed structural audio description.
        """
        try:
            frame = TelemetryFrame(**telemetry_frame)
        except Exception as e:
            logger.error(f"Validation failed for Tabular Layout Speech: {e}")
            raise ValueError(f"Invalid telemetry format: {e}")

        timestamp = datetime.now(timezone.utc).isoformat()
        response = self.evaluate_contrast(frame, timestamp)
        return response.model_dump()

    def evaluate_contrast(self, frame: TelemetryFrame, timestamp: str) -> StreamResponseData:
        """Converts text streams into sequential audio outlines.

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
            "You are the OCR Matrix Optimization and Visual-to-Acoustic Layout Assistant. "
            "Your role is to assist users navigating text and tabular structures for workplace productivity.\n"
            "Analyze the provided document OCR text stream and convert it into a structured, accessible, "
            "hands-free verbal description suitable for workplace environments.\n"
            "Format the output strictly as a JSON payload:\n"
            "{\n"
            "  \"status\": \"SCHEDULED_HABIT\",\n"
            "  \"action_required\": \"Verbal layout structure and navigation guide\",\n"
            "  \"confidence_score\": 0.0-1.0,\n"
            "  \"reasoning\": \"Brief document classification and structure summary\"\n"
            "}"
        )

        user_content = f"Document Text Stream:\n{frame.input_string}"

        for attempt in range(2):
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_content)
                ]
                response = self.llm.invoke(messages)
                parsed = json.loads(response.content)

                status = parsed.get("status", "SCHEDULED_HABIT")
                action = parsed["action_required"]
                reasoning = parsed["reasoning"]

                return StreamResponseData(
                    status=status,
                    action_required=action,
                    confidence_score=0.95,
                    reasoning=reasoning,
                    timestamp=timestamp
                )
            except Exception as e:
                logger.warning(f"TabularLayoutSpeech LLM attempt {attempt + 1} failed: {e}")
                if attempt == 1:
                    logger.error("LLM failure cascade. Using TabularLayoutSpeech local fallback.")
                    return local_result

        return local_result

    def _evaluate_local(self, frame: TelemetryFrame, timestamp: str) -> StreamResponseData:
        """Fallback local evaluation without LLM."""
        status = "SCHEDULED_HABIT"
        
        # Simple heuristics for document structure
        has_tables = "|" in frame.input_string or "---" in frame.input_string or "columns" in frame.input_string.lower()
        has_lists = any(line.strip().startswith("-") or line.strip().startswith("•") for line in frame.input_string.split("\n"))
        
        if has_tables:
            action = "Tabular Structure Detected: Document contains a table layout. Structure: Rows and columns. Navigate systematically from top-left to bottom-right."
            reasoning = "Table markers detected in OCR stream (pipes or dashes)."
        elif has_lists:
            action = "List Structure Detected: Document contains itemized content. Structure: Sequential items. Process entries in order."
            reasoning = "Bullet or dash markers detected in OCR stream."
        else:
            action = "Paragraph Structure Detected: Document contains flowing text. Structure: Sequential paragraphs. Process line by line."
            reasoning = "Paragraph formatting detected in OCR stream."

        return StreamResponseData(
            status=status,
            action_required=action,
            confidence_score=0.75,
            reasoning=reasoning,
            timestamp=timestamp
        )
