from __future__ import annotations

import hmac
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    ValidationError,
    field_validator,
)

from core.recovery import (
    CapacityExceededError,
    InstructionNotFoundError,
    parse_scheduled_at,
    validate_timezone,
    validate_user_id,
)


class InstructionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    title: str
    instruction_text: str
    source_label: str

    @field_validator("title", "source_label")
    @classmethod
    def strip_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty.")
        return value

    @field_validator("instruction_text")
    @classmethod
    def preserve_nonempty_instruction(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty.")
        return value


class ReminderBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    instruction_id: str
    scheduled_at: str
    timezone: str
    recurrence_minutes: StrictInt

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        return validate_timezone(value)


class ReminderActionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    action: str
    snooze_minutes: StrictInt | None = None


class DeleteDataBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    confirm: bool


class DeviceSessionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    requested_capabilities: list[str] = Field(default_factory=list)

    @field_validator("requested_capabilities")
    @classmethod
    def unique_capabilities(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value) or len(value) != len(set(value)):
            raise ValueError("capabilities must be unique non-empty strings.")
        return value


class DeviceActionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    action: str


def create_recovery_blueprint() -> Blueprint:
    blueprint = Blueprint("recovery", __name__)

    @blueprint.before_request
    def check_optional_api_key():
        expected_key = current_app.config.get("OCUGUARD_API_KEY")
        if expected_key:
            provided_key = request.headers.get("X-API-Key", "")
            if not hmac.compare_digest(
                str(expected_key).encode("utf-8"), provided_key.encode("utf-8")
            ):
                return jsonify(
                    {
                        "error": {
                            "code": "unauthorized",
                            "message": "A valid API key is required.",
                        }
                    }
                ), 401
        path = request.path
        settings = current_app.config["OCUGUARD_SETTINGS"]
        if path.startswith("/v1/recovery/") and not settings["features"][
            "recovery_companion"
        ]:
            return jsonify(
                {
                    "error": {
                        "code": "feature_disabled",
                        "message": "The recovery companion feature is disabled.",
                    }
                }
            ), 404
        if path.startswith("/v1/device/") and not settings["features"][
            "device_session_demo"
        ]:
            return jsonify(
                {
                    "error": {
                        "code": "feature_disabled",
                        "message": "The device session demo is disabled.",
                    }
                }
            ), 404
        return None

    @blueprint.get("/v1/recovery/instructions")
    def list_instructions():
        user_id, error_response = _query_user_id()
        if error_response:
            return error_response
        items = _store().list_instructions(user_id)
        return jsonify({"items": items}), 200

    @blueprint.post("/v1/recovery/instructions")
    def create_instruction():
        body, error_response = _request_model(InstructionBody)
        if error_response:
            return error_response
        user_id, error_response = _validate_user_id(body.user_id)
        if error_response:
            return error_response
        limits = _settings()["recovery"]
        validation_error = _validate_instruction_lengths(body, limits)
        if validation_error:
            return validation_error
        store = _store()
        try:
            item = store.create_instruction(
                user_id,
                body.title,
                body.instruction_text,
                body.source_label,
                limits["max_cards_per_user"],
            )
        except CapacityExceededError as error:
            return _limit_error(str(error))
        return jsonify({"item": item}), 201

    @blueprint.put("/v1/recovery/instructions/<instruction_id>")
    def update_instruction(instruction_id: str):
        body, error_response = _request_model(InstructionBody)
        if error_response:
            return error_response
        user_id, error_response = _validate_user_id(body.user_id)
        if error_response:
            return error_response
        validation_error = _validate_instruction_lengths(
            body, _settings()["recovery"]
        )
        if validation_error:
            return validation_error
        item = _store().update_instruction(
            user_id,
            instruction_id,
            body.title,
            body.instruction_text,
            body.source_label,
        )
        if item is None:
            return _not_found("Instruction card was not found.")
        return jsonify({"item": item}), 200

    @blueprint.delete("/v1/recovery/instructions/<instruction_id>")
    def delete_instruction(instruction_id: str):
        user_id, error_response = _query_user_id()
        if error_response:
            return error_response
        if not _store().delete_instruction(user_id, instruction_id):
            return _not_found("Instruction card was not found.")
        return "", 204

    @blueprint.get("/v1/recovery/reminders")
    def list_reminders():
        user_id, error_response = _query_user_id()
        if error_response:
            return error_response
        return jsonify({"items": _store().list_reminders(user_id)}), 200

    @blueprint.post("/v1/recovery/reminders")
    def create_reminder():
        body, error_response = _request_model(ReminderBody)
        if error_response:
            return error_response
        user_id, error_response = _validate_user_id(body.user_id)
        if error_response:
            return error_response
        settings = _settings()["recovery"]
        allowed_intervals = settings["allowed_recurrence_minutes"]
        if body.recurrence_minutes not in allowed_intervals:
            return _validation_error(
                "recurrence_minutes must be one of the configured reminder intervals."
            )
        try:
            scheduled_at = parse_scheduled_at(body.scheduled_at)
        except ValueError as error:
            return _validation_error(str(error))
        store = _store()
        try:
            item = store.create_reminder(
                user_id,
                body.instruction_id,
                scheduled_at,
                body.timezone,
                body.recurrence_minutes or None,
                settings["max_reminders_per_user"],
            )
        except CapacityExceededError as error:
            return _limit_error(str(error))
        except InstructionNotFoundError:
            return _not_found("Instruction card was not found.")
        return jsonify({"item": item}), 201

    @blueprint.patch("/v1/recovery/reminders/<reminder_id>")
    def update_reminder(reminder_id: str):
        body, error_response = _request_model(ReminderActionBody)
        if error_response:
            return error_response
        user_id, error_response = _validate_user_id(body.user_id)
        if error_response:
            return error_response
        if body.action not in {"pause", "resume", "snooze", "acknowledge"}:
            return _validation_error(
                "action must be pause, resume, snooze, or acknowledge."
            )
        if body.action == "snooze":
            if body.snooze_minutes not in _settings()["recovery"][
                "allowed_snooze_minutes"
            ]:
                return _validation_error(
                    "snooze_minutes must be one of the configured snooze intervals."
                )
        elif body.snooze_minutes is not None:
            return _validation_error(
                "snooze_minutes is only accepted with the snooze action."
            )
        try:
            item = _store().update_reminder_action(
                user_id,
                reminder_id,
                body.action,
                body.snooze_minutes,
            )
        except ValueError as error:
            return _validation_error(str(error))
        if item is None:
            return _not_found("Reminder was not found.")
        return jsonify({"item": item}), 200

    @blueprint.delete("/v1/recovery/reminders/<reminder_id>")
    def delete_reminder(reminder_id: str):
        user_id, error_response = _query_user_id()
        if error_response:
            return error_response
        if not _store().delete_reminder(user_id, reminder_id):
            return _not_found("Reminder was not found.")
        return "", 204

    @blueprint.delete("/v1/recovery/data")
    def delete_user_data():
        body, error_response = _request_model(DeleteDataBody)
        if error_response:
            return error_response
        if not body.confirm:
            return _validation_error("confirm must be true to delete prototype data.")
        user_id, error_response = _validate_user_id(body.user_id)
        if error_response:
            return error_response
        _store().delete_user_data(user_id)
        return jsonify({"deleted": True}), 200

    @blueprint.get("/v1/device/capabilities")
    def device_capabilities():
        return jsonify(_device_adapter().capabilities()), 200

    @blueprint.post("/v1/device/sessions")
    def create_device_session():
        body, error_response = _request_model(DeviceSessionBody)
        if error_response:
            return error_response
        user_id, error_response = _validate_user_id(body.user_id)
        if error_response:
            return error_response
        try:
            session = _device_adapter().start(
                user_id, body.requested_capabilities
            )
        except ValueError as error:
            return _validation_error(str(error))
        return jsonify({"session": session}), 201

    @blueprint.post("/v1/device/sessions/<session_id>/actions")
    def update_device_session(session_id: str):
        body, error_response = _request_model(DeviceActionBody)
        if error_response:
            return error_response
        user_id, error_response = _validate_user_id(body.user_id)
        if error_response:
            return error_response
        try:
            session = _device_adapter().act(
                session_id, user_id, body.action
            )
        except KeyError:
            return _not_found("Device session was not found.")
        except ValueError as error:
            return _validation_error(str(error))
        return jsonify({"session": session}), 200

    return blueprint


def _settings() -> dict[str, Any]:
    return current_app.config["OCUGUARD_SETTINGS"]


def _store():
    return current_app.config["RECOVERY_STORE"]


def _device_adapter():
    return current_app.config["DEVICE_SESSION_ADAPTER"]


def _request_model(
    model: type[BaseModel],
) -> tuple[BaseModel | None, Any | None]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, _bad_request("A JSON object is required.")
    try:
        return model.model_validate(payload), None
    except ValidationError as error:
        details = [
            {
                "field": ".".join(str(part) for part in item["loc"]),
                "message": item["msg"],
                "type": item["type"],
            }
            for item in error.errors(include_input=False)
        ]
        return None, (
            jsonify(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "Request fields did not pass validation.",
                        "details": details,
                    }
                }
            ),
            422,
        )


