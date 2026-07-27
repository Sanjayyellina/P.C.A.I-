"""
P.C.A.I. — C-002 Frame Quality Cell.

Mission
-------
Determine whether a registered frame is fit for downstream counting.

Authority
---------
May measure deterministic frame-quality metrics and return a workflow action.

Prohibited
----------
Must not detect pills, estimate counts, identify medicine, or override policy.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from pcai.cells.frame_quality.contracts import (
    CheckStatus,
    FrameQualityAssessment,
    FrameQualityInput,
    QualityCheck,
    QualityStatus,
)
from pcai.cells.frame_quality.metrics import (
    bright_pixel_ratio,
    dark_pixel_ratio,
    focus_score,
    glare_pixel_ratio,
)
from pcai.shared.errors import InvalidImageError


class FrameQualityCell(Protocol):
    """Public C-002 capability contract."""

    def assess(self, input_: FrameQualityInput) -> FrameQualityAssessment:
        """Assess whether one decoded BGR frame is suitable for counting."""


class DeterministicFrameQualityCell:
    """Deterministic OpenCV-backed implementation of C-002."""

    def assess(self, input_: FrameQualityInput) -> FrameQualityAssessment:
        self._validate_image(input_.image_bgr)

        checks = (
            self._minimum_width_check(input_),
            self._minimum_height_check(input_),
            self._focus_check(input_),
            self._dark_ratio_check(input_),
            self._bright_ratio_check(input_),
            self._glare_ratio_check(input_),
        )
        failed = tuple(check for check in checks if check.status is CheckStatus.FAIL)

        if not failed:
            return FrameQualityAssessment(
                frame_id=input_.frame_id,
                status=QualityStatus.PASS,
                checks=checks,
                reason_codes=(),
                required_action=None,
            )

        return FrameQualityAssessment(
            frame_id=input_.frame_id,
            status=QualityStatus.REQUIRE_RECAPTURE,
            checks=checks,
            reason_codes=tuple(self._reason_code(check.name) for check in failed),
            required_action="CORRECT_FRAME_AND_RECAPTURE",
        )

    @staticmethod
    def _validate_image(image_bgr: np.ndarray) -> None:
        if image_bgr.size == 0:
            raise InvalidImageError(
                code="FRAME_ARRAY_EMPTY",
                message="The decoded frame array is empty.",
            )
        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise InvalidImageError(
                code="FRAME_ARRAY_SHAPE_INVALID",
                message="Frame quality assessment requires a three-channel BGR image.",
            )

    @staticmethod
    def _minimum_width_check(input_: FrameQualityInput) -> QualityCheck:
        measured = float(input_.image_bgr.shape[1])
        threshold = float(input_.configuration.minimum_width_px)
        return QualityCheck(
            name="minimum_width_px",
            status=CheckStatus.PASS if measured >= threshold else CheckStatus.FAIL,
            measured_value=measured,
            threshold=threshold,
            comparison=">=",
            unit="px",
        )

    @staticmethod
    def _minimum_height_check(input_: FrameQualityInput) -> QualityCheck:
        measured = float(input_.image_bgr.shape[0])
        threshold = float(input_.configuration.minimum_height_px)
        return QualityCheck(
            name="minimum_height_px",
            status=CheckStatus.PASS if measured >= threshold else CheckStatus.FAIL,
            measured_value=measured,
            threshold=threshold,
            comparison=">=",
            unit="px",
        )

    @staticmethod
    def _focus_check(input_: FrameQualityInput) -> QualityCheck:
        measured = focus_score(input_.image_bgr)
        threshold = input_.configuration.minimum_focus_score
        return QualityCheck(
            name="minimum_focus_score",
            status=CheckStatus.PASS if measured >= threshold else CheckStatus.FAIL,
            measured_value=measured,
            threshold=threshold,
            comparison=">=",
            unit="variance_laplacian",
        )

    @staticmethod
    def _dark_ratio_check(input_: FrameQualityInput) -> QualityCheck:
        measured = dark_pixel_ratio(
            input_.image_bgr,
            threshold=input_.configuration.dark_pixel_threshold,
        )
        threshold = input_.configuration.maximum_dark_pixel_ratio
        return QualityCheck(
            name="maximum_dark_pixel_ratio",
            status=CheckStatus.PASS if measured <= threshold else CheckStatus.FAIL,
            measured_value=measured,
            threshold=threshold,
            comparison="<=",
            unit="ratio",
        )

    @staticmethod
    def _bright_ratio_check(input_: FrameQualityInput) -> QualityCheck:
        measured = bright_pixel_ratio(
            input_.image_bgr,
            threshold=input_.configuration.bright_pixel_threshold,
        )
        threshold = input_.configuration.maximum_bright_pixel_ratio
        return QualityCheck(
            name="maximum_bright_pixel_ratio",
            status=CheckStatus.PASS if measured <= threshold else CheckStatus.FAIL,
            measured_value=measured,
            threshold=threshold,
            comparison="<=",
            unit="ratio",
        )

    @staticmethod
    def _glare_ratio_check(input_: FrameQualityInput) -> QualityCheck:
        measured = glare_pixel_ratio(
            input_.image_bgr,
            value_threshold=input_.configuration.glare_value_threshold,
            saturation_threshold=input_.configuration.glare_saturation_threshold,
        )
        threshold = input_.configuration.maximum_glare_pixel_ratio
        return QualityCheck(
            name="maximum_glare_pixel_ratio",
            status=CheckStatus.PASS if measured <= threshold else CheckStatus.FAIL,
            measured_value=measured,
            threshold=threshold,
            comparison="<=",
            unit="ratio",
        )

    @staticmethod
    def _reason_code(check_name: str) -> str:
        return {
            "minimum_width_px": "FRAME_WIDTH_TOO_SMALL",
            "minimum_height_px": "FRAME_HEIGHT_TOO_SMALL",
            "minimum_focus_score": "FRAME_OUT_OF_FOCUS",
            "maximum_dark_pixel_ratio": "FRAME_TOO_DARK",
            "maximum_bright_pixel_ratio": "FRAME_TOO_BRIGHT",
            "maximum_glare_pixel_ratio": "FRAME_GLARE_EXCESSIVE",
        }[check_name]
