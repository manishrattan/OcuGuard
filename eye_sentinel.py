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
from typing import Dict, Any, List, Optional
from plugin_interface import OcuGuardSubAgentPlugin
from schemas import TelemetryFrame, StreamResponseData, PostOpRecoveryGuidance

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

logger = logging.getLogger("OcuGuard.EyeSentinel")

class LocalKeywordMatcher:
    """Zero-dependency local keyword matcher for eye emergency triage."""

    EMERGENCY_KEYWORDS = [
        "black curtain", "shadow", "darkness", "cannot see", "half blinded",
        "sudden", "sudden onset", "just happened", "flashing lights",
        "lightning flashes", "vision loss", "blacked out", "completely dark"
    ]
    
    URGENT_KEYWORDS = [
        "floaters", "sudden floaters", "increase in floaters", "blurry",
        "sudden blur", "light sensitivity", "eye pain", "severe pain", "sharp pain"
    ]
    
    ROUTINE_KEYWORDS = [
        "dryness", "dry eye", "itchiness", "itch", "watery", "redness", "discomfort"
    ]

    RISK_FACTORS = {
        "cataract_surgery": 1.2,
        "retinal_disease": 1.3,
        "diabetic_retinopathy": 1.25,
        "previous_detachment": 1.4,
        "age_over_50": 1.1
    }

    def evaluate(self, frame: TelemetryFrame, timestamp: str) -> StreamResponseData:
        """Evaluates telemetry frame locally using keyword rules.

        Args:
            frame: TelemetryFrame containing sensor and user data.
            timestamp: ISO 8601 timestamp string.

        Returns:
            StreamResponseData object.
        """
        input_lower = frame.input_string.lower()
        
        # Check explicit post-op recovery request first
        is_post_op = (
            "post_op_recovery" in frame.multimodal_flags or
            "post-op" in input_lower or
            "post op" in input_lower or
            "prone" in input_lower or
            "face down" in input_lower or
            "face-down" in input_lower
        )

        if is_post_op:
            return self._build_post_op_response(frame, timestamp)

        # Match keywords
        matched_emergencies = [kw for kw in self.EMERGENCY_KEYWORDS if kw in input_lower]
        matched_urgents = [kw for kw in self.URGENT_KEYWORDS if kw in input_lower]
        matched_routines = [kw for kw in self.ROUTINE_KEYWORDS if kw in input_lower]

        emergency_matched = len(matched_emergencies) > 0
        urgent_matched = len(matched_urgents) > 0
        routine_matched = len(matched_routines) > 0

        # Temporal override check: if the only emergency keyword matched is "sudden"
        # and we matched urgent symptoms, prioritize the URGENT classification
        if matched_emergencies == ["sudden"] and urgent_matched:
            emergency_matched = False

        # Check driving safety context
        is_driving = "driving_context" in frame.multimodal_flags or "driving" in input_lower or "drive" in input_lower

        if emergency_matched:
            status = "CRITICAL_ALERT"
            base_conf = 0.95
            action = "System Notification: Ingested telemetry strings match your pre-configured alert profile for acute discomfort. Please consult your supervisor, a professional mobility coach, or your personal emergency contact baseline instructions."
            reasoning = "Emergency-level keywords matched (e.g., shadow/curtain/onset/flashes) indicating significant sensory disruption."
            
            if is_driving:
                action = "System Notification: Driving detected with critical discomfort signal. Pull over to a safe location immediately and contact your support contact."
                
        elif urgent_matched:
            status = "ELEVATED_ALERT"
            base_conf = 0.70
            action = "System Notification: Elevated-level sensory pattern detected. Consider scheduling a professional assessment within 24-48 hours. Avoid strenuous activity."
            if is_driving:
                action = "System Notification: Elevated alert with driving detected. Pull over safely and seek appropriate support."
            reasoning = "Urgent-level symptoms detected (floaters, blur, discomfort)."
            
        elif routine_matched:
            status = "STANDARD_LOG"
            base_conf = 0.60
            action = "System Notification: Routine sensory pattern detected. Monitor condition. Apply standard mitigation if applicable. Escalate if condition worsens."
            reasoning = "Routine-level keywords matched (dryness, itching, minor discomfort)."
            
        else:
            # Ambiguous input - conservative bias triggers ELEVATED_ALERT
            status = "ELEVATED_ALERT"
            base_conf = 0.70
            action = "System Notification: Non-specific sensory pattern reported. Please consult with a professional to establish baseline parameters."
            reasoning = "Ambiguous input parsed. Conservative stream urgency routing applied."

        # Apply risk factor multipliers
        adjusted_conf = base_conf
        for factor, multiplier in self.RISK_FACTORS.items():
            if getattr(frame.history, factor, False):
                adjusted_conf *= multiplier
                
        adjusted_conf = min(1.0, adjusted_conf)

        return StreamResponseData(
            status=status,
            action_required=action,
            confidence_score=round(adjusted_conf, 4),
            reasoning=reasoning,
            timestamp=timestamp,
            escalation_trigger="Human Escalation Protocol" if status == "CRITICAL_ALERT" else None
        )

    def _build_post_op_response(self, frame: TelemetryFrame, timestamp: str) -> StreamResponseData:
        """Helper to build post-operative recovery guidance response."""
        # Parse timestamp hour to determine rotation schedule
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            hour = dt.hour
        except Exception:
            hour = datetime.now(timezone.utc).hour

        # Rotate positions every hour: prone, left side, right side.
        position_idx = hour % 3
        if position_idx == 0:
            recommended_side = "Prone (Face-Down)"
            positioning_instruction = "Lie completely flat on your stomach with face pointing down. Use the Triple Pillow layout."
        elif position_idx == 1:
            recommended_side = "Left Side"
            positioning_instruction = "Turn onto your left side. Place a pillow between your knees and maintain horizontal neck alignment."
        else:
            recommended_side = "Right Side"
            positioning_instruction = "Turn onto your right side. Place a pillow between your knees and maintain horizontal neck alignment."

        guidance = PostOpRecoveryGuidance(
            triple_pillow_triangle=True,
            airway_clearance="Implement Triple Pillow Triangle layout to support chest alignment and breathing.",
            positioning_instruction=positioning_instruction,
            recommended_side=recommended_side,
            timestamp=timestamp
        )

        return StreamResponseData(
            status="ADAPTIVE_GUIDANCE",
            action_required="Geometric Positioning Guide: Follow current bubble positioning rules. Ensure airway is clear. Rotate to next position at next hour boundary.",
            confidence_score=0.95,
            reasoning="Post-operative recovery context recognized. Geometric positioning schedule activated.",
            timestamp=timestamp,
            post_op_recovery_guidance=guidance
        )


