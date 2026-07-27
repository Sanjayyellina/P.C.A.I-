"""
P.C.A.I. — C-003 Tray Geometry Cell contracts.

These immutable contracts describe the conversion from camera space into a
canonical tray coordinate system.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from pcai.shared.identifiers import FrameId


class GeometryStatus(StrEnum):
    PASS = "PASS"
    REQUIRE_RECAPTURE = "REQUIRE_RECAPTURE"
    REQUIRE_RECALIBRATION = "REQUIRE_RECALIBRATION"


@dataclass(frozen=True, slots=True)
class TrayGeometryConfiguration:
    canonical_width_px: int
    canonical_height_px: int
    tray_width_mm: float
    tray_height_mm: float
    maximum_reprojection_error_px: float
    minimum_marker_count: int = 4


@dataclass(frozen=True, slots=True)
class TrayGeometryInput:
    frame_id: FrameId
    image_bgr: np.ndarray
    source_points_xy: np.ndarray
    destination_points_xy: np.ndarray
    configuration: TrayGeometryConfiguration


@dataclass(frozen=True, slots=True)
class TrayGeometryFacts:
    frame_id: FrameId
    status: GeometryStatus
    canonical_tray_bgr: np.ndarray | None
    tray_mask: np.ndarray | None
    homography: np.ndarray | None
    reprojection_error_px: float | None
    pixels_per_mm_x: float | None
    pixels_per_mm_y: float | None
    reason_codes: tuple[str, ...]
