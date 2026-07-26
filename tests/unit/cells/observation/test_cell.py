"""Unit tests for C-001 Observation Cell."""

from __future__ import annotations

from datetime import UTC, datetime

import cv2
import numpy as np
import pytest

from pcai.cells.observation import OpenCvObservationCell, RegisterFrame
from pcai.shared.errors import InvalidImageError
from pcai.shared.hashing import sha256_hex
from pcai.shared.identifiers import FrameId


def _encoded_png_bytes() -> bytes:
    image = np.zeros((24, 32, 3), dtype=np.uint8)
    image[6:18, 8:24] = (255, 255, 255)
    encoded, buffer = cv2.imencode(".png", image)
    assert encoded
    return buffer.tobytes()


def _command(*, image_bytes: bytes | None = None) -> RegisterFrame:
    return RegisterFrame(
        frame_id=FrameId("frame-001"),
        image_bytes=_encoded_png_bytes() if image_bytes is None else image_bytes,
        source_name="unit-test-camera",
        captured_at_utc=datetime(2026, 7, 26, 18, 0, tzinfo=UTC),
        camera_configuration_hash="camera-config-v1",
        calibration_version="calibration-v1",
    )


def test_register_returns_immutable_frame_metadata() -> None:
    command = _command()

    observation = OpenCvObservationCell().register(command)

    assert observation.frame_id == FrameId("frame-001")
    assert observation.width_px == 32
    assert observation.height_px == 24
    assert observation.channels == 3
    assert observation.dtype_name == "uint8"
    assert observation.object_sha256 == sha256_hex(command.image_bytes)


def test_register_is_deterministic_for_identical_bytes() -> None:
    command = _command()
    cell = OpenCvObservationCell()

    first = cell.register(command)
    second = cell.register(command)

    assert first == second


def test_register_rejects_empty_image_bytes() -> None:
    with pytest.raises(InvalidImageError) as error:
        OpenCvObservationCell().register(_command(image_bytes=b""))

    assert error.value.code == "FRAME_BYTES_EMPTY"


def test_register_rejects_undecodable_bytes() -> None:
    with pytest.raises(InvalidImageError) as error:
        OpenCvObservationCell().register(_command(image_bytes=b"not-an-image"))

    assert error.value.code == "FRAME_DECODE_FAILED"
