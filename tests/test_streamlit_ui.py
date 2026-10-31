import base64
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


def _app_test():
    app_path = Path(__file__).parents[1] / "ui" / "streamlit_app.py"
    return AppTest.from_file(str(app_path)).run()


def _scene_document(app):
    source = app.get("iframe")[0].proto.src
    _, _, encoded_document = source.partition(",")
    return base64.b64decode(encoded_document).decode("utf-8")


def test_orientation_slider_updates_visual_values_without_calling_api():
    with patch("requests.post") as post:
        app = _app_test()
        app.slider[0].set_value(35).run()

    assert not app.exception
    assert app.selectbox[0].value == "OCUGUARD_CORE"
    assert app.metric[0].value == "-35°"
    post.assert_not_called()


def test_drag_scene_renders_a_live_core_demo_zone_indicator():
    app = _app_test()
    initial_scene = _scene_document(app)

    assert 'data-initial-zone="green"' in initial_scene
    assert "DRAG INTERACTION LOADING" in initial_scene
    assert "GREEN - WITHIN DEMO ZONE" in initial_scene
    assert 'addEventListener("pointerdown"' in initial_scene
    assert 'addEventListener("pointermove"' in initial_scene
    assert "perspective: 1050px" in initial_scene
    assert "rotateX(" in initial_scene
    assert "rotateY(" in initial_scene
    assert 'tabindex="0"' in initial_scene
    assert 'addEventListener("keydown"' in initial_scene
    assert "pitch < threshold" in initial_scene

    app.slider[0].set_value(30).run()
    boundary_scene = _scene_document(app)
    assert 'data-initial-zone="green"' in boundary_scene

    app.slider[0].set_value(31).run()
    threshold_scene = _scene_document(app)

    assert 'data-initial-zone="danger"' in threshold_scene
    assert "RED - DEMO THRESHOLD CROSSED" in threshold_scene


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


def test_submitted_warning_status_renders_opt_in_demo_audio():
    app = _app_test()
    app.slider[0].set_value(35).run()
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
