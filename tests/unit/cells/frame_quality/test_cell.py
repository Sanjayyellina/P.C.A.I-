"""Unit tests for C-002 Frame Quality Cell."""

from __future__ import annotations

from uuid import uuid4

import numpy as np

from pcai.cells.frame_quality import (
    DeterministicFrameQualityCell,
    FrameQualityConfiguration,
    FrameQualityInput,
    QualityStatus,
)
from pcai.shared.identifiers import FrameId


def _configuration(**overrides: float | int) -> FrameQualityConfiguration:
    values: dict[str, float | int] = {
        "minimum_width_px": 32,
        "minimum_height_px": 32,
        "minimum_focus_score": 1.0,
        "maximum_dark_pixel_ratio": 0.95,
        "maximum_bright_pixel_ratio": 0.95,
        "maximum_glare_pixel_ratio": 0.95,
    }
    values.update(overrides)
    return FrameQualityConfiguration(**values)


def _frame_id() -> FrameId:
    return FrameId(str(uuid4()))


def test_passes_supported_sharp_frame() -> None:
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    image[:, ::2] = 180
    cell = DeterministicFrameQualityCell()

    assessment = cell.assess(
        FrameQualityInput(
            frame_id=_frame_id(),
            image_bgr=image,
            configuration=_configuration(),
        )
    )

    assert assessment.status is QualityStatus.PASS
    assert assessment.reason_codes == ()
    assert assessment.required_action is None


def test_requires_recapture_for_blurred_frame() -> None:
    image = np.full((64, 64, 3), 100, dtype=np.uint8)
    cell = DeterministicFrameQualityCell()

    assessment = cell.assess(
        FrameQualityInput(
            frame_id=_frame_id(),
            image_bgr=image,
            configuration=_configuration(minimum_focus_score=10.0),
        )
    )

    assert assessment.status is QualityStatus.REQUIRE_RECAPTURE
    assert "FRAME_OUT_OF_FOCUS" in assessment.reason_codes


def test_requires_recapture_for_small_resolution() -> None:
    image = np.zeros((16, 16, 3), dtype=np.uint8)
    image[:, ::2] = 180
    cell = DeterministicFrameQualityCell()

    assessment = cell.assess(
        FrameQualityInput(
            frame_id=_frame_id(),
            image_bgr=image,
            configuration=_configuration(),
        )
    )

    assert assessment.status is QualityStatus.REQUIRE_RECAPTURE
    assert "FRAME_WIDTH_TOO_SMALL" in assessment.reason_codes
    assert "FRAME_HEIGHT_TOO_SMALL" in assessment.reason_codes


def test_repeated_assessment_is_deterministic() -> None:
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    image[:, ::2] = 180
    input_ = FrameQualityInput(
        frame_id=_frame_id(),
        image_bgr=image,
        configuration=_configuration(),
    )
    cell = DeterministicFrameQualityCell()

    assert cell.assess(input_) == cell.assess(input_)
