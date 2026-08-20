"""Unit tests for C-004 Candidate Observation Cell."""

from __future__ import annotations

from uuid import uuid4

import cv2
import numpy as np

from pcai.cells.candidate_observation import (
    CandidateConfiguration,
    CandidateObservationInput,
    CandidateStatus,
    DeterministicCandidateObservationCell,
    ForegroundPolarity,
)
from pcai.shared.identifiers import FrameId


def _configuration() -> CandidateConfiguration:
    return CandidateConfiguration(
        foreground_threshold=200,
        morphology_kernel_px=3,
        minimum_area_mm2=20.0,
        maximum_single_area_mm2=500.0,
        maximum_supported_area_mm2=2_000.0,
        minimum_solidity_single=0.85,
        touching_area_multiplier=1.25,
    )


def _input(image: np.ndarray) -> CandidateObservationInput:
    return CandidateObservationInput(
        frame_id=FrameId(str(uuid4())),
        canonical_tray_bgr=image,
        tray_mask=np.full(image.shape[:2], 255, dtype=np.uint8),
        pixels_per_mm_x=1.0,
        pixels_per_mm_y=1.0,
        configuration=_configuration(),
    )


def test_observes_three_isolated_candidates() -> None:
    image = np.full((200, 300, 3), 255, dtype=np.uint8)
    for centre in ((60, 70), (150, 70), (240, 70)):
        cv2.circle(image, centre, 12, (40, 40, 40), -1)

    result = DeterministicCandidateObservationCell().observe(_input(image))

    assert len(result.candidates) == 3
    assert all(candidate.status is CandidateStatus.SINGLE_CANDIDATE for candidate in result.candidates)
    assert [candidate.candidate_id for candidate in result.candidates] == [
        "candidate-0001",
        "candidate-0002",
        "candidate-0003",
    ]


def test_observes_light_tablets_on_a_dark_canonical_tray() -> None:
    image = np.zeros((200, 300, 3), dtype=np.uint8)
    for centre in ((60, 70), (150, 70), (240, 70)):
        cv2.circle(image, centre, 12, (240, 240, 240), -1)

    input_ = _input(image)
    input_ = CandidateObservationInput(
        frame_id=input_.frame_id,
        canonical_tray_bgr=input_.canonical_tray_bgr,
        tray_mask=input_.tray_mask,
        pixels_per_mm_x=input_.pixels_per_mm_x,
        pixels_per_mm_y=input_.pixels_per_mm_y,
        configuration=CandidateConfiguration(
            foreground_threshold=200,
            morphology_kernel_px=3,
            minimum_area_mm2=20.0,
            maximum_single_area_mm2=500.0,
            maximum_supported_area_mm2=2_000.0,
            minimum_solidity_single=0.85,
            touching_area_multiplier=1.25,
            foreground_polarity=ForegroundPolarity.LIGHT_ON_DARK,
        ),
    )

    result = DeterministicCandidateObservationCell().observe(input_)

    assert len(result.candidates) == 3
    assert all(candidate.status is CandidateStatus.SINGLE_CANDIDATE for candidate in result.candidates)


def test_marks_border_intersection_as_partial_object() -> None:
    image = np.full((200, 300, 3), 255, dtype=np.uint8)
    cv2.circle(image, (2, 80), 15, (40, 40, 40), -1)

    result = DeterministicCandidateObservationCell().observe(_input(image))

    assert len(result.candidates) == 1
    assert result.candidates[0].status is CandidateStatus.PARTIAL_OBJECT


def test_marks_large_region_as_touching() -> None:
    image = np.full((200, 300, 3), 255, dtype=np.uint8)
    cv2.ellipse(image, (150, 100), (25, 14), 0, 0, 360, (40, 40, 40), -1)

    result = DeterministicCandidateObservationCell().observe(_input(image))

    assert len(result.candidates) == 1
    assert result.candidates[0].status is CandidateStatus.TOUCHING_REGION


def test_candidate_observation_is_deterministic() -> None:
    image = np.full((200, 300, 3), 255, dtype=np.uint8)
    cv2.circle(image, (80, 80), 12, (40, 40, 40), -1)
    input_ = _input(image)
    cell = DeterministicCandidateObservationCell()

    first = cell.observe(input_)
    second = cell.observe(input_)

    assert [candidate.candidate_id for candidate in first.candidates] == [
        candidate.candidate_id for candidate in second.candidates
    ]
    assert np.array_equal(first.foreground_mask, second.foreground_mask)
