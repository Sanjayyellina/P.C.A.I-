"""First deterministic C-004 to C-005 exact-count integration test."""

from __future__ import annotations

from uuid import uuid4

import cv2
import numpy as np

from pcai.cells.candidate_observation import (
    CandidateConfiguration,
    CandidateObservationInput,
    DeterministicCandidateObservationCell,
)
from pcai.cells.classical_counting import (
    ClassicalCountingConfiguration,
    ClassicalCountingInput,
    CountStatus,
    StrictClassicalCountingCell,
)
from pcai.shared.identifiers import FrameId


def test_counts_ten_isolated_synthetic_tablets_exactly() -> None:
    image = np.full((300, 500, 3), 255, dtype=np.uint8)
    centres = [
        (60, 70),
        (150, 70),
        (240, 70),
        (330, 70),
        (420, 70),
        (60, 190),
        (150, 190),
        (240, 190),
        (330, 190),
        (420, 190),
    ]
    for centre in centres:
        cv2.circle(image, centre, 14, (40, 40, 40), -1)

    frame_id = FrameId(str(uuid4()))
    candidates = DeterministicCandidateObservationCell().observe(
        CandidateObservationInput(
            frame_id=frame_id,
            canonical_tray_bgr=image,
            tray_mask=np.full(image.shape[:2], 255, dtype=np.uint8),
            pixels_per_mm_x=1.0,
            pixels_per_mm_y=1.0,
            configuration=CandidateConfiguration(
                foreground_threshold=200,
                morphology_kernel_px=3,
                minimum_area_mm2=20.0,
                maximum_single_area_mm2=1_000.0,
                maximum_supported_area_mm2=4_000.0,
                minimum_solidity_single=0.85,
                touching_area_multiplier=1.25,
            ),
        )
    )

    result = StrictClassicalCountingCell().count(
        ClassicalCountingInput(
            frame_id=frame_id,
            candidate_set=candidates,
            configuration=ClassicalCountingConfiguration(
                allow_touching_regions=False,
                reject_unknown_regions=True,
                reject_partial_objects=True,
                reject_possible_stacks=True,
            ),
        )
    )

    assert result.status is CountStatus.COUNTED
    assert result.candidate_count == 10
    assert len(result.accepted_candidate_ids) == 10
    assert result.reason_codes == ()
