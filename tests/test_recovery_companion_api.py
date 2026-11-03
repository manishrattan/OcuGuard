from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.config import load_settings
from core.recovery import RecoveryStore
from integrations.oem.device_sessions import SyntheticDeviceSessionAdapter


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    import app as application

    settings = load_settings()
    settings["recovery"]["database_path"] = str(tmp_path / "recovery.sqlite3")
    monkeypatch.setitem(application.app.config, "OCUGUARD_SETTINGS", settings)
    monkeypatch.setitem(
        application.app.config,
        "RECOVERY_STORE",
        RecoveryStore(settings["recovery"]["database_path"]),
    )
    monkeypatch.setitem(
        application.app.config,
        "DEVICE_SESSION_ADAPTER",
        SyntheticDeviceSessionAdapter(
            settings["device"]["capabilities"],
            settings["device"]["session_ttl_seconds"],
        ),
    )
    monkeypatch.setitem(application.app.config, "OCUGUARD_API_KEY", None)
    application.app.config["TESTING"] = True
    return application.app.test_client()


def _instruction_payload(user_id="demo-user", **overrides):
    return {
        "user_id": user_id,
        "title": "Care-team instruction",
        "instruction_text": "Use the exact wording.\nDo not add advice.",
        "source_label": "Entered by user",
        **overrides,
    }


def _create_instruction(client, user_id="demo-user"):
    response = client.post(
        "/v1/recovery/instructions",
        json=_instruction_payload(user_id=user_id),
    )
    assert response.status_code == 201
    return response.get_json()["item"]


def test_instruction_cards_preserve_text_support_updates_and_are_user_scoped(
    api_client,
):
    instruction = _create_instruction(api_client)
    assert instruction["instruction_text"] == (
        "Use the exact wording.\nDo not add advice."
    )

    other_user = api_client.get(
        "/v1/recovery/instructions?user_id=another-user"
    )
    assert other_user.status_code == 200
    assert other_user.get_json()["items"] == []

    update = api_client.put(
        f"/v1/recovery/instructions/{instruction['id']}",
        json=_instruction_payload(
            title="Updated title",
            instruction_text="Updated verbatim instruction.",
        ),
    )
    assert update.status_code == 200
    assert update.get_json()["item"]["instruction_text"] == (
        "Updated verbatim instruction."
    )
    assert update.get_json()["item"]["title"] == "Updated title"


def test_instruction_validation_does_not_return_submitted_health_text(api_client):
    response = api_client.post(
        "/v1/recovery/instructions",
        json=_instruction_payload(instruction_text="  "),
    )

    assert response.status_code == 422
    assert "instruction_text" in response.get_json()["error"]["details"][0]["field"]
    assert "Do not add" not in response.get_data(as_text=True)

    invalid_user = api_client.get("/v1/recovery/instructions?user_id=not/a/user")
    assert invalid_user.status_code == 422


def test_reminders_are_user_controlled_pause_resume_acknowledge_and_repeat(
    api_client,
):
    instruction = _create_instruction(api_client)
    due_at = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    create = api_client.post(
        "/v1/recovery/reminders",
        json={
            "user_id": "demo-user",
            "instruction_id": instruction["id"],
            "scheduled_at": due_at,
            "timezone": "UTC",
            "recurrence_minutes": 1440,
        },
    )
    assert create.status_code == 201
    reminder = create.get_json()["item"]
    assert reminder["due"] is True
    assert reminder["status"] == "active"

    pause = api_client.patch(
        f"/v1/recovery/reminders/{reminder['id']}",
        json={"user_id": "demo-user", "action": "pause"},
    )
    assert pause.status_code == 200
    assert pause.get_json()["item"]["status"] == "paused"
    assert pause.get_json()["item"]["due"] is False

    resume = api_client.patch(
        f"/v1/recovery/reminders/{reminder['id']}",
        json={"user_id": "demo-user", "action": "resume"},
    )
    assert resume.status_code == 200
    assert resume.get_json()["item"]["status"] == "active"

    acknowledge = api_client.patch(
        f"/v1/recovery/reminders/{reminder['id']}",
        json={"user_id": "demo-user", "action": "acknowledge"},
    )
    assert acknowledge.status_code == 200
    next_due = datetime.fromisoformat(
        acknowledge.get_json()["item"]["scheduled_at"]
    )
    assert next_due > datetime.now(timezone.utc)
    assert acknowledge.get_json()["item"]["status"] == "active"


def test_one_time_reminder_completes_and_card_delete_removes_reminders(api_client):
    instruction = _create_instruction(api_client)
    create = api_client.post(
        "/v1/recovery/reminders",
        json={
            "user_id": "demo-user",
            "instruction_id": instruction["id"],
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
            "timezone": "UTC",
            "recurrence_minutes": 0,
        },
    )
    assert create.status_code == 201
    reminder_id = create.get_json()["item"]["id"]

    acknowledge = api_client.patch(
        f"/v1/recovery/reminders/{reminder_id}",
        json={"user_id": "demo-user", "action": "acknowledge"},
    )
    assert acknowledge.status_code == 200
    assert acknowledge.get_json()["item"]["status"] == "completed"
    assert acknowledge.get_json()["item"]["due"] is False

    delete = api_client.delete(
        f"/v1/recovery/instructions/{instruction['id']}?user_id=demo-user"
    )
    assert delete.status_code == 204
    assert api_client.get("/v1/recovery/reminders?user_id=demo-user").get_json()[
        "items"
    ] == []