class EyeSentinelAgent(OcuGuardSubAgentPlugin):
    """Adaptive Geometric Orientation Assistant with posture and acoustic feedback analysis.

    Extends the plugin interface and integrates LLM evaluation with
    a zero-dependency local keyword matcher fallback loop.
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        """Initializes the EyeSentinelAgent."""
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.local_matcher = LocalKeywordMatcher()
        
        # Setup LangChain LLM if credentials exist
        self.llm = None
        if LANGCHAIN_AVAILABLE and self.openai_api_key:
            try:
                self.llm = ChatOpenAI(
                    model="gpt-4",
                    openai_api_key=self.openai_api_key,
                    temperature=0.0,
                    request_timeout=2.0,  # Strict timeout limit
                    max_retries=1         # 1 retry internally (total 2 attempts)
                )
            except Exception as e:
                logger.error(f"Failed to initialize ChatOpenAI: {e}. Fallback active.")

    @property
    def condition_id(self) -> str:
        """Returns the unique condition tracking ID."""
        return "ADAPTIVE_GEOMETRIC_ORIENTATION_ANALYSIS"

    def validate_safety_envelope(self, telemetry_frame: Dict[str, Any]) -> Dict[str, Any]:
        """Plugin Interface implementation. Evaluates telemetry framework.

        Args:
            telemetry_frame: Dict payload matching TelemetryFrame schema.

        Returns:
            Dictionary matching the standard API response contract.
        """
        # Convert dictionary to TelemetryFrame object
        try:
            frame = TelemetryFrame(**telemetry_frame)
        except Exception as e:
            logger.error(f"Validation failed for telemetry frame object: {e}")
            raise ValueError(f"Invalid telemetry format: {e}")

        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Evaluate
        response_data = self.evaluate_triage(frame, timestamp)
        return response_data.model_dump()

    def evaluate_triage(self, frame: TelemetryFrame, timestamp: str) -> StreamResponseData:
        """Performs adaptive orientation checks using LLM, with fallback.

        Args:
            frame: Redacted TelemetryFrame payload.
            timestamp: UTC timestamp.

        Returns:
            StreamResponseData.
        """
        # Pitch warning check for geometric constraints
        if frame.pitch > -55.0 and ("post_op_recovery" in frame.multimodal_flags or "prone" in frame.input_string.lower()):
            # Head pitch violation during posture constraint!
            response = self.local_matcher.evaluate(frame, timestamp)
            response.status = "CRITICAL_ALERT"
            response.action_required = "System Alert: Current head orientation exceeds geometric constraint (-55.0°). Adjust posture to comply with positioning parameters."
            response.reasoning = f"Head pitch angle of {frame.pitch}° exceeds orientation safety threshold (-55.0°)."
            return response

        # If LLM is unavailable, route directly to local keyword matcher
        if not self.llm:
            logger.info("LangChain/OpenAI unconfigured or failed init. Running LocalKeywordMatcher.")
            return self.local_matcher.evaluate(frame, timestamp)

        # Build prompt messages
        system_prompt = (
            "You are an Adaptive Geometric Orientation Assistant. You must classify sensory stream data into: "
            "CRITICAL_ALERT, ELEVATED_ALERT, STANDARD_LOG, INFORMATION, or ADAPTIVE_GUIDANCE based on stream urgency level.\n\n"
            "Classification Rules:\n"
            "- CRITICAL_ALERT: High-intensity sensory disruption keywords (darkness, shadow, sudden vision change, flashing, sharp discomfort).\n"
            "- ELEVATED_ALERT: Moderate sensory disturbance (floaters, blur, generalized discomfort, light sensitivity).\n"
            "- STANDARD_LOG: Routine sensory patterns (dryness, itching, mild irritation).\n"
            "- ADAPTIVE_GUIDANCE: User indicates specific postural or positioning guidance requests.\n\n"
            "Output strictly in JSON format matching this schema:\n"
            "{\n"
            "  \"status\": \"CRITICAL_ALERT|ELEVATED_ALERT|STANDARD_LOG|ADAPTIVE_GUIDANCE\",\n"
            "  \"action_required\": \"Actionable system guidance\",\n"
            "  \"confidence_score\": 0.0-1.0,\n"
            "  \"reasoning\": \"Brief explanation\"\n"
            "}"
        )

        user_content = f"Input text: '{frame.input_string}'. Multimodal flags: {frame.multimodal_flags}. History: {frame.history.model_dump()}"

        # Attempt LLM call with retry cascade
        for attempt in range(2):
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_content)
                ]
                response = self.llm.invoke(messages)
                parsed = json.loads(response.content)
                
                # Enforce structure
                status = parsed["status"]
                action = parsed["action_required"]
                base_conf = float(parsed.get("confidence_score", 0.90))
                reasoning = parsed["reasoning"]

                # Apply post-op formatting if LLM routed to ADAPTIVE_GUIDANCE
                if status == "ADAPTIVE_GUIDANCE" or "post-op" in frame.input_string.lower():
                    return self.local_matcher._build_post_op_response(frame, timestamp)

                # Ensure safety warnings are in action_required
                if "driving_context" in frame.multimodal_flags and status in ["CRITICAL_ALERT", "ELEVATED_ALERT"]:
                    action = "System Alert: Critical stream urgency detected while driving. Pull over to a safe location immediately." if status == "CRITICAL_ALERT" else "System Alert: Elevated stream urgency detected. Pull over safely to reassess."

                # Apply risk factor multipliers to LLM confidence score
                adjusted_conf = base_conf
                for factor, multiplier in self.local_matcher.RISK_FACTORS.items():
                    if getattr(frame.history, factor, False):
                        adjusted_conf *= multiplier
                adjusted_conf = min(1.0, adjusted_conf)

                return StreamResponseData(
                    status=status,
                    action_required=action,
                    confidence_score=round(adjusted_conf, 4),
                    reasoning=reasoning,
                    timestamp=timestamp,
                    escalation_trigger="Human Escalation Protocol" if status == "CRITICAL_ALERT" else None
                )

            except Exception as e:
                logger.warning(f"LLM attempt {attempt + 1} failed: {e}")
                if attempt == 1:
                    # Final failure -> route to local matcher fallback
                    logger.error("LLM cascade exhausted. Running local matcher fallback.")
                    return self.local_matcher.evaluate(frame, timestamp)
        
        # Final fallback backup
        return self.local_matcher.evaluate(frame, timestamp)
