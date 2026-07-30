from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HypothesisDecision(StrEnum):
    ACCEPT = "accept"
    REVIEW = "review"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class CountProbability:
    count: int
    probability: float

    def __post_init__(self) -> None:
        if self.count < 0:
            raise ValueError("count cannot be negative.")
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class TabletHypothesis:
    candidate_id: int
    estimated_count: int
    confidence: float
    decision: HypothesisDecision
    probabilities: tuple[CountProbability, ...]
    reason_codes: tuple[str, ...]
    split_region_count: int | None = None

    def __post_init__(self) -> None:
        if self.candidate_id < 0:
            raise ValueError("candidate_id cannot be negative.")
        if self.estimated_count < 0:
            raise ValueError("estimated_count cannot be negative.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1.")
        if self.split_region_count is not None and self.split_region_count < 0:
            raise ValueError("split_region_count cannot be negative.")


@dataclass(frozen=True, slots=True)
class ClassicalCountEstimate:
    total_count: int
    confidence: float
    hypotheses: tuple[TabletHypothesis, ...]
    accepted_candidates: int
    review_candidates: int
    rejected_candidates: int
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.total_count < 0:
            raise ValueError("total_count cannot be negative.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1.")
        for name in (
            "accepted_candidates",
            "review_candidates",
            "rejected_candidates",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative.")
