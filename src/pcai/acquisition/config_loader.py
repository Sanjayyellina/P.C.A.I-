from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2

from .contracts import CameraConfig


_BACKENDS: dict[str, int] = {
    "any": cv2.CAP_ANY,
    "v4l2": cv2.CAP_V4L2,
    "gstreamer": cv2.CAP_GSTREAMER,
    "ffmpeg": cv2.CAP_FFMPEG,
}


def load_camera_config(path: str | Path) -> CameraConfig:
    """Load and validate a camera profile from JSON."""

    profile_path = Path(path)
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"Camera profile does not exist: {profile_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Camera profile is invalid JSON: {profile_path}") from error

    if not isinstance(payload, dict):
        raise ValueError("Camera profile root must be a JSON object.")

    backend = _parse_backend(payload.pop("backend", None))
    source = payload.get("source", 0)
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    values: dict[str, Any] = {
        "source": source,
        "width_px": payload.get("width_px", 1280),
        "height_px": payload.get("height_px", 720),
        "fps": payload.get("fps", 30.0),
        "backend": backend,
        "buffer_size": payload.get("buffer_size", 2),
        "fourcc": payload.get("fourcc", "MJPG"),
        "camera_id": payload.get("camera_id", "camera-0"),
    }
    return CameraConfig(**values)


def _parse_backend(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        raise ValueError("backend must be a string, integer, or null.")

    key = value.strip().lower()
    try:
        return _BACKENDS[key]
    except KeyError as error:
        supported = ", ".join(sorted(_BACKENDS))
        raise ValueError(
            f"Unsupported camera backend {value!r}; supported: {supported}."
        ) from error
