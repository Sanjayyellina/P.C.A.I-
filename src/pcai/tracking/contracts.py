from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TrackState(StrEnum):
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    LOST = "lost"
    REMOVED = "removed"


class CountPublicationDecision(StrEnum):
    HOLD = "hold"
    PUBLISH = "publish"
    CLEAR = "clear"


@dataclass(frozen=True, slots=True)
class TrackObservation:
    frame_sequence: int
    fused_candidate_id: int
    centroid_xy: tuple[float, float]
    bounding_box_xyxy: tuple[float, float, float, float]
    estimated_count: int
    confidence: float

    def __post_init__(self) -> None:
        if self.frame_sequence < 0:
            raise ValueError("frame_sequence cannot be negative.")
        if self.fused_candidate_id < 0:
            raise ValueError("fused_candidate_id cannot be negative.")
        if self.estimated_count < 0:
            raise ValueError("estimated_count cannot be negative.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1.")
        x1, y1, x2, y2 = self.bounding_box_xyxy
        if x2 < x1 or y2 < y1:
            raise ValueError("bounding_box_xyxy must satisfy x2 >= x1 and y2 >= y1.")


@dataclass(frozen=True, slots=True)
class TrackedObject:
    track_id: int
    state: TrackState
    first_frame_sequence: int
    last_frame_sequence: int
    age_frames: int
    hit_count: int
    missed_frames: int
    centroid_xy: tuple[float, float]
    bounding_box_xyxy: tuple[float, float, float, float]
    estimated_count: int
    confidence: float
    count_history: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.track_id < 0:
            raise ValueError("track_id cannot be negative.")
        if self.first_frame_sequence < 0 or self.last_frame_sequence < 0:
            raise ValueError("frame sequences cannot be negative.")
        if self.last_frame_sequence < self.first_frame_sequence:
            raise ValueError("last_frame_sequence cannot precede first_frame_sequence.")
        for field_name in ("age_frames", "hit_count", "missed_frames"):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} cannot be negative.")
        if self.estimated_count < 0:
            raise ValueError("estimated_count cannot be negative.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class TrackingFrameResult:
    frame_sequence: int
    tracks: tuple[TrackedObject, ...]
    active_tracks: int
    confirmed_tracks: int
    created_tracks: int
    removed_track_ids: tuple[int, ...]
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.frame_sequence < 0:
            raise ValueError("frame_sequence cannot be negative.")
        for field_name in (
            "active_tracks",
            "confirmed_tracks",
            "created_tracks",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} cannot be negative.")


@dataclass(frozen=True, slots=True)
class StableCountResult:
    frame_sequence: int
    observed_count: int
    stable_count: int | None
    confidence: float
    consecutive_stable_frames: int
    decision: CountPublicationDecision
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.frame_sequence < 0:
            raise ValueError("frame_sequence cannot be negative.")
        if self.observed_count < 0:
            raise ValueError("observed_count cannot be negative.")
        if self.stable_count is not None and self.stable_count < 0:
            raise ValueError("stable_count cannot be negative.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1.")
        if self.consecutive_stable_frames < 0:
            raise ValueError("consecutive_stable_frames cannot be negative.")
