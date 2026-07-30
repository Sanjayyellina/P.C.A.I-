from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .contracts import TrayGeometry


@dataclass(frozen=True, slots=True)
class NormalizedTrayFrame:
    image_bgr: np.ndarray
    geometry: TrayGeometry


class TrayPerspectiveTransformer:
    """Warp camera frames into the normalized tray workspace."""

    def warp(self, image_bgr: np.ndarray, geometry: TrayGeometry) -> NormalizedTrayFrame:
        self._validate_image(image_bgr)
        self._validate_geometry(geometry)

        warped = cv2.warpPerspective(
            image_bgr,
            geometry.perspective_matrix,
            (
                geometry.normalized_width_px,
                geometry.normalized_height_px,
            ),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0),
        )

        return NormalizedTrayFrame(image_bgr=warped, geometry=geometry)

    def image_to_tray_points(
        self,
        points_xy: np.ndarray,
        geometry: TrayGeometry,
    ) -> np.ndarray:
        points = self._validate_points(points_xy)
        transformed = cv2.perspectiveTransform(
            points.reshape(1, -1, 2),
            geometry.perspective_matrix,
        )
        return transformed.reshape(-1, 2)

    def tray_to_image_points(
        self,
        points_xy: np.ndarray,
        geometry: TrayGeometry,
    ) -> np.ndarray:
        points = self._validate_points(points_xy)
        transformed = cv2.perspectiveTransform(
            points.reshape(1, -1, 2),
            geometry.inverse_perspective_matrix,
        )
        return transformed.reshape(-1, 2)

    @staticmethod
    def _validate_image(image_bgr: np.ndarray) -> None:
        if not isinstance(image_bgr, np.ndarray):
            raise TypeError("image_bgr must be a numpy array.")
        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise ValueError("image_bgr must have shape (height, width, 3).")
        if image_bgr.size == 0:
            raise ValueError("image_bgr cannot be empty.")

    @staticmethod
    def _validate_geometry(geometry: TrayGeometry) -> None:
        if geometry.perspective_matrix.shape != (3, 3):
            raise ValueError("perspective_matrix must have shape (3, 3).")
        if geometry.inverse_perspective_matrix.shape != (3, 3):
            raise ValueError("inverse_perspective_matrix must have shape (3, 3).")
        if geometry.normalized_width_px <= 0 or geometry.normalized_height_px <= 0:
            raise ValueError("Normalized tray dimensions must be positive.")

    @staticmethod
    def _validate_points(points_xy: np.ndarray) -> np.ndarray:
        points = np.asarray(points_xy, dtype=np.float32)
        if points.ndim != 2 or points.shape[1] != 2:
            raise ValueError("points_xy must have shape (N, 2).")
        if len(points) == 0:
            raise ValueError("points_xy cannot be empty.")
        return points
