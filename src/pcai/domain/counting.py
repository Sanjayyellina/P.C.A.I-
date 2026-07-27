"""P.C.A.I. immutable counting-domain value objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pcai.shared.identifiers import FrameId


class CountStatus(StrEnum):
    COUNTED = "COUNTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class ClassicalCountObservation:
    frame_id: FrameId
    status: CountStatus
    candidate_count: int | None
    accepted_candidate_ids: tuple[str, ...]
    excluded_candidate_ids: tuple[str, ...]
    touching_region_ids: tuple[str, ...]
    unknown_region_ids: tuple[str, ...]
    partial_region_ids: tuple[str, ...]
    artifact_region_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
