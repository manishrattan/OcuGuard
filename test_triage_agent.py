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
import pytest
from datetime import datetime
from unittest.mock import MagicMock

# Set test environment variables
os.environ["API_KEY"] = "TEST_SECRET_KEY"
os.environ["OPENAI_API_KEY"] = "mock-openai-key"

from app import app, rate_limits, stats_db
from schemas import TelemetryFrame, HistoryInfo
from supervisor import SupervisorAgent
from eye_sentinel import EyeSentinelAgent
from gaze_compass import GazeCompassAgent
from preop_waitlist import PreOpWaitlistAgent
from be_my_eyes import BeMyEyesAgent

# ----------------- FIXTURES -----------------

@pytest.fixture
def client():
    app.config["TESTING"] = True
    rate_limits.clear()
    stats_db["total_requests"] = 0
    stats_db["cloud_routing_count"] = 0
    stats_db["local_routing_count"] = 0
    for key in stats_db["status_counts"]:
        stats_db["status_counts"][key] = 0
    yield app.test_client()

# Mock langchain response class
class MockLLMResponse:
    def __init__(self, content: str):
        self.content = content

# ----------------- SUPERVISOR TESTS -----------------

def test_supervisor_redact_email():
    agent = SupervisorAgent()
    text = "Please write to patient john.doe@example.com for follow-up."
    redacted = agent.redact_pii(text)
    assert "[REDACTED_EMAIL]" in redacted
    assert "john.doe@example.com" not in redacted

def test_supervisor_redact_phone():
    agent = SupervisorAgent()
    text = "Call me at +1-123-456-7890 tomorrow."
    redacted = agent.redact_pii(text)
    assert "[REDACTED_PHONE]" in redacted
    assert "123-456-7890" not in redacted

def test_supervisor_redact_ssn():
    agent = SupervisorAgent()
    text = "Primary client ID is SSN 000-12-3456."
    redacted = agent.redact_pii(text)
    assert "[REDACTED_SSN]" in redacted
    assert "000-12-3456" not in redacted

def test_supervisor_valid_token():
    agent = SupervisorAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="No symptoms",
        client_id="OCUGUARD_CLIENT",
        user_token="OCUGUARD_TOKEN"
    )
    is_valid, route, redacted = agent.validate_and_route(frame)
    assert is_valid is True
    assert route == "CLOUD_HYBRID"
    assert redacted.input_string == "No symptoms"

def test_supervisor_invalid_token():
    agent = SupervisorAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="No symptoms",
        client_id="BAD_CLIENT",
        user_token="OCUGUARD_TOKEN"
    )
    is_valid, route, _ = agent.validate_and_route(frame)
    assert is_valid is False
    assert route == "LOCAL_FALLBACK"

def test_supervisor_network_drop():
    agent = SupervisorAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="No symptoms",
        multimodal_flags=["network_drop"],
        client_id="OCUGUARD_CLIENT",
        user_token="OCUGUARD_TOKEN"
    )
    is_valid, route, _ = agent.validate_and_route(frame)
    assert is_valid is False
    assert route == "LOCAL_FALLBACK"


# ----------------- EYE SENTINEL TESTS -----------------

def test_eye_sentinel_emergency_keyword_post_cataract():
    agent = EyeSentinelAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="I suddenly see a dark shadow or black curtain covering my eye.",
        history=HistoryInfo(cataract_surgery=True)
    )
    res = agent.local_matcher.evaluate(frame, "2026-05-15T12:00:00Z")
    assert res.status == "EMERGENCY"
    assert res.confidence_score >= 0.90
    assert "ER" in res.action_required

def test_eye_sentinel_emergency_keyword_no_history():
    agent = EyeSentinelAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="I suddenly see a black curtain",
        history=HistoryInfo(cataract_surgery=False)
    )
    res = agent.local_matcher.evaluate(frame, "2026-05-15T12:00:00Z")
    assert res.status == "EMERGENCY"
    assert res.confidence_score >= 0.85

def test_eye_sentinel_urgent_keyword():
    agent = EyeSentinelAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="There is a sudden increase in floaters and blurry vision.",
    )
    res = agent.local_matcher.evaluate(frame, "2026-05-15T12:00:00Z")
    assert res.status == "URGENT"
    assert res.confidence_score == 0.70

