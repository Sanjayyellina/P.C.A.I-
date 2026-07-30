from __future__ import annotations

import json

import cv2
import pytest

from pcai.acquisition.config_loader import load_camera_config


def test_loads_usb_profile(tmp_path) -> None:
    profile = tmp_path / "camera.json"
    profile.write_text(
        json.dumps(
            {
                "camera_id": "usb-1",
                "source": "0",
                "backend": "v4l2",
                "width_px": 1920,
                "height_px": 1080,
                "fps": 30.0,
                "buffer_size": 2,
                "fourcc": "MJPG",
            }
        ),
        encoding="utf-8",
    )

    config = load_camera_config(profile)

    assert config.camera_id == "usb-1"
    assert config.source == 0
    assert config.backend == cv2.CAP_V4L2
    assert config.width_px == 1920
    assert config.height_px == 1080
    assert config.fps == 30.0


def test_loads_gstreamer_pipeline(tmp_path) -> None:
    profile = tmp_path / "camera.json"
    pipeline = "nvarguscamerasrc ! videoconvert ! appsink"
    profile.write_text(
        json.dumps(
            {
                "camera_id": "csi-0",
                "source": pipeline,
                "backend": "gstreamer",
                "fourcc": None,
            }
        ),
        encoding="utf-8",
    )

    config = load_camera_config(profile)

    assert config.source == pipeline
    assert config.backend == cv2.CAP_GSTREAMER
    assert config.fourcc is None


def test_rejects_unknown_backend(tmp_path) -> None:
    profile = tmp_path / "camera.json"
    profile.write_text(
        json.dumps({"backend": "unknown"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported camera backend"):
        load_camera_config(profile)


def test_rejects_invalid_json(tmp_path) -> None:
    profile = tmp_path / "camera.json"
    profile.write_text("{not-json", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid JSON"):
        load_camera_config(profile)


def test_rejects_missing_profile(tmp_path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        load_camera_config(tmp_path / "missing.json")
