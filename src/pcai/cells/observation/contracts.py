"""
P.C.A.I. — C-001 Observation Cell contracts.

These immutable contracts define the public Register Observation capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pcai.shared.identifiers import FrameId, ObservationId


@dataclass(frozen=True, slots=True)
class RegisterFrame:
    """Command to register one captured frame as an immutable observation."""

    observation_id: ObservationId
    frame_id: FrameId
    image_bytes: bytes
    source_name: str
    captured_at_utc: datetime
    camera_configuration_hash: str
    calibration_version: str


@dataclass(frozen=True, slots=True)
class FrameObservation:
    """Immutable metadata derived from one successfully decoded frame."""

    observation_id: ObservationId
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