def test_eye_sentinel_routine_keyword():
    agent = EyeSentinelAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="My eyes feel some dryness and redness",
    )
    res = agent.local_matcher.evaluate(frame, "2026-05-15T12:00:00Z")
    assert res.status == "ROUTINE"
    assert res.confidence_score == 0.60

def test_eye_sentinel_ambiguous_input():
    agent = EyeSentinelAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="It feels a bit strange today",
    )
    res = agent.local_matcher.evaluate(frame, "2026-05-15T12:00:00Z")
    # Ambiguous input - conservative safety bias
    assert res.status == "URGENT"
    assert res.confidence_score == 0.70

def test_eye_sentinel_pitch_violation():
    agent = EyeSentinelAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="Recovery",
        pitch=-10.0, # Violation: Should be past -55.0° (i.e. -60° etc.)
        multimodal_flags=["post_op_recovery"]
    )
    res = agent.evaluate_triage(frame, "2026-05-15T12:00:00Z")
    assert res.status == "VIOLATION"
    assert "POSTURE VIOLATION" in res.action_required

def test_eye_sentinel_post_op_recovery_even_hour():
    agent = EyeSentinelAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="Recovering after surgery",
        pitch=-60.0,
        multimodal_flags=["post_op_recovery"]
    )
    # 12:00 is even hour -> Prone recommendation
    res = agent.evaluate_triage(frame, "2026-05-15T12:00:00Z")
    assert res.status == "POST_OP_RECOVERY"
    assert res.post_op_recovery_guidance.recommended_side == "Prone (Face-Down)"
    assert "Triple Pillow" in res.post_op_recovery_guidance.airway_clearance

def test_eye_sentinel_post_op_recovery_odd_hour():
    agent = EyeSentinelAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="Recovering after surgery",
        pitch=-60.0,
        multimodal_flags=["post_op_recovery"]
    )
    # 13:00 is odd hour -> Left or Right rotation side recommendation
    res = agent.evaluate_triage(frame, "2026-05-15T13:00:00Z")
    assert res.status == "POST_OP_RECOVERY"
    assert "Side" in res.post_op_recovery_guidance.recommended_side

def test_eye_sentinel_risk_factors():
    agent = EyeSentinelAgent()
    # Test multiplicative: base 0.70 * cataract 1.2 * age>50 1.1 = 0.924
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="I see floaters",
        history=HistoryInfo(cataract_surgery=True, age_over_50=True)
    )
    res = agent.local_matcher.evaluate(frame, "2026-05-15T12:00:00Z")
    assert res.status == "URGENT"
    assert abs(res.confidence_score - 0.924) < 0.001


# ----------------- GAZE COMPASS TESTS -----------------

def test_gaze_compass_obscured():
    agent = GazeCompassAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="",
        target_x=0.1, target_y=0.1,
        blind_x=0.0, blind_y=0.0, blind_r=0.3
    )
    # Distance is hypot(0.1, 0.1) = 0.141 <= 0.3 (inside scotoma)
    res = agent._evaluate_local(frame, "2026-05-15T12:00:00Z")
    assert res.status == "VIOLATION"
    assert res.pan_localization > 0.0
    assert "obscured" in res.action_required

def test_gaze_compass_prl_lock():
    agent = GazeCompassAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="",
        target_x=0.32, target_y=0.0,
        blind_x=0.0, blind_y=0.0, blind_r=0.3
    )
    # Distance is 0.32: outside blind_r (0.30) but inside blind_r * 1.25 (0.375)
    res = agent._evaluate_local(frame, "2026-05-15T12:00:00Z")
    assert res.status == "SAFE"
    assert "locked" in res.action_required

def test_gaze_compass_clear():
    agent = GazeCompassAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="",
        target_x=0.8, target_y=0.8,
        blind_x=0.0, blind_y=0.0, blind_r=0.3
    )
    res = agent._evaluate_local(frame, "2026-05-15T12:00:00Z")
    assert res.status == "SAFE"
    assert "clear" in res.action_required


