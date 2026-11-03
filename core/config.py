from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "app.json"


def load_settings(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else Path(
        os.getenv("OCUGUARD_CONFIG_FILE", DEFAULT_CONFIG_PATH)
    )
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError(f"Application configuration not found: {path}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Application configuration is invalid JSON: {path}") from error

    if not isinstance(settings, dict):
        raise ValueError("Application configuration must be a JSON object.")

    for section in (
        "application",
        "features",
        "recovery",
        "device",
        "ui",
    ):
        if not isinstance(settings.get(section), dict):
            raise ValueError(f"Configuration section '{section}' must be an object.")
    application = settings["application"]
    listing = application.get("listing_draft")
    if not isinstance(application.get("name"), str) or not application["name"].strip():
        raise ValueError("application.name must be a non-empty string.")
    if not isinstance(application.get("prototype_notice"), str):
        raise ValueError("application.prototype_notice must be a string.")
    if not isinstance(listing, dict) or any(
        not isinstance(listing.get(key), str) or not listing[key].strip()
        for key in ("name", "category_hypothesis", "short_description")
    ):
        raise ValueError(
            "application.listing_draft requires name, category_hypothesis, "
            "and short_description strings."
        )
    for key in ("privacy_policy_url", "support_url"):
        value = listing.get(key)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"application.listing_draft.{key} must be a string or null.")

    recovery = settings["recovery"]
    database_path = os.getenv(
        "OCUGUARD_DATABASE_PATH", recovery.get("database_path")
    )
    if not isinstance(database_path, str) or not database_path.strip():
        raise ValueError("recovery.database_path must be a non-empty path.")
    resolved_database_path = Path(database_path)
    if not resolved_database_path.is_absolute():
        resolved_database_path = PROJECT_ROOT / resolved_database_path
    recovery["database_path"] = str(resolved_database_path)

    _require_positive_int(recovery, "max_cards_per_user")
    _require_positive_int(recovery, "max_reminders_per_user")
    _require_positive_int(recovery, "max_user_id_chars")
    _require_positive_int(recovery, "max_title_chars")
    _require_positive_int(recovery, "max_instruction_chars")
    _require_positive_int(recovery, "max_source_chars")

    recurrence = recovery.get("allowed_recurrence_minutes")
    if (
        not isinstance(recurrence, list)
        or not recurrence
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in recurrence
        )
        or len(recurrence) != len(set(recurrence))
        or 0 not in recurrence
    ):
        raise ValueError(
            "recovery.allowed_recurrence_minutes must be unique non-negative "
            "integers and include 0 for one-time reminders."
        )
    snooze_minutes = recovery.get("allowed_snooze_minutes")
    if (
        not isinstance(snooze_minutes, list)
        or not snooze_minutes
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in snooze_minutes
        )
        or len(snooze_minutes) != len(set(snooze_minutes))
    ):
        raise ValueError(
            "recovery.allowed_snooze_minutes must be unique positive integers."
        )

    device = settings["device"]
    if device.get("adapter") != "synthetic":
        raise ValueError(
            "Only the synthetic device adapter is implemented; vendor adapters "
            "must be explicitly integrated and reviewed."
        )
    _require_positive_int(device, "session_ttl_seconds")
    capabilities = device.get("capabilities")
    if not isinstance(capabilities, list) or any(
        not isinstance(value, str) or not value.strip() for value in capabilities
    ):
        raise ValueError("device.capabilities must be a list of non-empty strings.")

    ui = settings["ui"]
    if not isinstance(ui.get("api_url"), str) or not ui["api_url"].strip():
        raise ValueError("ui.api_url must be a non-empty string.")
    if (
        isinstance(ui.get("api_timeout_seconds"), bool)
        or not isinstance(ui.get("api_timeout_seconds"), (int, float))
        or ui["api_timeout_seconds"] <= 0
    ):
        raise ValueError("ui.api_timeout_seconds must be a positive number.")
    timezones = ui.get("timezones")
    if (
        not isinstance(timezones, list)
        or not timezones
        or any(not isinstance(value, str) or not value.strip() for value in timezones)
    ):
        raise ValueError("ui.timezones must be a list of non-empty strings.")
    for value in timezones:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError(f"Unknown IANA timezone in ui.timezones: {value}") from error

    features = settings["features"]
    for name in ("recovery_companion", "device_session_demo", "browser_speech"):
        if not isinstance(features.get(name), bool):
            raise ValueError(f"features.{name} must be a boolean.")

    environment = os.getenv("OCUGUARD_ENVIRONMENT", "development").lower()
    api_key = os.getenv("API_KEY")
    if environment == "production":
        if not api_key:
            raise RuntimeError(
                "API_KEY is required when OCUGUARD_ENVIRONMENT=production."
            )
        raise RuntimeError(
            "Production startup is disabled until per-user authentication, "
            "encrypted persistent storage, transport security, and operational "
            "controls are implemented."
        )
    settings["runtime"] = {
        "environment": environment,
        "api_key_configured": bool(api_key),
    }
    return settings


def _require_positive_int(section: dict[str, Any], key: str) -> None:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"Configuration value '{key}' must be a positive integer.")
