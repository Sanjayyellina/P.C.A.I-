from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .contracts import TrayDetectionResult, TrayGeometry
from .detector import TrayDetector
from .perspective import NormalizedTrayFrame, TrayPerspectiveTransformer


@dataclass(frozen=True, slots=True)
class TrayWorkspaceResult:
    ready: bool
    normalized_frame: NormalizedTrayFrame | None
    geometry: TrayGeometry | None
    reason: str | None


class TrayWorkspaceBuilder:
    """Detect and normalize the tray in one deterministic operation."""

    def __init__(
        self,
        detector: TrayDetector | None = None,
        transformer: TrayPerspectiveTransformer | None = None,
    ) -> None:
        self._detector = detector or TrayDetector()
        self._transformer = transformer or TrayPerspectiveTransformer()

    def build(self, image_bgr: np.ndarray) -> TrayWorkspaceResult:
        detection = self._detector.detect(image_bgr)
        if not detection.tray_found or detection.geometry is None:
            return TrayWorkspaceResult(
                ready=False,
                normalized_frame=None,
                geometry=None,
                reason=detection.reason or "TRAY_NOT_READY",
            )

        normalized = self._transformer.warp(image_bgr, detection.geometry)
        return TrayWorkspaceResult(
            ready=True,
            normalized_frame=normalized,
            geometry=detection.geometry,
            reason=None,
        )

    def map_image_points_to_tray(
        self,
        points_xy: np.ndarray,
        geometry: TrayGeometry,
    ) -> np.ndarray:
        return self._transformer.image_to_tray_points(points_xy, geometry)

    def map_tray_points_to_image(
        self,
        points_xy: np.ndarray,
        geometry: TrayGeometry,
    ) -> np.ndarray:
        return self._transformer.tray_to_image_points(points_xy, geometry)