def test_due_reminder_can_be_snoozed_only_for_configured_interval(api_client):
    instruction = _create_instruction(api_client)
    create = api_client.post(
        "/v1/recovery/reminders",
        json={
            "user_id": "demo-user",
            "instruction_id": instruction["id"],
            "scheduled_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            "timezone": "UTC",
            "recurrence_minutes": 0,
        },
    )
    reminder_id = create.get_json()["item"]["id"]

    invalid = api_client.patch(
        f"/v1/recovery/reminders/{reminder_id}",
        json={
            "user_id": "demo-user",
            "action": "snooze",
            "snooze_minutes": 30,
        },
    )
    assert invalid.status_code == 422

    snoozed = api_client.patch(
        f"/v1/recovery/reminders/{reminder_id}",
        json={
            "user_id": "demo-user",
            "action": "snooze",
            "snooze_minutes": 10,
        },
    )
    assert snoozed.status_code == 200
    item = snoozed.get_json()["item"]
    assert item["due"] is False
    assert item["status"] == "active"
    assert datetime.fromisoformat(item["scheduled_at"]) > datetime.now(timezone.utc)


def test_reminder_rejects_missing_timezone_unsupported_interval_and_foreign_card(
    api_client,
):
    instruction = _create_instruction(api_client)
    payload = {
        "user_id": "demo-user",
        "instruction_id": instruction["id"],
        "scheduled_at": datetime.now(timezone.utc).isoformat(),
        "timezone": "Not/AZone",
        "recurrence_minutes": 1440,
    }
    assert api_client.post("/v1/recovery/reminders", json=payload).status_code == 422

    payload["timezone"] = "UTC"
    payload["recurrence_minutes"] = 60
    assert api_client.post("/v1/recovery/reminders", json=payload).status_code == 422

    payload["recurrence_minutes"] = 0
    payload["user_id"] = "other-user"
    assert api_client.post("/v1/recovery/reminders", json=payload).status_code == 404


def test_data_deletion_requires_confirmation_and_clears_user_records(api_client):
    _create_instruction(api_client)
    rejected = api_client.delete(
        "/v1/recovery/data",
        json={"user_id": "demo-user", "confirm": False},
    )
    assert rejected.status_code == 422

    deleted = api_client.delete(
        "/v1/recovery/data",
        json={"user_id": "demo-user", "confirm": True},
    )
    assert deleted.status_code == 200
    assert api_client.get("/v1/recovery/instructions?user_id=demo-user").get_json()[
        "items"
    ] == []


def test_optional_api_key_protects_recovery_and_device_routes(api_client, monkeypatch):
    import app as application

    monkeypatch.setitem(
        application.app.config, "OCUGUARD_API_KEY", "synthetic-test-secret"
    )
    assert api_client.get("/v1/device/capabilities").status_code == 401
    assert (
        api_client.get(
            "/v1/device/capabilities",
            headers={"X-API-Key": "synthetic-test-secret"},
        ).status_code
        == 200
    )


def test_device_session_contract_is_explicitly_synthetic_and_has_lifecycle(
    api_client,
):
    capabilities = api_client.get("/v1/device/capabilities").get_json()
    assert capabilities["adapter_status"] == "simulation_only"
    assert capabilities["hardware_connected"] is False
    assert capabilities["live_capture"] is False
    assert capabilities["display_output"] is False
    assert capabilities["audio_output"] is False

    created = api_client.post(
        "/v1/device/sessions",
        json={"user_id": "demo-user", "requested_capabilities": []},
    )
    assert created.status_code == 201
    session = created.get_json()["session"]
    assert session["status"] == "simulated"
    assert session["connection_status"] == "not_connected"
    assert session["hardware_connected"] is False

    paused = api_client.post(
        f"/v1/device/sessions/{session['session_id']}/actions",
        json={"user_id": "demo-user", "action": "pause"},
    )
    assert paused.status_code == 200
    assert paused.get_json()["session"]["status"] == "paused"

    resumed = api_client.post(
        f"/v1/device/sessions/{session['session_id']}/actions",
        json={"user_id": "demo-user", "action": "resume"},
    )
    assert resumed.status_code == 200
    assert resumed.get_json()["session"]["status"] == "simulated"

    stopped = api_client.post(
        f"/v1/device/sessions/{session['session_id']}/actions",
        json={"user_id": "demo-user", "action": "stop"},
    )
    assert stopped.status_code == 200
    assert stopped.get_json()["session"]["status"] == "stopped"


def test_device_session_isolation_and_invalid_transitions(api_client):
    created = api_client.post(
        "/v1/device/sessions",
        json={"user_id": "demo-user", "requested_capabilities": []},
    ).get_json()["session"]
    session_id = created["session_id"]

    wrong_user = api_client.post(
        f"/v1/device/sessions/{session_id}/actions",
        json={"user_id": "another-user", "action": "pause"},
    )
    assert wrong_user.status_code == 404

    invalid_transition = api_client.post(
        f"/v1/device/sessions/{session_id}/actions",
        json={"user_id": "demo-user", "action": "resume"},
    )
    assert invalid_transition.status_code == 422


def test_configured_per_user_card_and_reminder_limits_are_enforced(api_client):
    import app as application

    settings = application.app.config["OCUGUARD_SETTINGS"]
    settings["recovery"]["max_cards_per_user"] = 1
    instruction = _create_instruction(api_client)
    card_limit = api_client.post(
        "/v1/recovery/instructions",
        json=_instruction_payload(title="Second card"),
    )
    assert card_limit.status_code == 409

    settings["recovery"]["max_reminders_per_user"] = 1
    payload = {
        "user_id": "demo-user",
        "instruction_id": instruction["id"],
        "scheduled_at": datetime.now(timezone.utc).isoformat(),
        "timezone": "UTC",
        "recurrence_minutes": 0,
    }
    assert api_client.post("/v1/recovery/reminders", json=payload).status_code == 201
    assert api_client.post("/v1/recovery/reminders", json=payload).status_code == 409
