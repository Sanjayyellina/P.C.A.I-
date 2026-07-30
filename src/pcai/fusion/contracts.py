from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FusionDecision(StrEnum):
    ACCEPT = "accept"
    WAIT = "wait"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class CandidateAssociation:
    classical_candidate_id: int | None
    yolo_instance_id: int | None
    iou: float
    centroid_distance_px: float | None
    matched: bool

    def __post_init__(self) -> None:
        if self.classical_candidate_id is None and self.yolo_instance_id is None:
            raise ValueError("At least one candidate identifier must be present.")
        if not 0.0 <= self.iou <= 1.0:
            raise ValueError("iou must be between 0 and 1.")
        if self.centroid_distance_px is not None and self.centroid_distance_px < 0:
            raise ValueError("centroid_distance_px cannot be negative.")


@dataclass(frozen=True, slots=True)
class FusedCandidateHypothesis:
    identifier: int
    classical_candidate_id: int | None
    yolo_instance_id: int | None
    estimated_count: int
    confidence: float
    decision: FusionDecision
    classical_confidence: float | None
    yolo_confidence: float | None
    agreement_score: float
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.identifier < 0:
            raise ValueError("identifier cannot be negative.")
        if self.estimated_count < 0:
            raise ValueError("estimated_count cannot be negative.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1.")
        if self.classical_confidence is not None and not 0.0 <= self.classical_confidence <= 1.0:
            raise ValueError("classical_confidence must be between 0 and 1.")
        if self.yolo_confidence is not None and not 0.0 <= self.yolo_confidence <= 1.0:
            raise ValueError("yolo_confidence must be between 0 and 1.")
        if not 0.0 <= self.agreement_score <= 1.0:
            raise ValueError("agreement_score must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class FusedCountEstimate:
    frame_sequence: int
    camera_id: str
    total_count: int
    confidence: float
    decision: FusionDecision
    candidates: tuple[FusedCandidateHypothesis, ...]
    matched_pairs: int
    unmatched_classical: int
    unmatched_yolo: int
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.frame_sequence < 0:
            raise ValueError("frame_sequence cannot be negative.")
        if self.total_count < 0:
            raise ValueError("total_count cannot be negative.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1.")
        for field_name in (
            "matched_pairs",
            "unmatched_classical",
            "unmatched_yolo",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} cannot be negative.")
