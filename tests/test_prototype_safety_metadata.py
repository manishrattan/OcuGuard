from core.schemas import StreamResponseData


def test_default_response_metadata_does_not_claim_compliance_or_clinical_use():
    response = StreamResponseData(
        status="SAFE",
        action_required="Synthetic demo output.",
        confidence_score=0.0,
        reasoning="Test response.",
        timestamp="2026-01-01T00:00:00Z",
    )

    metadata = response.compliance_gate
    assert "not assessed" in metadata["software_classification"].lower()
    assert "not evaluated" in metadata["fail_safe_status"].lower()
    assert "no certified standard" in metadata["pii_anonymization_standard"].lower()
    assert "not validated" in response.disclaimer.lower()
    assert "hipaa" not in str(metadata).lower()
    assert "gdpr" not in str(metadata).lower()


def test_orientation_threshold_response_is_neutral_demo_language():
    from app import app

    client = app.test_client()
    response = client.post(
        "/v1/stream/evaluate",
        json={
            "user_id": "synthetic-safety-test",
            "input_string": "Synthetic orientation test",
            "agent_mode": "OCUGUARD_CORE",
            "pitch": -35.0,
            "roll": 0.0,
            "yaw": 0.0,
        },
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["status"] == "VIOLATION"
    assert "not guidance for a person" in data["action_required"]
    assert data["confidence_score"] == 0.0
    assert "hipaa" not in str(data["compliance_gate"]).lower()
    assert "gdpr" not in str(data["compliance_gate"]).lower()
