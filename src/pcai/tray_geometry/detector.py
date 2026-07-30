from __future__ import annotations

from dataclasses import dataclass
from math import exp

import cv2
import numpy as np

from .contracts import TrayCorners, TrayDetectionResult, TrayGeometry


@dataclass(frozen=True, slots=True)
class TrayDetectorConfig:
    normalized_width_px: int = 1024
    normalized_height_px: int = 768
    minimum_area_ratio: float = 0.20
    maximum_area_ratio: float = 0.98
    polygon_epsilon_ratio: float = 0.02
    minimum_rectangularity: float = 0.75
    minimum_confidence: float = 0.55
    blur_kernel_size: int = 5
    canny_low: int = 40
    canny_high: int = 140
    morphology_kernel_size: int = 7

    def __post_init__(self) -> None:
        if self.normalized_width_px <= 0 or self.normalized_height_px <= 0:
            raise ValueError("Normalized tray dimensions must be positive.")
        if not 0.0 < self.minimum_area_ratio < self.maximum_area_ratio <= 1.0:
            raise ValueError("Area ratios must satisfy 0 < min < max <= 1.")
        if not 0.0 < self.polygon_epsilon_ratio < 1.0:
            raise ValueError("polygon_epsilon_ratio must be between 0 and 1.")
        if not 0.0 <= self.minimum_rectangularity <= 1.0:
            raise ValueError("minimum_rectangularity must be between 0 and 1.")
        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1.")
        for name in ("blur_kernel_size", "morphology_kernel_size"):
            value = getattr(self, name)
            if value <= 0 or value % 2 == 0:
                raise ValueError(f"{name} must be a positive odd integer.")
        if not 0 <= self.canny_low < self.canny_high <= 255:
            raise ValueError("Canny thresholds must satisfy 0 <= low < high <= 255.")


class TrayDetector:
    """Detect the dominant quadrilateral tray and build its homography."""

    def __init__(self, config: TrayDetectorConfig | None = None) -> None:
        self._config = config or TrayDetectorConfig()

    def detect(self, image_bgr: np.ndarray) -> TrayDetectionResult:
        self._validate_image(image_bgr)
        height, width = image_bgr.shape[:2]
        image_area = float(height * width)

        edges = self._edge_map(image_bgr)
        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        best: tuple[float, np.ndarray] | None = None
        for contour in contours:
            contour_area = float(cv2.contourArea(contour))
            area_ratio = contour_area / image_area
            if not self._config.minimum_area_ratio <= area_ratio <= self._config.maximum_area_ratio:
                continue

            perimeter = float(cv2.arcLength(contour, True))
            if perimeter <= 0:
                continue

            polygon = cv2.approxPolyDP(
                contour,
                self._config.polygon_epsilon_ratio * perimeter,
                True,
            )
            if len(polygon) != 4 or not cv2.isContourConvex(polygon):
                continue

            rectangularity = self._rectangularity(polygon)
            if rectangularity < self._config.minimum_rectangularity:
                continue

            score = self._confidence(area_ratio, rectangularity, polygon, width, height)
            if best is None or score > best[0]:
                best = (score, polygon.reshape(4, 2).astype(np.float32))

        if best is None:
            return TrayDetectionResult(False, None, "TRAY_QUADRILATERAL_NOT_FOUND")

        confidence, points = best
        if confidence < self._config.minimum_confidence:
            return TrayDetectionResult(False, None, "TRAY_CONFIDENCE_LOW")

        ordered = self._order_points(points)
        destination = np.array(
            [
                [0.0, 0.0],
                [self._config.normalized_width_px - 1.0, 0.0],
                [self._config.normalized_width_px - 1.0, self._config.normalized_height_px - 1.0],
                [0.0, self._config.normalized_height_px - 1.0],
            ],
            dtype=np.float32,
        )
        perspective = cv2.getPerspectiveTransform(ordered, destination)
        inverse = cv2.getPerspectiveTransform(destination, ordered)

        corners = TrayCorners(
            top_left=tuple(map(float, ordered[0])),
            top_right=tuple(map(float, ordered[1])),
            bottom_right=tuple(map(float, ordered[2])),
            bottom_left=tuple(map(float, ordered[3])),
        )
        geometry = TrayGeometry(
            corners=corners,
            perspective_matrix=perspective,
            inverse_perspective_matrix=inverse,
            normalized_width_px=self._config.normalized_width_px,
            normalized_height_px=self._config.normalized_height_px,
            confidence=round(confidence, 4),
        )
        return TrayDetectionResult(True, geometry, None)

    def _edge_map(self, image_bgr: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(
            gray,
            (self._config.blur_kernel_size, self._config.blur_kernel_size),
            0,
        )
        edges = cv2.Canny(
            blurred,
            self._config.canny_low,
            self._config.canny_high,
        )
        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (
                self._config.morphology_kernel_size,
                self._config.morphology_kernel_size,
            ),
        )
        return cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    @staticmethod
    def _rectangularity(polygon: np.ndarray) -> float:
        area = float(cv2.contourArea(polygon))
        rectangle = cv2.minAreaRect(polygon)
        rect_width, rect_height = rectangle[1]
        rectangle_area = float(rect_width * rect_height)
        if rectangle_area <= 0:
            return 0.0
        return max(0.0, min(1.0, area / rectangle_area))

    @staticmethod
    def _order_points(points: np.ndarray) -> np.ndarray:
        ordered = np.zeros((4, 2), dtype=np.float32)
        sums = points.sum(axis=1)
        differences = np.diff(points, axis=1).reshape(-1)
        ordered[0] = points[np.argmin(sums)]
        ordered[2] = points[np.argmax(sums)]
        ordered[1] = points[np.argmin(differences)]
        ordered[3] = points[np.argmax(differences)]
        return ordered

    def _confidence(
        self,
        area_ratio: float,
        rectangularity: float,
        polygon: np.ndarray,
        width: int,
        height: int,
    ) -> float:
        target_area = (self._config.minimum_area_ratio + self._config.maximum_area_ratio) / 2.0
        area_score = exp(-4.0 * abs(area_ratio - target_area))
        border_score = self._border_margin_score(polygon, width, height)
        return max(
            0.0,
            min(1.0, 0.45 * rectangularity + 0.35 * area_score + 0.20 * border_score),
        )

    @staticmethod
    def _border_margin_score(polygon: np.ndarray, width: int, height: int) -> float:
        points = polygon.reshape(-1, 2)
        margin_x = min(float(points[:, 0].min()), float(width - 1 - points[:, 0].max()))
        margin_y = min(float(points[:, 1].min()), float(height - 1 - points[:, 1].max()))
        normalized = min(margin_x / max(width, 1), margin_y / max(height, 1))
        return max(0.0, min(1.0, normalized * 10.0 + 0.5))

    @staticmethod
    def _validate_image(image_bgr: np.ndarray) -> None:
        if not isinstance(image_bgr, np.ndarray):
            raise TypeError("image_bgr must be a numpy array.")
        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise ValueError("image_bgr must have shape (height, width, 3).")
        if image_bgr.size == 0:
            raise ValueError("image_bgr cannot be empty.")
