import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "message": "Stream evaluation completed",
            "data": {
                "status": "VIOLATION",
                "action_required": "Synthetic threshold demo result.",
            },
            "timestamp": "2026-10-30T00:00:00Z",
        }


class FakeMcpResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "jsonrpc": "2.0",
            "id": "synthetic-request",
            "result": {
                "structuredContent": {
                    "data": {
                        "status": "VIOLATION",
                        "action_required": "Synthetic MCP response.",
                    }
                },
                "content": [
                    {"type": "text", "text": "Status: VIOLATION"}
                ],
                "isError": False,
            },
        }


def _app_test():
    app_path = Path(__file__).parents[1] / "ui" / "studio.py"
    return AppTest.from_file(str(app_path)).run()


def _scene_document():
    return (
        Path(__file__).parents[1] / "ui" / "glasses_component" / "index.html"
    ).read_text(encoding="utf-8")


def _glasses_args(app):
    component = app.get("component_instance")[0]
    return json.loads(component.proto.json_args)


def test_orientation_slider_updates_visual_values_without_calling_api():
    with patch("requests.post") as post:
        app = _app_test()
        app.slider[0].set_value(-35).run()

    assert not app.exception
    assert app.selectbox[0].value == "OCUGUARD_CORE"
    assert app.metric[0].value == "-35°"
    assert _glasses_args(app)["pitch"] == -35.0
    post.assert_not_called()


def test_scene_renders_threejs_model_and_live_severity_map():
    app = _app_test()
    initial_scene = _scene_document()

    assert "three@0.180.0/build/three.module.js" in initial_scene
    assert "THREE.WebGLRenderer" in initial_scene
    assert "THREE.ExtrudeGeometry" in initial_scene
    assert 'id="zone-status" role="status">UNKNOWN · MCP RESPONSE MAP' in initial_scene
    assert "const severityColors" in initial_scene
    assert "streamlit:setComponentValue" in initial_scene
    assert "streamlit:componentReady" in initial_scene
    assert 'addEventListener("pointerdown"' in initial_scene
    assert 'addEventListener("pointermove"' in initial_scene
    assert "glasses.rotation.x" in initial_scene
    assert "glasses.rotation.y" in initial_scene
    assert "glasses.rotation.z" in initial_scene
    assert "now - lastSentAt < 400" in initial_scene
    assert "sendComponentValue(true)" in initial_scene
    assert "GREEN</span>" in initial_scene
    assert "YELLOW</span>" in initial_scene
    assert "URGENT</span>" in initial_scene

    app.slider[0].set_value(-35).run()
    assert _glasses_args(app)["pitch"] == -35.0


def test_orientation_sliders_cover_full_yaw_and_roll_rotation():
    app = _app_test()

    app.slider[0].set_value(90)
    app.slider[1].set_value(-180)
    app.slider[2].set_value(180)
    app.run()

    assert not app.exception
    assert app.metric[0].value == "90°"
    assert app.metric[1].value == "-180°"
    assert app.metric[2].value == "180°"
    max_args = _glasses_args(app)
    assert max_args["pitch"] == 90.0
    assert max_args["roll"] == -180.0
    assert max_args["yaw"] == 180.0

    app.slider[0].set_value(-90)
    app.slider[1].set_value(180)
    app.slider[2].set_value(-180)
    app.run()
    min_args = _glasses_args(app)
    assert min_args["pitch"] == -90.0
    assert min_args["roll"] == 180.0
    assert min_args["yaw"] == -180.0


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("SAFE", "GREEN"),
        ("WARN", "YELLOW"),
        ("VIOLATION", "YELLOW"),
        ("ESCALATION", "URGENT"),
        ("CRITICAL_ALERT", "URGENT"),
        ("unexpected", "UNKNOWN"),
    ],
)
def test_mcp_status_maps_to_display_severity(status, expected):
    from ui.studio import _mcp_severity

    assert _mcp_severity(status) == expected


def test_synthetic_frame_posts_jsonrpc_tools_call_with_profile_flags():
    app = _app_test()
    app.checkbox[0].set_value(True)
    app.checkbox[1].set_value(True)
    send_button = next(
        button for button in app.button if button.label == "Send synthetic OCR to MCP"
    )

    with patch("requests.post", return_value=FakeMcpResponse()) as post:
        send_button.click().run()

    assert not app.exception
    post.assert_called_once()
    assert post.call_args.args[0] == "http://127.0.0.1:3000/messages"
    request_payload = post.call_args.kwargs["json"]
    assert request_payload["jsonrpc"] == "2.0"
    assert request_payload["method"] == "tools/call"
    assert request_payload["params"]["name"] == "evaluate_wearable_stream"
    arguments = request_payload["params"]["arguments"]
    assert arguments["pitch"] == -20.0
    assert arguments["yaw"] == -5.0
    assert arguments["input_string"] == "Synthetic orientation demo."
    assert arguments["history"] == {
        "cataract_surgery": True,
        "retinal_disease": True,
    }
    assert any(
        "YELLOW" in item.value
        for item in app.markdown
        if isinstance(item.value, str)
    )


