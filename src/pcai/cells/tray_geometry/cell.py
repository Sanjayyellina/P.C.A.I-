"""
P.C.A.I. — C-003 Tray Geometry Cell.

Mission
-------
Convert a quality-approved frame into a canonical tray coordinate system.

Authority
---------
May validate point correspondences, estimate homography, measure reprojection
error, rectify perspective, generate a tray mask, and report physical scale.

Prohibited
----------
Must not detect pills, classify candidates, count pills, or identify medicine.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from pcai.cells.tray_geometry.contracts import (
    GeometryStatus,
    TrayGeometryFacts,
    TrayGeometryInput,
)
from pcai.cells.tray_geometry.homography import (
    estimate_homography,
    full_tray_mask,
    reprojection_error_px,
    validate_point_array,
    warp_to_canonical,
)
from pcai.shared.errors import InvalidImageError, OperatingEnvelopeError


class TrayGeometryCell(Protocol):
    """Public C-003 capability contract."""

    def measure(self, input_: TrayGeometryInput) -> TrayGeometryFacts:
        """Measure canonical tray geometry for one frame."""


class ProjectiveTrayGeometryCell:
    """Deterministic projective-geometry implementation of C-003."""

    def measure(self, input_: TrayGeometryInput) -> TrayGeometryFacts:
        self._validate_image(input_.image_bgr)
        configuration = input_.configuration

        if configuration.canonical_width_px <= 0 or configuration.canonical_height_px <= 0:
            raise OperatingEnvelopeError(
                code="CANONICAL_TRAY_DIMENSIONS_INVALID",
                message="Canonical tray dimensions must be positive.",
            )
        if configuration.tray_width_mm <= 0.0 or configuration.tray_height_mm <= 0.0:
            raise OperatingEnvelopeError(
                code="TRAY_PHYSICAL_DIMENSIONS_INVALID",
                message="Physical tray dimensions must be positive.",
            )

        try:
            validate_point_array(
                input_.source_points_xy,
                minimum_points=configuration.minimum_marker_count,
            )
            validate_point_array(
                input_.destination_points_xy,
                minimum_points=configuration.minimum_marker_count,
            )
        except ValueError:
            return self._failure(
                input_,
                status=GeometryStatus.REQUIRE_RECAPTURE,
                reason_code="FIDUCIAL_POINTS_INVALID",
            )

        if input_.source_points_xy.shape != input_.destination_points_xy.shape:
            return self._failure(
                input_,
                status=GeometryStatus.REQUIRE_RECAPTURE,
                reason_code="FIDUCIAL_POINT_COUNT_MISMATCH",
            )

        homography = estimate_homography(
            input_.source_points_xy,
            input_.destination_points_xy,
        )
        if homography is None or not np.isfinite(homography).all():
            return self._failure(
                input_,
                status=GeometryStatus.REQUIRE_RECALIBRATION,
                reason_code="HOMOGRAPHY_ESTIMATION_FAILED",
            )

        error_px = reprojection_error_px(
            input_.source_points_xy,
            input_.destination_points_xy,
            homography,
        )
        if error_px > configuration.maximum_reprojection_error_px:
            return TrayGeometryFacts(
                frame_id=input_.frame_id,
                status=GeometryStatus.REQUIRE_RECALIBRATION,
                canonical_tray_bgr=None,
                tray_mask=None,
                homography=homography,
                reprojection_error_px=error_px,
                pixels_per_mm_x=None,
                pixels_per_mm_y=None,
                reason_codes=("REPROJECTION_ERROR_TOO_HIGH",),
            )

        canonical = warp_to_canonical(
            input_.image_bgr,
            homography,
            width_px=configuration.canonical_width_px,
            height_px=configuration.canonical_height_px,
        )
        mask = full_tray_mask(
            width_px=configuration.canonical_width_px,
            height_px=configuration.canonical_height_px,
        )

        return TrayGeometryFacts(
            frame_id=input_.frame_id,
            status=GeometryStatus.PASS,
            canonical_tray_bgr=canonical,
            tray_mask=mask,
            homography=homography,
            reprojection_error_px=error_px,
            pixels_per_mm_x=(
                configuration.canonical_width_px / configuration.tray_width_mm
            ),
            pixels_per_mm_y=(
                configuration.canonical_height_px / configuration.tray_height_mm
            ),
            reason_codes=(),
        )

    @staticmethod
    def _validate_image(image_bgr: np.ndarray) -> None:
        if image_bgr.size == 0:
            raise InvalidImageError(
                code="FRAME_ARRAY_EMPTY",
                message="Tray geometry requires a non-empty decoded frame.",
            )
        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise InvalidImageError(
                code="FRAME_ARRAY_SHAPE_INVALID",
                message="Tray geometry requires a three-channel BGR image.",
            )

    @staticmethod
    def _failure(
        input_: TrayGeometryInput,
        *,
        status: GeometryStatus,
        reason_code: str,
    ) -> TrayGeometryFacts:
        return TrayGeometryFacts(
            frame_id=input_.frame_id,
            status=status,
            canonical_tray_bgr=None,
            tray_mask=None,
            homography=None,
            reprojection_error_px=None,
            pixels_per_mm_x=None,
            pixels_per_mm_y=None,
            reason_codes=(reason_code,),
        )
