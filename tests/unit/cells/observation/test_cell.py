"""Unit tests for C-001 Observation Cell."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import cv2
import numpy as np
import pytest

from pcai.cells.observation import OpenCvObservationCell, RegisterFrame
from pcai.shared.errors import InvalidImageError
from pcai.shared.hashing import sha256_hex
from pcai.shared.identifiers import FrameId, ObservationId


def _encoded_png_bytes(*, width_px: int = 8, height_px: int = 6) -> bytes:
    image = np.zeros((height_px, width_px, 3), dtype=np.uint8)
    success, encoded = cv2.imencode(".png", image)
    assert success is True
    return encoded.tobytes()


def _valid_command(*, image_bytes: bytes | None = None) -> RegisterFrame:
    return RegisterFrame(
        observation_id=ObservationId(str(uuid4())),
        frame_id=FrameId(str(uuid4())),
        image_bytes=_encoded_png_bytes() if image_bytes is None else image_bytes,
        source_name="unit-test-camera",
        captured_at_utc=datetime(2026, 7, 26, 12, 0, tzinfo=UTC),
        camera_configuration_hash="camera-config-v1",
        calibration_version="calibration-v1",
    )


def test_registers_valid_frame_metadata_and_hash() -> None:
    command = _valid_command()
    cell = OpenCvObservationCell()

    observation = cell.register(command)

    assert observation.observation_id == command.observation_id
    assert observation.frame_id == command.frame_id
    assert observation.width_px == 8
    assert observation.height_px == 6
    assert observation.channels == 3
    assert observation.dtype_name == "uint8"
    assert observation.object_sha256 == sha256_hex(command.image_bytes)


def test_repeated_registration_is_deterministic() -> None:
    command = _valid_command()
    cell = OpenCvObservationCell()

    first = cell.register(command)
    second = cell.register(command)

    assert first == second


def test_rejects_empty_image_bytes() -> None:
    cell = OpenCvObservationCell()

    with pytest.raises(InvalidImageError) as error:
        cell.register(_valid_command(image_bytes=b""))

    assert error.value.code == "FRAME_BYTES_EMPTY"


def test_rejects_undecodable_image_bytes() -> None:
    cell = OpenCvObservationCell()

    with pytest.raises(InvalidImageError) as error:
        cell.register(_valid_command(image_bytes=b"not-an-image"))

    assert error.value.code == "FRAME_DECODE_FAILED"
