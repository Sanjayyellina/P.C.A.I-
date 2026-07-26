"""
P.C.A.I. — C-001 Observation Cell contracts.

Mission
-------
Define immutable input and output contracts for trustworthy frame registration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pcai.shared.identifiers import FrameId


@dataclass(frozen=True, slots=True)
class RegisterFrame:
    """Command requesting registration of one captured frame."""

    frame_id: FrameId
    image_bytes: bytes
    source_name: str
    captured_at_utc: datetime
    camera_configuration_hash: str
    calibration_version: str

    def __post_init__(self) -> None:
        if not self.source_name.strip():
            raise ValueError("source_name must not be empty")
        if self.captured_at_utc.tzinfo is None:
            raise ValueError("captured_at_utc must be timezone-aware")
        if not self.camera_configuration_hash.strip():
            raise ValueError("camera_configuration_hash must not be empty")
        if not self.calibration_version.strip():
            raise ValueError("calibration_version must not be empty")


@dataclass(frozen=True, slots=True)
class FrameObservation:
    """Immutable metadata describing one successfully decoded frame."""

    frame_id: FrameId
    object_sha256: str
    source_name: str
    captured_at_utc: datetime
    width_px: int
    height_px: int
    channels: int
    dtype_name: str
    camera_configuration_hash: str
    calibration_version: str
