"""Homography and canonical tray helpers for C-003."""

from __future__ import annotations

import cv2
import numpy as np


def validate_point_array(points_xy: np.ndarray, *, minimum_points: int) -> None:
    """Validate an Nx2 floating-point point array."""
    if points_xy.ndim != 2 or points_xy.shape[1] != 2:
        raise ValueError("Point array must have shape (N, 2).")
    if points_xy.shape[0] < minimum_points:
        raise ValueError("Point array does not contain enough points.")


def estimate_homography(
    source_points_xy: np.ndarray,
    destination_points_xy: np.ndarray,
) -> np.ndarray | None:
    """Estimate a projective transform from source to destination coordinates."""
    homography, _mask = cv2.findHomography(
        source_points_xy.astype(np.float32),
        destination_points_xy.astype(np.float32),
        method=0,
    )
    return homography


def reprojection_error_px(
    source_points_xy: np.ndarray,
    destination_points_xy: np.ndarray,
    homography: np.ndarray,
) -> float:
    """Return mean Euclidean reprojection error in destination pixels."""
    source = source_points_xy.astype(np.float32).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(source, homography).reshape(-1, 2)
    errors = np.linalg.norm(projected - destination_points_xy.astype(np.float32), axis=1)
    return float(np.mean(errors))


def warp_to_canonical(
    image_bgr: np.ndarray,
    homography: np.ndarray,
    *,
    width_px: int,
    height_px: int,
) -> np.ndarray:
    """Warp the source image into canonical tray coordinates."""
    return cv2.warpPerspective(image_bgr, homography, (width_px, height_px))


def full_tray_mask(*, width_px: int, height_px: int) -> np.ndarray:
    """Return a full-size binary mask for the canonical tray interior."""
    return np.full((height_px, width_px), 255, dtype=np.uint8)
