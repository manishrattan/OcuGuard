from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse

import pytest
import requests

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest


class FakeResponse:
    def __init__(self, body, status_code=200):
        self._body = body
        self.status_code = status_code
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._body


def _app_test():
    page_path = Path(__file__).parents[1] / "ui" / "recovery_companion_page.py"
    return AppTest.from_file(str(page_path))


def test_recovery_page_renders_tabs_with_no_hardware_claims():
    def fake_request(method, url, **kwargs):
        path = urlparse(url).path
        if path.endswith("/instructions") or path.endswith("/reminders"):
            return FakeResponse({"items": []})
        return FakeResponse(
            {
                "adapter": "synthetic",
                "adapter_status": "simulation_only",
                "hardware_connected": False,
                "live_capture": False,
                "display_output": False,
                "audio_output": False,
                "capabilities": [],
            }
        )

    with patch("requests.request", side_effect=fake_request):
        app = _app_test().run()

    assert not app.exception
    assert any("Recovery Companion prototype" in title.value for title in app.title)
    assert [tab.label for tab in app.tabs] == [
        "Instruction cards",
        "Reminders",
        "Device status",
        "Privacy controls",
    ]
    assert any("Do not enter real patient information" in item.value for item in app.warning)
    assert any("does not discover" in item.value.lower() for item in app.caption)


def test_streamlit_can_save_and_render_an_instruction_verbatim():
    saved_items = []

    def fake_request(method, url, **kwargs):
        path = urlparse(url).path
        if method == "GET" and path.endswith("/instructions"):
            return FakeResponse({"items": saved_items})
        if method == "GET" and path.endswith("/reminders"):
            return FakeResponse({"items": []})
        if method == "GET" and path.endswith("/capabilities"):
            return FakeResponse({"capabilities": [], "hardware_connected": False})
        if method == "POST" and path.endswith("/instructions"):
            payload = kwargs["json"]
            item = {
                "id": "synthetic-card-id",
                "title": payload["title"],
                "instruction_text": payload["instruction_text"],
                "source_label": payload["source_label"],
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
            saved_items.append(item)
            return FakeResponse({"item": item}, status_code=201)
        pytest.fail(f"Unexpected API request: {method} {url}")

    with patch("requests.request", side_effect=fake_request):
        app = _app_test().run()
        next(widget for widget in app.text_input if widget.key == "recovery-new-title").set_value(
            "Exact wording"
        )
        next(widget for widget in app.text_input if widget.key == "recovery-new-source").set_value(
            "User-entered source"
        )
        next(
            widget
            for widget in app.text_area
            if widget.key == "recovery-new-instruction"
        ).set_value("Line one.\n  Preserve indentation.")
        next(
            button
            for button in app.button
            if button.label == "Save instruction card"
        ).click()
        app.run()

    assert not app.exception
    assert saved_items[0]["instruction_text"] == "Line one.\n  Preserve indentation."
    assert any("Line one." in text.value for text in app.text)


def test_ui_api_client_reports_transport_errors_explicitly():
    from ui.recovery_companion import _api_request

    with patch(
        "requests.request",
        side_effect=requests.exceptions.Timeout(),
    ):
        result, error = _api_request(
            "GET",
            "http://127.0.0.1:5000",
            "/v1/recovery/instructions",
            1,
        )

    assert result is None
    assert error == "The API request timed out."


def test_browser_speech_text_is_script_escaped_before_embedding():
    from ui import recovery_companion

    captured = {}

    def capture(markup, **kwargs):
        captured["markup"] = markup

    with patch.object(recovery_companion.st.components.v1, "html", side_effect=capture):
        recovery_companion._speak_instruction(
            '</script><script>alert("no")</script>', "safe-test"
        )

    assert "\\u003c/script\\u003e" in captured["markup"]
    assert '</script><script>alert("no")</script>' not in captured["markup"]
    assert "Stop reading aloud" in captured["markup"]