# ----------------- PRE-OP WAITLIST TESTS -----------------

def test_preop_waitlist_table_detection():
    agent = PreOpWaitlistAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="Category | Q1 | Q2\nSales | 100 | 120\nCosts | 80 | 90"
    )
    res = agent._evaluate_local(frame, "2026-05-15T12:00:00Z")
    assert res.status == "WAITLIST"
    assert "table" in res.action_required.lower()
    assert "Sales" in res.action_required
    assert "Costs" in res.action_required

def test_preop_waitlist_text_summary():
    agent = PreOpWaitlistAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="This is a simple paragraph.\nIt outlines general information.\nNo tables are here."
    )
    res = agent._evaluate_local(frame, "2026-05-15T12:00:00Z")
    assert res.status == "WAITLIST"
    assert "simple paragraph" in res.action_required


# ----------------- BE MY EYES TESTS -----------------

def test_be_my_eyes_low_confidence():
    agent = BeMyEyesAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="Reading insulin syringe details.",
        confidence=80.0 # Under 82% threshold
    )
    res = agent._evaluate_local(frame, "2026-05-15T12:00:00Z")
    assert res.status == "BME"
    assert "Be My Eyes" in res.action_required
    assert res.escalation_trigger == "Be My Eyes Professional Network"

def test_be_my_eyes_panic_words():
    agent = BeMyEyesAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="I am confused and scared by this bottle, please connect me.",
        confidence=95.0
    )
    res = agent._evaluate_local(frame, "2026-05-15T12:00:00Z")
    assert res.status == "BME"
    assert "Be My Eyes" in res.action_required

def test_be_my_eyes_safe():
    agent = BeMyEyesAgent()
    frame = TelemetryFrame(
        user_id="user_123",
        input_string="The bottle shows 50ml",
        confidence=90.0
    )
    res = agent._evaluate_local(frame, "2026-05-15T12:00:00Z")
    assert res.status == "SAFE"
    assert res.escalation_trigger is None


# ----------------- API / FLASK GATEWAY TESTS -----------------

def test_flask_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json == {"status": "healthy"}

def test_flask_info(client):
    res = client.get("/v1/triage/info")
    assert res.status_code == 200
    assert "service" in res.json
    assert "emergency_keywords" in res.json

def test_flask_protected_config_unauthorized(client):
    res = client.get("/v1/system/config")
    assert res.status_code == 401
    assert "error" in res.json

def test_flask_protected_config_authorized(client):
    res = client.get("/v1/system/config", headers={"X-API-Key": "TEST_SECRET_KEY"})
    assert res.status_code == 200
    assert res.json["environment"] == "Production"

def test_flask_protected_stats_authorized(client):
    res = client.get("/v1/system/stats", headers={"X-API-Key": "TEST_SECRET_KEY"})
    assert res.status_code == 200
    assert "total_requests" in res.json

def test_flask_single_triage_api(client):
    req_body = {
        "user_id": "test_uuid",
        "input_string": "black curtain in eye since sudden onset",
        "client_id": "OCUGUARD_CLIENT",
        "user_token": "OCUGUARD_TOKEN",
        "history": {
            "cataract_surgery": True
        }
    }
    res = client.post("/v1/triage", json=req_body)
    assert res.status_code == 200
    assert res.json["message"] == "Triage analysis completed"
    assert res.json["data"]["status"] == "EMERGENCY"
    assert res.json["data"]["escalation_trigger"] == "Be My Eyes Professional Network"

def test_flask_batch_triage_api(client):
    req_body = {
        "requests": [
            {
                "user_id": "user1",
                "input_string": "black curtain",
                "client_id": "OCUGUARD_CLIENT",
                "user_token": "OCUGUARD_TOKEN",
                "history": {"cataract_surgery": True}
            },
            {
                "user_id": "user2",
                "input_string": "dry eyes redness",
                "client_id": "OCUGUARD_CLIENT",
                "user_token": "OCUGUARD_TOKEN"
            }
        ]
    }
    res = client.post("/v1/triage/batch", json=req_body)
    assert res.status_code == 200
    assert len(res.json["results"]) == 2
    assert res.json["results"][0]["data"]["status"] == "EMERGENCY"
    assert res.json["results"][1]["data"]["status"] == "ROUTINE"

