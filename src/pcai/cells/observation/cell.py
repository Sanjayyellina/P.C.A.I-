"""
P.C.A.I. — C-001 Observation Cell.

Mission
-------
Register trustworthy image observations.

Authority
---------
May decode image bytes, validate supported structure, hash the original bytes,
and emit immutable FrameObservation metadata.

Prohibited
----------
Must not assess frame quality, detect pills, count pills, identify medicine, or
advance workflow state.
"""

from __future__ import annotations

from typing import Final, Protocol

import cv2
import numpy as np

from pcai.cells.observation.contracts import FrameObservation, RegisterFrame
from pcai.shared.errors import InvalidImageError, UnsupportedImageError
from pcai.shared.hashing import sha256_hex

SUPPORTED_CHANNEL_COUNT: Final[int] = 3
MINIMUM_IMAGE_DIMENSION_PX: Final[int] = 1


class ObservationCell(Protocol):
    """Public C-001 capability contract."""

    def register(self, command: RegisterFrame) -> FrameObservation:
        """Validate and register one immutable frame observation."""


class OpenCvObservationCell:
    """OpenCV-backed deterministic implementation of C-001."""

    def register(self, command: RegisterFrame) -> FrameObservation:
        if not command.image_bytes:
            raise InvalidImageError(
                code="FRAME_BYTES_EMPTY",
                message="The captured frame contains no image bytes.",
            )

        encoded = np.frombuffer(command.image_bytes, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)

        if image is None:
            raise InvalidImageError(
                code="FRAME_DECODE_FAILED",
                message="The captured frame could not be decoded as an approved image.",
            )

        if image.ndim != 3:
            raise UnsupportedImageError(
                code="FRAME_DIMENSIONS_UNSUPPORTED",
                message="The decoded frame does not have the required image dimensions.",
            )

        height_px, width_px, channels = image.shape

        if width_px < MINIMUM_IMAGE_DIMENSION_PX or height_px < MINIMUM_IMAGE_DIMENSION_PX:
            raise UnsupportedImageError(
                code="FRAME_RESOLUTION_UNSUPPORTED",
                message="The decoded frame has an unsupported resolution.",
            )

        if channels != SUPPORTED_CHANNEL_COUNT:
            raise UnsupportedImageError(
                code="FRAME_CHANNELS_UNSUPPORTED",
                message="The decoded frame does not use the supported colour channel count.",
            )

        return FrameObservation(
            observation_id=command.observation_id,
            frame_id=command.frame_id,
            object_sha256=sha256_hex(command.image_bytes),
            source_name=command.source_name,
            captured_at_utc=command.captured_at_utc,
            width_px=width_px,
            height_px=height_px,
            channels=channels,
            dtype_name=str(image.dtype),
            camera_configuration_hash=command.camera_configuration_hash,
            calibration_version=command.calibration_version,
        )
