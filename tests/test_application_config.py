from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.config import load_settings


def test_application_configuration_supports_database_override(tmp_path, monkeypatch):
    monkeypatch.delenv("OCUGUARD_CONFIG_FILE", raising=False)
    override_path = tmp_path / "custom-recovery.sqlite3"
    monkeypatch.setenv("OCUGUARD_DATABASE_PATH", str(override_path))

    settings = load_settings()

    assert settings["recovery"]["database_path"] == str(override_path)
    assert settings["device"]["adapter"] == "synthetic"
    assert settings["features"]["recovery_companion"] is True


def test_application_configuration_rejects_unknown_device_adapter(tmp_path):
    config_path = tmp_path / "config.json"
    settings_path = Path(__file__).parents[1] / "config" / "app.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    settings["device"]["adapter"] = "unreviewed-vendor"
    config_path.write_text(json.dumps(settings), encoding="utf-8")

    with pytest.raises(ValueError, match="Only the synthetic"):
        load_settings(config_path)


def test_production_environment_requires_configured_api_key(monkeypatch):
    monkeypatch.setenv("OCUGUARD_ENVIRONMENT", "production")
    monkeypatch.delenv("API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="API_KEY is required"):
        load_settings()


def test_production_startup_fails_closed_even_with_a_shared_api_key(monkeypatch):
    monkeypatch.setenv("OCUGUARD_ENVIRONMENT", "production")
    monkeypatch.setenv("API_KEY", "synthetic-test-secret")

    with pytest.raises(RuntimeError, match="per-user authentication"):
        load_settings()
