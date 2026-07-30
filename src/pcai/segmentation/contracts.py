from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class CandidateObservation:
    identifier: int
    mask: np.ndarray
    contour: np.ndarray
    centroid_xy: tuple[float, float]
    bounding_box_xywh: tuple[int, int, int, int]
    area_px2: float
    perimeter_px: float
    circularity: float
    solidity: float
    aspect_ratio: float
    mean_intensity: float


@dataclass(frozen=True, slots=True)
class SegmentationResult:
    binary_mask: np.ndarray
    candidates: tuple[CandidateObservation, ...]
    processing_time_ms: float
    confidence: float
