"""
P.C.A.I. — C-002 Frame Quality Cell contracts.

These immutable contracts define deterministic frame-quality assessment.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from pcai.shared.identifiers import FrameId


class QualityStatus(StrEnum):
    PASS = "PASS"
    REQUIRE_RECAPTURE = "REQUIRE_RECAPTURE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCK = "BLOCK"


class CheckStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class FrameQualityConfiguration:
    minimum_width_px: int
    minimum_height_px: int
    minimum_focus_score: float
    maximum_dark_pixel_ratio: float
    maximum_bright_pixel_ratio: float
    maximum_glare_pixel_ratio: float
    dark_pixel_threshold: int = 10
    bright_pixel_threshold: int = 245
    glare_value_threshold: int = 245
    glare_saturation_threshold: int = 25


@dataclass(frozen=True, slots=True)
class FrameQualityInput:
    frame_id: FrameId
    image_bgr: np.ndarray
    configuration: FrameQualityConfiguration


@dataclass(frozen=True, slots=True)
class QualityCheck:
    name: str
    status: CheckStatus
    measured_value: float
    threshold: float
    comparison: str
    unit: str


@dataclass(frozen=True, slots=True)
class FrameQualityAssessment:
    frame_id: FrameId
    status: QualityStatus
    checks: tuple[QualityCheck, ...]
    reason_codes: tuple[str, ...]
    required_action: str | None