def _query_user_id() -> tuple[str | None, Any | None]:
    return _validate_user_id(request.args.get("user_id"))


def _validate_user_id(value: object) -> tuple[str | None, Any | None]:
    try:
        user_id = validate_user_id(
            value, _settings()["recovery"]["max_user_id_chars"]
        )
    except ValueError as error:
        return None, _validation_error(str(error))
    return user_id, None


def _validate_instruction_lengths(
    body: InstructionBody, limits: dict[str, Any]
) -> Any | None:
    lengths = (
        ("title", body.title, limits["max_title_chars"]),
        ("instruction_text", body.instruction_text, limits["max_instruction_chars"]),
        ("source_label", body.source_label, limits["max_source_chars"]),
    )
    for field, value, maximum in lengths:
        if len(value) > maximum:
            return _validation_error(
                f"{field} must contain no more than {maximum} characters."
            )
    return None


def _bad_request(message: str):
    return jsonify({"error": {"code": "bad_request", "message": message}}), 400


def _validation_error(message: str):
    return jsonify({"error": {"code": "invalid_input", "message": message}}), 422


def _not_found(message: str):
    return jsonify({"error": {"code": "not_found", "message": message}}), 404


def _limit_error(message: str):
    return jsonify({"error": {"code": "limit_reached", "message": message}}), 409
