"""
P.C.A.I. — C-004 Candidate Observation Cell contracts.

A candidate is an observed foreground region, not yet an accepted pill.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from pcai.shared.identifiers import FrameId


class CandidateStatus(StrEnum):
    SINGLE_CANDIDATE = "SINGLE_CANDIDATE"
    TOUCHING_REGION = "TOUCHING_REGION"
    POSSIBLE_STACK = "POSSIBLE_STACK"
    FOREIGN_OBJECT = "FOREIGN_OBJECT"
    PARTIAL_OBJECT = "PARTIAL_OBJECT"
    ARTIFACT = "ARTIFACT"
    UNKNOWN = "UNKNOWN"


class ForegroundPolarity(StrEnum):
    """Expected tablet contrast within the already-canonical tray image."""

    DARK_ON_LIGHT = "DARK_ON_LIGHT"
    LIGHT_ON_DARK = "LIGHT_ON_DARK"


@dataclass(frozen=True, slots=True)
class CandidateConfiguration:
    foreground_threshold: int
    morphology_kernel_px: int
    minimum_area_mm2: float
    maximum_single_area_mm2: float
    maximum_supported_area_mm2: float
    minimum_solidity_single: float
    touching_area_multiplier: float
    foreground_polarity: ForegroundPolarity = ForegroundPolarity.DARK_ON_LIGHT


@dataclass(frozen=True, slots=True)
class CandidateObservationInput:
    frame_id: FrameId
    canonical_tray_bgr: np.ndarray
    tray_mask: np.ndarray
    pixels_per_mm_x: float
    pixels_per_mm_y: float
    configuration: CandidateConfiguration


@dataclass(frozen=True, slots=True)
class CandidateObservation:
    candidate_id: str
    contour: np.ndarray
    bounding_box_xywh: tuple[int, int, int, int]
    centroid_xy: tuple[float, float]
    area_px2: float
    area_mm2: float
    perimeter_px: float
    circularity: float
    solidity: float
    aspect_ratio: float
    touches_tray_border: bool
    status: CandidateStatus
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateSet:
    frame_id: FrameId
    foreground_mask: np.ndarray
    candidates: tuple[CandidateObservation, ...]