def test_flask_batch_triage_exceeds_limit(client):
    req_body = {
        "requests": [{"user_id": f"u{i}", "input_string": "dry eye"} for i in range(11)]
    }
    res = client.post("/v1/triage/batch", json=req_body)
    assert res.status_code == 422
    assert "Max batch size" in res.json["message"]

def test_flask_rate_limiting(client):
    req_body = {
        "user_id": "spammer_user",
        "input_string": "redness",
        "client_id": "OCUGUARD_CLIENT",
        "user_token": "OCUGUARD_TOKEN"
    }
    # Send 60 requests -> should succeed
    for _ in range(60):
        res = client.post("/v1/triage", json=req_body)
        assert res.status_code == 200
    # Send 61st request -> should get rate limited
    res = client.post("/v1/triage", json=req_body)
    assert res.status_code == 429
    assert "Rate limit" in res.json["message"]

def test_flask_validation_error_422(client):
    req_body = {
        # Missing user_id and input_string fields to trigger ValidationError
        "client_id": "OCUGUARD_CLIENT",
        "user_token": "OCUGUARD_TOKEN"
    }
    res = client.post("/v1/triage", json=req_body)
    assert res.status_code == 422
    assert "error" in res.json

def test_driving_context_emergency(client):
    req_body = {
        "user_id": "user_drive",
        "input_string": "black curtain and I am driving",
        "client_id": "OCUGUARD_CLIENT",
        "user_token": "OCUGUARD_TOKEN"
    }
    res = client.post("/v1/triage", json=req_body)
    assert res.status_code == 200
    assert "PULL OVER" in res.json["data"]["action_required"]


# ----------------- LLM MONKEYPATCH TESTS -----------------

def test_eye_sentinel_llm_success(monkeypatch):
    import eye_sentinel
    monkeypatch.setattr(eye_sentinel, "LANGCHAIN_AVAILABLE", True)
    mock_chat = MagicMock()
    monkeypatch.setattr(eye_sentinel, "ChatOpenAI", mock_chat)

    agent = EyeSentinelAgent(openai_api_key="mock-key")
    assert agent.llm is not None
    
    # Mock ChatOpenAI's invoke method
    mock_response_content = json.dumps({
        "status": "EMERGENCY",
        "action_required": "🚨 Proceed to emergency room immediately.",
        "confidence_score": 0.95,
        "reasoning": "LLM output shows retinal detachment risk."
    })
    
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MockLLMResponse(mock_response_content)
    agent.llm = mock_llm

    frame = TelemetryFrame(
        user_id="user_123",
        input_string="black curtain",
        client_id="OCUGUARD_CLIENT",
        user_token="OCUGUARD_TOKEN"
    )
    
    res = agent.evaluate_triage(frame, "2026-05-15T12:00:00Z")
    assert res.status == "EMERGENCY"
    assert "Proceed to emergency room" in res.action_required
    mock_llm.invoke.assert_called_once()

def test_eye_sentinel_llm_failure_cascade(monkeypatch):
    import eye_sentinel
    monkeypatch.setattr(eye_sentinel, "LANGCHAIN_AVAILABLE", True)
    mock_chat = MagicMock()
    monkeypatch.setattr(eye_sentinel, "ChatOpenAI", mock_chat)

    agent = EyeSentinelAgent(openai_api_key="mock-key")
    assert agent.llm is not None
    
    # Mock ChatOpenAI's invoke method to throw an error, triggering retry and fallback
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("OpenAI API rate limit or outage")
    agent.llm = mock_llm

    frame = TelemetryFrame(
        user_id="user_123",
        input_string="dry eye redness",
        client_id="OCUGUARD_CLIENT",
        user_token="OCUGUARD_TOKEN"
    )
    
    res = agent.evaluate_triage(frame, "2026-05-15T12:00:00Z")
    # Fallback to local matcher should run and correctly identify ROUTINE
    assert res.status == "ROUTINE"
    assert mock_llm.invoke.call_count == 2 # 2 attempts before fallback
