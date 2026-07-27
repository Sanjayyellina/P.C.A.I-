"""Unit tests for C-003 Tray Geometry Cell."""

from __future__ import annotations

from uuid import uuid4

import numpy as np

from pcai.cells.tray_geometry import (
    GeometryStatus,
    ProjectiveTrayGeometryCell,
    TrayGeometryConfiguration,
    TrayGeometryInput,
)
from pcai.shared.identifiers import FrameId


def _configuration() -> TrayGeometryConfiguration:
    return TrayGeometryConfiguration(
        canonical_width_px=220,
        canonical_height_px=140,
        tray_width_mm=220.0,
        tray_height_mm=140.0,
        maximum_reprojection_error_px=0.1,
    )


def _points() -> np.ndarray:
    return np.array(
        [[0.0, 0.0], [219.0, 0.0], [219.0, 139.0], [0.0, 139.0]],
        dtype=np.float32,
    )


def test_measure_passes_identity_geometry() -> None:
    image = np.zeros((140, 220, 3), dtype=np.uint8)
    cell = ProjectiveTrayGeometryCell()

    result = cell.measure(
        TrayGeometryInput(
            frame_id=FrameId(str(uuid4())),
            image_bgr=image,
            source_points_xy=_points(),
            destination_points_xy=_points(),
            configuration=_configuration(),
        )
    )

    assert result.status is GeometryStatus.PASS
    assert result.canonical_tray_bgr is not None
    assert result.canonical_tray_bgr.shape == (140, 220, 3)
    assert result.tray_mask is not None
    assert result.tray_mask.shape == (140, 220)
    assert result.pixels_per_mm_x == 1.0
    assert result.pixels_per_mm_y == 1.0


def test_measure_requires_recapture_for_point_count_mismatch() -> None:
    image = np.zeros((140, 220, 3), dtype=np.uint8)
    source = _points()
    destination = source[:3]
    cell = ProjectiveTrayGeometryCell()

    result = cell.measure(
        TrayGeometryInput(
            frame_id=FrameId(str(uuid4())),
            image_bgr=image,
            source_points_xy=source,
            destination_points_xy=destination,
            configuration=_configuration(),
        )
    )

    assert result.status is GeometryStatus.REQUIRE_RECAPTURE
    assert "FIDUCIAL_POINTS_INVALID" in result.reason_codes


def test_measure_is_deterministic() -> None:
    image = np.zeros((140, 220, 3), dtype=np.uint8)
    input_ = TrayGeometryInput(
        frame_id=FrameId(str(uuid4())),
        image_bgr=image,
        source_points_xy=_points(),
        destination_points_xy=_points(),
        configuration=_configuration(),
    )
    cell = ProjectiveTrayGeometryCell()

    first = cell.measure(input_)
    second = cell.measure(input_)

    assert first.status == second.status
    assert first.reprojection_error_px == second.reprojection_error_px
    assert np.array_equal(first.canonical_tray_bgr, second.canonical_tray_bgr)
    assert np.array_equal(first.tray_mask, second.tray_mask)
