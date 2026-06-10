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
import time
import logging
from datetime import datetime, timezone
from functools import wraps
from typing import List, Dict, Any

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from pydantic import ValidationError

from schemas import TelemetryFrame, AdaptivePayloadResponse, StreamResponseData
from supervisor import SupervisorAgent
from eye_sentinel import EyeSentinelAgent
from gaze_compass import GazeCompassAgent
from tabular_layout_speech import TabularLayoutSpeechAgent
from ergonomic_schedule import ErgonomicScheduleAgent
from ambient_luminance import AmbientLuminanceAgent
from be_my_eyes import BeMyEyesAgent

# Load environment variables
load_dotenv()

# Configure Logging (Ensure no PII leaks in default formatters)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("OcuGuard.Gateway")

app = Flask(__name__)

# Initialize OcuGuard Agents
supervisor = SupervisorAgent()
eye_sentinel = EyeSentinelAgent()
gaze_compass = GazeCompassAgent()
tabular_layout_speech = TabularLayoutSpeechAgent()
ergonomic_schedule = ErgonomicScheduleAgent()
ambient_luminance = AmbientLuminanceAgent()
be_my_eyes = BeMyEyesAgent()

# Global Statistics (For /v1/system/stats)
stats_db = {
    "total_stream_evaluations": 0,
    "cloud_routing_count": 0,
    "local_routing_count": 0,
    "status_counts": {
        "CRITICAL_ALERT": 0,
        "ELEVATED_ALERT": 0,
        "STANDARD_LOG": 0,
        "SAFE": 0,
        "VIOLATION": 0,
        "ESCALATION": 0,
        "SCHEDULED_HABIT": 0,
        "ENVIRONMENTAL_OPTIMIZATION": 0,
        "INFORMATION": 0
    },
    "errors": 0
}

# In-Memory Rate Limiting: user_id -> list of float timestamps
rate_limits: Dict[str, List[float]] = {}

def rate_limit_required(f):
    """Decorator to enforce 60 requests/minute per user_id."""
    @wraps(f)
    def decorated(*args, **kwargs):
        req_json = request.get_json(silent=True) or {}
        user_id = req_json.get("user_id", request.remote_addr)
        
        now = time.time()
        # Clean up timestamps older than 60 seconds
        user_history = rate_limits.get(user_id, [])
        user_history = [t for t in user_history if now - t < 60.0]
        
        if len(user_history) >= 60:
            logger.warning(f"Rate limit exceeded for user: {user_id}")
            return jsonify({
                "error": "Too Many Requests",
                "message": "Rate limit of 60 requests per minute exceeded."
            }), 429
            
        user_history.append(now)
        rate_limits[user_id] = user_history
        return f(*args, **kwargs)
    return decorated

def api_key_required(f):
    """Decorator to enforce optional API Key protection."""
    @wraps(f)
    def decorated(*args, **kwargs):
        expected_key = os.getenv("API_KEY")
        if expected_key:
            provided_key = request.headers.get("X-API-Key")
            if not provided_key or provided_key != expected_key:
                logger.warning("Unauthorized access attempt to protected endpoint.")
                return jsonify({"error": "Unauthorized", "message": "Invalid API Key"}), 401
        return f(*args, **kwargs)
    return decorated

