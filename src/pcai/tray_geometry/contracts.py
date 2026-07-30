from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class TrayCorners:
    top_left: tuple[float, float]
    top_right: tuple[float, float]
    bottom_right: tuple[float, float]
    bottom_left: tuple[float, float]


@dataclass(frozen=True, slots=True)
class TrayGeometry:
    corners: TrayCorners
    perspective_matrix: np.ndarray
    inverse_perspective_matrix: np.ndarray
    normalized_width_px: int
    normalized_height_px: int
    confidence: float


@dataclass(frozen=True, slots=True)
class TrayDetectionResult:
    tray_found: bool
    geometry: TrayGeometry | None
    reason: str | None
