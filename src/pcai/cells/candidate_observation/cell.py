"""
P.C.A.I. — C-004 Candidate Observation Cell.

Mission
-------
Transform a calibrated tray image into measurable foreground candidates.

Authority
---------
May segment tray foreground, extract contours, measure geometric properties,
and assign conservative observation statuses.

Prohibited
----------
Must not assume every region is one pill, produce the final count, identify
medicine, or resolve touching regions beyond its operating envelope.
"""

from __future__ import annotations

from typing import Protocol

import cv2
import numpy as np

from pcai.cells.candidate_observation.contracts import (
    CandidateObservation,
    CandidateObservationInput,
    CandidateSet,
    CandidateStatus,
    ForegroundPolarity,
)
from pcai.shared.errors import InvalidImageError, OperatingEnvelopeError
from pcai.vision.contours import (
    contour_centroid,
    contour_circularity,
    contour_solidity,
    external_contours,
)
from pcai.vision.masks import touches_mask_border
from pcai.vision.morphology import close_mask, open_mask
from pcai.vision.thresholding import (
    binary_inverse_threshold,
    binary_threshold,
    grayscale,
)


class CandidateObservationCell(Protocol):
    """Public C-004 capability contract."""

    def observe(self, input_: CandidateObservationInput) -> CandidateSet:
        """Observe foreground candidates inside one canonical tray."""


class DeterministicCandidateObservationCell:
    """Classical deterministic implementation of C-004."""

    def observe(self, input_: CandidateObservationInput) -> CandidateSet:
        self._validate(input_)
        configuration = input_.configuration

        gray = grayscale(input_.canonical_tray_bgr)
        if configuration.foreground_polarity is ForegroundPolarity.DARK_ON_LIGHT:
            foreground = binary_inverse_threshold(
                gray,
                threshold_value=configuration.foreground_threshold,
            )
        elif configuration.foreground_polarity is ForegroundPolarity.LIGHT_ON_DARK:
            foreground = binary_threshold(
                gray,
                threshold_value=configuration.foreground_threshold,
            )
        else:
            raise OperatingEnvelopeError(
                code="FOREGROUND_POLARITY_INVALID",
                message="Candidate observation requires a supported foreground polarity.",
            )
        foreground = cv2.bitwise_and(foreground, input_.tray_mask)
        foreground = open_mask(
            foreground,
            kernel_size_px=configuration.morphology_kernel_px,
        )
        foreground = close_mask(
            foreground,
            kernel_size_px=configuration.morphology_kernel_px,
        )

        candidates = tuple(
            self._build_candidate(
                input_=input_,
                contour=contour,
                index=index,
            )
            for index, contour in enumerate(external_contours(foreground), start=1)
        )

        return CandidateSet(
            frame_id=input_.frame_id,
            foreground_mask=foreground,
            candidates=candidates,
        )

    @staticmethod
    def _validate(input_: CandidateObservationInput) -> None:
        image = input_.canonical_tray_bgr
        mask = input_.tray_mask
        if image.size == 0 or image.ndim != 3 or image.shape[2] != 3:
            raise InvalidImageError(
                code="CANONICAL_TRAY_IMAGE_INVALID",
                message="Candidate observation requires a non-empty three-channel tray image.",
            )
        if mask.ndim != 2 or mask.shape != image.shape[:2]:
            raise InvalidImageError(
                code="TRAY_MASK_INVALID",
                message="Tray mask dimensions must match the canonical tray image.",
            )
        if input_.pixels_per_mm_x <= 0.0 or input_.pixels_per_mm_y <= 0.0:
            raise OperatingEnvelopeError(
                code="PIXEL_SCALE_INVALID",
                message="Candidate observation requires positive pixel-to-millimetre scale.",
            )

    def _build_candidate(
        self,
        *,
        input_: CandidateObservationInput,
        contour: np.ndarray,
        index: int,
    ) -> CandidateObservation:
        area_px2 = float(cv2.contourArea(contour))
        pixel_area_per_mm2 = input_.pixels_per_mm_x * input_.pixels_per_mm_y
        area_mm2 = area_px2 / pixel_area_per_mm2
        perimeter_px = float(cv2.arcLength(contour, True))
        x, y, width, height = cv2.boundingRect(contour)
        aspect_ratio = float(width / height) if height else 0.0
        border = touches_mask_border(contour, input_.tray_mask)
        solidity = contour_solidity(contour)
        status, reason_codes = self._classify(
            area_mm2=area_mm2,
            solidity=solidity,
            touches_border=border,
            input_=input_,
        )

        return CandidateObservation(
            candidate_id=f"candidate-{index:04d}",
            contour=contour,
            bounding_box_xywh=(x, y, width, height),
            centroid_xy=contour_centroid(contour),
            area_px2=area_px2,
            area_mm2=area_mm2,
            perimeter_px=perimeter_px,
            circularity=contour_circularity(contour),
            solidity=solidity,
            aspect_ratio=aspect_ratio,
            touches_tray_border=border,
            status=status,
            reason_codes=reason_codes,
        )

    @staticmethod
    def _classify(
        *,
        area_mm2: float,
        solidity: float,
        touches_border: bool,
        input_: CandidateObservationInput,
    ) -> tuple[CandidateStatus, tuple[str, ...]]:
        configuration = input_.configuration

        if touches_border:
            return CandidateStatus.PARTIAL_OBJECT, ("CANDIDATE_TOUCHES_TRAY_BORDER",)
        if area_mm2 < configuration.minimum_area_mm2:
            return CandidateStatus.ARTIFACT, ("CANDIDATE_AREA_TOO_SMALL",)
        if area_mm2 > configuration.maximum_supported_area_mm2:
            return CandidateStatus.UNKNOWN, ("CANDIDATE_AREA_UNSUPPORTED",)
        if (
            area_mm2 > configuration.maximum_single_area_mm2
            or area_mm2
            > configuration.maximum_single_area_mm2 * configuration.touching_area_multiplier
        ):
            return CandidateStatus.TOUCHING_REGION, ("CANDIDATE_LIKELY_TOUCHING_REGION",)
        if solidity < configuration.minimum_solidity_single:
            return CandidateStatus.UNKNOWN, ("CANDIDATE_SOLIDITY_TOO_LOW",)
        return CandidateStatus.SINGLE_CANDIDATE, ()