def test_drag_orientation_posts_mcp_request_and_plays_warning_sound():
    app = _app_test()
    app.session_state["demo_pitch"] = -35
    app.session_state["demo_roll"] = 12
    app.session_state["demo_yaw"] = 40
    app.session_state["pending_glasses_orientation"] = {
        "pitch": -35,
        "roll": 12,
        "yaw": 40,
    }

    with patch("requests.post", return_value=FakeMcpResponse()) as post:
        app.run()

    assert not app.exception
    post.assert_called_once()
    request_payload = post.call_args.kwargs["json"]
    arguments = request_payload["params"]["arguments"]
    assert post.call_args.args[0] == "http://127.0.0.1:3000/messages"
    assert post.call_args.kwargs["timeout"] == 3.0
    assert arguments["pitch"] == -35.0
    assert arguments["roll"] == 12.0
    assert arguments["yaw"] == 40.0
    assert len(app.get("audio")) == 1
    assert app.session_state["activity_events"][0]["mode"] == "DRAG:OCUGUARD_CORE"
    assert _glasses_args(app)["pitch"] == -35.0


def test_optional_demo_audio_plays_for_returned_mcp_warning_map():
    app = _app_test()
    app.slider[0].set_value(-35).run()
    app.toggle[0].set_value(True).run()
    send_button = next(
        button for button in app.button if button.label == "Send synthetic OCR to MCP"
    )

    with patch("requests.post", return_value=FakeMcpResponse()):
        send_button.click().run()

    assert not app.exception
    assert len(app.get("audio")) == 1
    assert any(
        "YELLOW" in item.value
        for item in app.markdown
        if isinstance(item.value, str)
    )


def test_selected_agent_is_named_and_catalog_covers_every_mode():
    app = _app_test()
    expected_agents = {
        "EYE_SENTINEL": "Eye Sentinel",
        "OCUGUARD_CORE": "OcuGuard Core (built-in rules)",
        "GAZE_COMPASS": "Gaze Compass",
        "TABULAR_LAYOUT_SPEECH": "Tabular Layout Speech",
        "ERGONOMIC_SCHEDULE": "Ergonomic Schedule",
        "AMBIENT_LUMINANCE": "Ambient Luminance",
        "BE_MY_EYES": "Be My Eyes (local prototype mode)",
        "ANISEIKONIA_SCALING": "Aniseikonia Scaling",
        "METAMORPHOPSIA_GRID_REMAPPER": "Metamorphopsia Grid Remapper",
        "BIOFEEDBACK_ANXIETY_SENTINEL": "Biofeedback Anxiety Sentinel",
    }

    assert app.selectbox[0].label == "Agent to evaluate"
    assert len(app.selectbox[0].options) == 10
    assert app.expander[0].label == "Explore strengths of all 10 prototype agents"

    for mode, agent_name in expected_agents.items():
        app.selectbox[0].set_value(mode).run()
        markdown_values = [
            element.value
            for element in app.markdown
            if isinstance(element.value, str)
        ]
        assert f"**{agent_name}**" in markdown_values
        assert any("supplied" in value.lower() for value in markdown_values)


def test_faq_capabilities_page_lists_and_opens_agent_documentation():
    page_path = (
        Path(__file__).parents[1] / "ui" / "pages" / "1_FAQ_and_Capabilities.py"
    )
    docs_path = Path(__file__).parents[1] / "ui" / "docs" / "agents"
    agent_docs = [path for path in docs_path.glob("*.md") if path.name != "README.md"]
    app = AppTest.from_file(str(page_path)).run()

    assert not app.exception
    assert len(agent_docs) == 12
    assert any("FAQ & Capabilities" in item.value for item in app.title)
    assert any(button.label == "Supervisor" for button in app.button)
    assert any(button.label == "Pre-Op Waitlist" for button in app.button)

    eye_sentinel = next(
        button for button in app.button if button.label == "Eye Sentinel"
    )
    eye_sentinel.click().run()

    assert not app.exception
    assert any(
        "Does this diagnose an eye condition?" in item.value for item in app.markdown
    )


def test_faq_search_filters_the_agent_directory():
    page_path = (
        Path(__file__).parents[1] / "ui" / "pages" / "1_FAQ_and_Capabilities.py"
    )
    app = AppTest.from_file(str(page_path)).run()

    app.text_input[0].set_value("pan_localization").run()

    visible_button_labels = {button.label for button in app.button}
    assert "Gaze Compass" in visible_button_labels
    assert "Eye Sentinel" not in visible_button_labels
    assert "Open Gaze Compass FAQ" in visible_button_labels
    assert "Open Eye Sentinel FAQ" not in visible_button_labels


def test_streamlit_entrypoint_registers_studio_and_faq_navigation():
    entrypoint = Path(__file__).parents[1] / "ui" / "streamlit_app.py"
    app = AppTest.from_file(str(entrypoint)).run()

    assert not app.exception
    assert any("OcuGuard Studio" in item.value for item in app.markdown)


def test_submitted_warning_status_renders_opt_in_demo_audio():
    app = _app_test()
    app.slider[0].set_value(-35).run()
    app.toggle[0].set_value(True).run()

    with patch("requests.post", return_value=FakeResponse()) as post:
        app.button[3].click().run()

    assert not app.exception
    post.assert_called_once()
    assert post.call_args.kwargs["json"]["pitch"] == -35.0
    assert post.call_args.kwargs["json"]["agent_mode"] == "OCUGUARD_CORE"
    assert app.session_state["last_api_result"]["data"]["status"] == "VIOLATION"
    assert app.session_state["last_api_mode"] == "OCUGUARD_CORE"
    assert app.session_state["activity_events"][0]["pitch"] == -35.0
    assert len(app.get("audio")) == 1

    app.selectbox[0].set_value("ERGONOMIC_SCHEDULE").run()
    captions = [item.value for item in app.caption]
    warnings = [item.value for item in app.warning]
    assert any("Last evaluated by: OcuGuard Core" in value for value in captions)
    assert any("last submission" in value for value in warnings)
