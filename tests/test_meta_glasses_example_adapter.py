import pytest

from integrations.oem.meta_glasses import MetaGlassesExampleAdapter


def test_maps_synthetic_orientation_to_shared_telemetry_frame():
    frame = MetaGlassesExampleAdapter().to_telemetry_frame(
        {
            "user_id": "synthetic-demo-user",
            "input_string": "",
            "orientation": {
                "pitch_degrees": -4.5,
                "yaw_degrees": 3.2,
                "roll_degrees": 0.0,
            },
            "ignored_media_reference": "not-copied",
        }
    )

    assert frame.user_id == "synthetic-demo-user"
    assert frame.input_string == ""
    assert frame.pitch == -4.5
    assert frame.yaw == 3.2
    assert frame.roll == 0.0
    assert frame.oem_platform == "meta_glasses_example"
    assert not hasattr(frame, "ignored_media_reference")


def test_rejects_missing_orientation_instead_of_assuming_neutral_values():
    with pytest.raises(ValueError, match="orientation"):
        MetaGlassesExampleAdapter().to_telemetry_frame(
            {"user_id": "synthetic-demo-user", "input_string": ""}
        )


def test_rejects_incomplete_orientation():
    with pytest.raises(ValueError, match="roll_degrees"):
        MetaGlassesExampleAdapter().to_telemetry_frame(
            {
                "user_id": "synthetic-demo-user",
                "input_string": "",
                "orientation": {
                    "pitch_degrees": 1.0,
                    "yaw_degrees": 2.0,
                },
            }
        )