def process_single_frame(frame_data: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to route, redact, and evaluate a single telemetry frame."""
    stats_db["total_stream_evaluations"] += 1
    
    # 1. Parse and Validate Telemetry schema
    frame = TelemetryFrame(**frame_data)
    
    # 2. Ingest through Supervisor (PII removal & security token validation)
    is_valid, route_mode, redacted_frame = supervisor.validate_and_route(frame)
    
    # Log metadata metrics securely (Scrubbed parameters)
    logger.info(
        f"Processing evaluation request: user_id_length={len(redacted_frame.user_id)} "
        f"route_mode={route_mode} client_id={redacted_frame.client_id}"
    )

    if route_mode == "LOCAL_FALLBACK":
        stats_db["local_routing_count"] += 1
    else:
        stats_db["cloud_routing_count"] += 1

    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Determine the targeted sub-agent plugin
    agent_mode = frame_data.get("agent_mode", "EYE_SENTINEL")
    
    # Execute routing matching dashboard engine parameters
    if agent_mode == "EYE_SENTINEL":
        # Eye-Sentinel orientation & acoustic feedback analyzer
        if route_mode == "LOCAL_FALLBACK":
            response_data = eye_sentinel.local_matcher.evaluate(redacted_frame, timestamp)
        else:
            response_data = eye_sentinel.evaluate_triage(redacted_frame, timestamp)
            
    elif agent_mode == "OCUGUARD_CORE":
        # Kinematics / posture alignment parameter enforcer
        status = "SAFE"
        action = "All anterior segment vector paths reporting stable alignment indices."
        if redacted_frame.pitch < -45.0:
            status = "VIOLATION"
            action = "Warning: Avoid forward bending past waist boundaries. Drop your height via a vertical squat."
        elif redacted_frame.pitch < -30.0:
            status = "VIOLATION"
            action = "Alert: Postural compromise detected. Avoid lying back or horizontal recline slopes."
            
        response_data = StreamResponseData(
            status=status,
            action_required=action,
            confidence_score=0.95,
            reasoning=f"Anterior check processed for pitch {redacted_frame.pitch}°.",
            timestamp=timestamp
        )
        
    elif agent_mode == "GAZE_COMPASS":
        # Low Vision PRL Alignment assistant
        if route_mode == "LOCAL_FALLBACK":
            response_data = gaze_compass._evaluate_local(redacted_frame, timestamp)
        else:
            response_data = gaze_compass.evaluate_alignment(redacted_frame, timestamp)
            
    elif agent_mode == "TABULAR_LAYOUT_SPEECH":
        # OCR Matrix Optimization for workplace productivity
        if route_mode == "LOCAL_FALLBACK":
            response_data = tabular_layout_speech._evaluate_local(redacted_frame, timestamp)
        else:
            response_data = tabular_layout_speech.evaluate_contrast(redacted_frame, timestamp)
    
    elif agent_mode == "ERGONOMIC_SCHEDULE":
        # Postural habit tracking and wellness routine monitoring
        response_data = ergonomic_schedule.evaluate_posture(redacted_frame, timestamp)
    
    elif agent_mode == "AMBIENT_LUMINANCE":
        # Environmental light & contrast optimization assistant
        response_data = ambient_luminance.evaluate_environment(redacted_frame, timestamp)
            
    elif agent_mode == "BE_MY_EYES":
        # Acoustic Layout Optimizer & escalation proxy
        if route_mode == "LOCAL_FALLBACK":
            response_data = be_my_eyes._evaluate_local(redacted_frame, timestamp)
        else:
            response_data = be_my_eyes.evaluate_safety(redacted_frame, timestamp)
            
    else:
        # Unknown agent - default to EYE_SENTINEL
        response_data = eye_sentinel.evaluate_triage(redacted_frame, timestamp)

    # Track status statistics safely
    status = response_data.status
    if status in stats_db["status_counts"]:
        stats_db["status_counts"][status] += 1
        
    return response_data.model_dump()


# REST ENDPOINTS

@app.route("/health", methods=["GET"])
def health_check():
    """Health check for service monitoring."""
    return jsonify({"status": "healthy"}), 200

@app.route("/v1/stream/info", methods=["GET"])
def get_info():
    """Returns general service documentation and supported agents."""
    return jsonify({
        "service": "OcuGuard Adaptive Stream Evaluation Engine",
        "version": "2.0.0",
        "supported_agents": [
            "EYE_SENTINEL",
            "OCUGUARD_CORE",
            "GAZE_COMPASS",
            "TABULAR_LAYOUT_SPEECH",
            "ERGONOMIC_SCHEDULE",
            "AMBIENT_LUMINANCE",
            "BE_MY_EYES"
        ],
        "emergency_keywords": eye_sentinel.local_matcher.EMERGENCY_KEYWORDS,
        "urgent_keywords": eye_sentinel.local_matcher.URGENT_KEYWORDS,
        "routine_keywords": eye_sentinel.local_matcher.ROUTINE_KEYWORDS
    }), 200

@app.route("/v1/system/config", methods=["GET"])
@api_key_required
def get_system_config():
    """Protected endpoint to retrieve active model parameters."""
    return jsonify({
        "environment": "Production",
        "openai_integration": eye_sentinel.llm is not None,
        "rate_limiting_cap": 60,
        "fallback_override": "ACTIVE_LOCAL_OVERRIDE_ENABLED",
        "compliance_index": "Assisted Living Assistive Cognitive Middleware"
    }), 200

@app.route("/v1/system/stats", methods=["GET"])
@api_key_required
def get_system_stats():
    """Protected endpoint exposing processed log aggregates."""
    return jsonify(stats_db), 200

@app.route("/v1/stream/evaluate", methods=["POST"])
@rate_limit_required
def evaluate_stream():
    """Performs single telemetry frame routing and evaluation."""
    payload = request.get_json(silent=True)
    if not payload:
        stats_db["errors"] += 1
        return jsonify({"error": "Bad Request", "message": "Missing JSON request body"}), 400
        
    try:
        data = process_single_frame(payload)
        response = AdaptivePayloadResponse(
            message="Stream evaluation completed",
            data=StreamResponseData(**data),
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        return jsonify(response.model_dump()), 200
        
    except ValidationError as ve:
        stats_db["errors"] += 1
        logger.error(f"Input validation error: {ve}")
        return jsonify({"error": "Unprocessable Entity", "message": ve.errors()}), 422
        
    except Exception as e:
        stats_db["errors"] += 1
        logger.error(f"Internal routing error occurred: {e}", exc_info=True)
        return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred"}), 500

@app.route("/v1/stream/evaluate/batch", methods=["POST"])
@rate_limit_required
def evaluate_stream_batch():
    """Performs batch evaluations up to a maximum of 10 requests."""
    payload = request.get_json(silent=True) or {}
    requests_list = payload.get("requests")
    
    if not requests_list or not isinstance(requests_list, list):
        stats_db["errors"] += 1
        return jsonify({"error": "Bad Request", "message": "Missing 'requests' array parameter"}), 400
        
    if len(requests_list) > 10:
        stats_db["errors"] += 1
        return jsonify({"error": "Unprocessable Entity", "message": "Max batch size is 10 requests"}), 422

    results = []
    for idx, req in enumerate(requests_list):
        try:
            res_data = process_single_frame(req)
            results.append({
                "index": idx,
                "status": "success",
                "data": res_data
            })
        except ValidationError as ve:
            stats_db["errors"] += 1
            results.append({
                "index": idx,
                "status": "validation_error",
                "message": ve.errors()
            })
        except Exception as e:
            stats_db["errors"] += 1
            results.append({
                "index": idx,
                "status": "error",
                "message": str(e)
            })

    return jsonify({
        "message": "Batch triage analysis completed",
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
