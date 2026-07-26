"""
P.C.A.I. — C-001 Observation Cell.

Mission
-------
Register trustworthy physical observations from captured image bytes.

Authority
---------
May validate, decode, measure and hash a captured frame.

Prohibited
----------
Must not count pills, identify medicine or mutate prior observations.
"""

from __future__ import annotations

from typing import Final

import cv2
import numpy as np
from numpy.typing import NDArray

from pcai.cells.observation.contracts import FrameObservation, RegisterFrame
from pcai.shared.errors import InvalidImageError
from pcai.shared.hashing import sha256_hex

EXPECTED_CHANNEL_COUNT: Final = 3
MINIMUM_DIMENSION_PX: Final = 1


class OpenCvObservationCell:
    """Deterministic OpenCV implementation of C-001."""

    def register(self, command: RegisterFrame) -> FrameObservation:
        """Validate and register one immutable frame observation."""

        image = self._decode_image(command.image_bytes)
        height_px, width_px, channels = image.shape

        if width_px < MINIMUM_DIMENSION_PX or height_px < MINIMUM_DIMENSION_PX:
            raise InvalidImageError(
                code="FRAME_RESOLUTION_UNSUPPORTED",
                message="The captured frame has an unsupported resolution.",
            )

        if channels != EXPECTED_CHANNEL_COUNT:
            raise InvalidImageError(
                code="FRAME_CHANNELS_UNSUPPORTED",
                message="The captured frame does not use the approved colour format.",
            )

        return FrameObservation(
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

    @staticmethod
    def _decode_image(image_bytes: bytes) -> NDArray[np.uint8]:
        if not image_bytes:
            raise InvalidImageError(
                code="FRAME_BYTES_EMPTY",
                message="The captured frame contains no image bytes.",
            )

        encoded = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)

        if image is None:
            raise InvalidImageError(
                code="FRAME_DECODE_FAILED",
                message="The captured frame could not be decoded as an approved image.",
            )

        return image
