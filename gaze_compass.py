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
import math
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

logger = logging.getLogger("OcuGuard.GazeCompass")

class GazeCompassAgent(OcuGuardSubAgentPlugin):
    """Assistive Low-Vision Alignment Specialist.

    Monitors patients navigating central scotomas, calculating 3D panning
    localization offsets to help shift objects onto the Preferred Retinal Locus (PRL).
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        """Initializes the GazeCompassAgent."""
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
        return "GAZE_COMPASS_PRL_TRACKING"

    def validate_safety_envelope(self, telemetry_frame: Dict[str, Any]) -> Dict[str, Any]:
        """Validates telemetry coordinate fields.

        Args:
            telemetry_frame: Dict input frame matching TelemetryFrame.

        Returns:
            Standard Dict response.
        """
        try:
            frame = TelemetryFrame(**telemetry_frame)
        except Exception as e:
            logger.error(f"Validation failed for Gaze Compass: {e}")
            raise ValueError(f"Invalid telemetry format: {e}")

        timestamp = datetime.now(timezone.utc).isoformat()
        response = self.evaluate_alignment(frame, timestamp)
        return response.model_dump()

    def evaluate_alignment(self, frame: TelemetryFrame, timestamp: str) -> StreamResponseData:
        """Evaluates whether objects are obscured by central scotoma.

        If obscured, outputs panning coordinates to slide visual focus.

        Args:
            frame: TelemetryFrame dataset.
            timestamp: ISO 8601 timestamp.

        Returns:
            StreamResponseData.
        """
        # Execute fast local mathematical loop
        local_result = self._evaluate_local(frame, timestamp)

        if not self.llm:
            return local_result

        # Build prompt for LLM evaluation
        system_prompt = (
            "You are the Gaze-Compass AI Agent. You evaluate spatial eye telemetry for patients with central scotomas.\n"
            "Given:\n"
            "- Target object: (target_x, target_y)\n"
            "- Central scotoma: (blind_x, blind_y) with radius blind_r\n"
            "- Gaze coordinates: (gaze_x, gaze_y)\n\n"
            "Assess whether the target is obscured (within radius blind_r of the scotoma center).\n"
            "Calculate a horizontal pan localization offset (-1.0 to 1.0) to slide the object out of the blind spot.\n"
            "Output strictly in JSON:\n"
            "{\n"
            "  \"status\": \"SAFE|VIOLATION\",\n"
            "  \"action_required\": \"TTS audio prompt guiding the user's vision shift\",\n"
            "  \"pan_localization\": -1.0 to 1.0,\n"
            "  \"confidence_score\": 0.0-1.0,\n"
            "  \"reasoning\": \"Brief explanation of target relative to scotoma\"\n"
            "}"
        )

        user_content = (
            f"Target: ({frame.target_x}, {frame.target_y}), "
            f"Blind spot: ({frame.blind_x}, {frame.blind_y}), radius: {frame.blind_r}, "
            f"Gaze: ({frame.gaze_x}, {frame.gaze_y})"
        )

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
                pan_val = float(parsed.get("pan_localization", local_result.pan_localization))
                reasoning = parsed["reasoning"]

                return StreamResponseData(
                    status=status,
                    action_required=action,
                    confidence_score=0.95,
                    reasoning=reasoning,
                    timestamp=timestamp,
                    pan_localization=round(max(-1.0, min(1.0, pan_val)), 4)
                )
            except Exception as e:
                logger.warning(f"GazeCompass LLM attempt {attempt + 1} failed: {e}")
                if attempt == 1:
                    logger.error("LLM failure cascade. Using GazeCompass local fallback.")
                    return local_result

        return local_result

    def _evaluate_local(self, frame: TelemetryFrame, timestamp: str) -> StreamResponseData:
        """Local mathematical routing fallback for Gaze Compass."""
        dx = frame.target_x - frame.blind_x
        dy = frame.target_y - frame.blind_y
        dist = math.hypot(dx, dy)
        
        # Calculate horizontal panning direction away from center (-1.0 to 1.0)
        # Scale by 1.5 to provide sufficient response velocity
        pan_val = max(-1.0, min(1.0, dx * 1.5))

        if dist <= frame.blind_r:
            status = "VIOLATION"
            direction = "right" if pan_val >= 0 else "left"
            action = f"Objective obscured within the central scotoma zone. Shift vision {direction} to center the peripheral target."
            reasoning = f"Target distance {dist:.2f} is inside scotoma boundary {frame.blind_r:.2f}."
        elif dist <= frame.blind_r * 1.25:
            status = "SAFE"
            action = "Target locked within usable functional peripheral vision locus."
            reasoning = f"Target distance {dist:.2f} is settled within the Preferred Retinal Locus buffer."
        else:
            status = "SAFE"
            action = "Target remains in clear peripheral alignment."
            reasoning = f"Target distance {dist:.2f} is well outside scotoma zone."

        return StreamResponseData(
            status=status,
            action_required=action,
            confidence_score=0.90,
            reasoning=reasoning,
            timestamp=timestamp,
            pan_localization=round(pan_val, 4)
        )
