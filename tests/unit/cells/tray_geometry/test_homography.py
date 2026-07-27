"""Unit tests for C-003 homography helpers."""

from __future__ import annotations

import numpy as np

from pcai.cells.tray_geometry.homography import (
    estimate_homography,
    reprojection_error_px,
)


def test_identity_correspondence_has_near_zero_reprojection_error() -> None:
    points = np.array(
        [[0.0, 0.0], [100.0, 0.0], [100.0, 50.0], [0.0, 50.0]],
        dtype=np.float32,
    )
    homography = estimate_homography(points, points)

    assert homography is not None
    assert reprojection_error_px(points, points, homography) < 1e-5
