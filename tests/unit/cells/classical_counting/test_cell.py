"""Unit tests for C-005 Classical Counting Cell."""

from __future__ import annotations

from uuid import uuid4

import numpy as np

from pcai.cells.candidate_observation.contracts import (
    CandidateObservation,
    CandidateSet,
    CandidateStatus,
)
from pcai.cells.classical_counting import (
    ClassicalCountingConfiguration,
    ClassicalCountingInput,
    CountStatus,
    StrictClassicalCountingCell,
)
from pcai.shared.identifiers import FrameId


def _candidate(candidate_id: str, status: CandidateStatus) -> CandidateObservation:
    contour = np.array([[[0, 0]], [[1, 0]], [[1, 1]], [[0, 1]]], dtype=np.int32)
    return CandidateObservation(
        candidate_id=candidate_id,
        contour=contour,
        bounding_box_xywh=(0, 0, 2, 2),
        centroid_xy=(0.5, 0.5),
        area_px2=1.0,
        area_mm2=1.0,
        perimeter_px=4.0,
        circularity=0.78,
        solidity=1.0,
        aspect_ratio=1.0,
        touches_tray_border=False,
        status=status,
        reason_codes=(),
    )


def _input(*candidates: CandidateObservation) -> ClassicalCountingInput:
    frame_id = FrameId(str(uuid4()))
    return ClassicalCountingInput(
        frame_id=frame_id,
        candidate_set=CandidateSet(
            frame_id=frame_id,
            foreground_mask=np.zeros((4, 4), dtype=np.uint8),
            candidates=tuple(candidates),
        ),
        configuration=ClassicalCountingConfiguration(
            allow_touching_regions=False,
            reject_unknown_regions=True,
            reject_partial_objects=True,
            reject_possible_stacks=True,
        ),
    )


def test_counts_only_single_candidates_and_ignores_artifacts() -> None:
    result = StrictClassicalCountingCell().count(
        _input(
            _candidate("candidate-0001", CandidateStatus.SINGLE_CANDIDATE),
            _candidate("candidate-0002", CandidateStatus.SINGLE_CANDIDATE),
            _candidate("candidate-0003", CandidateStatus.ARTIFACT),
        )
    )

    assert result.status is CountStatus.COUNTED
    assert result.candidate_count == 2
    assert result.accepted_candidate_ids == ("candidate-0001", "candidate-0002")
    assert result.artifact_region_ids == ("candidate-0003",)


def test_requires_review_when_touching_region_is_present() -> None:
    result = StrictClassicalCountingCell().count(
        _input(
            _candidate("candidate-0001", CandidateStatus.SINGLE_CANDIDATE),
            _candidate("candidate-0002", CandidateStatus.TOUCHING_REGION),
        )
    )

    assert result.status is CountStatus.REVIEW_REQUIRED
    assert result.candidate_count is None
    assert result.accepted_candidate_ids == ("candidate-0001",)
    assert result.touching_region_ids == ("candidate-0002",)
    assert result.reason_codes == ("TOUCHING_REGIONS_PRESENT",)


def test_requires_review_for_unknown_partial_stack_and_foreign_object() -> None:
    result = StrictClassicalCountingCell().count(
        _input(
            _candidate("unknown", CandidateStatus.UNKNOWN),
            _candidate("partial", CandidateStatus.PARTIAL_OBJECT),
            _candidate("stack", CandidateStatus.POSSIBLE_STACK),
            _candidate("foreign", CandidateStatus.FOREIGN_OBJECT),
        )
    )

    assert result.status is CountStatus.REVIEW_REQUIRED
    assert result.reason_codes == (
        "UNKNOWN_REGIONS_PRESENT",
        "PARTIAL_OBJECTS_PRESENT",
        "POSSIBLE_STACKS_PRESENT",
        "FOREIGN_OBJECTS_PRESENT",
    )


def test_counting_is_deterministic() -> None:
    input_ = _input(
        _candidate("candidate-0001", CandidateStatus.SINGLE_CANDIDATE),
        _candidate("candidate-0002", CandidateStatus.SINGLE_CANDIDATE),
    )
    cell = StrictClassicalCountingCell()

    assert cell.count(input_) == cell.count(input_)
