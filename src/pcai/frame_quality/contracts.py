from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FrameQualityDecision(StrEnum):
    ACCEPT = "accept"
    WAIT = "wait"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class FrameQualityThresholds:
    minimum_focus_score: float = 80.0
    minimum_brightness: float = 45.0
    maximum_brightness: float = 215.0
    maximum_dark_clip_ratio: float = 0.20
    maximum_bright_clip_ratio: float = 0.08
    minimum_contrast: float = 25.0
    maximum_glare_ratio: float = 0.06
    maximum_motion_score: float = 18.0
    minimum_overall_score: float = 75.0

    def __post_init__(self) -> None:
        if self.minimum_focus_score < 0:
            raise ValueError("minimum_focus_score cannot be negative.")
        if not 0 <= self.minimum_brightness < self.maximum_brightness <= 255:
            raise ValueError("brightness thresholds must satisfy 0 <= min < max <= 255.")
        for field_name in (
            "maximum_dark_clip_ratio",
            "maximum_bright_clip_ratio",
            "maximum_glare_ratio",
        ):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1.")
        if self.minimum_contrast < 0:
            raise ValueError("minimum_contrast cannot be negative.")
        if self.maximum_motion_score < 0:
            raise ValueError("maximum_motion_score cannot be negative.")
        if not 0.0 <= self.minimum_overall_score <= 100.0:
            raise ValueError("minimum_overall_score must be between 0 and 100.")


@dataclass(frozen=True, slots=True)
class FrameQualityMetrics:
    focus_score: float
    mean_brightness: float
    contrast_score: float
    dark_clip_ratio: float
    bright_clip_ratio: float
    glare_ratio: float
    motion_score: float | None


@dataclass(frozen=True, slots=True)
class FrameQualityReport:
    frame_sequence: int
    camera_id: str
    metrics: FrameQualityMetrics
    overall_score: float
    decision: FrameQualityDecision
    reason_codes: tuple[str, ...]
    recommended_action: str | None

    @property
    def accepted(self) -> bool:
        return self.decision is FrameQualityDecision.ACCEPT
