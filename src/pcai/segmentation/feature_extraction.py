from __future__ import annotations

from dataclasses import dataclass
from math import pi

import cv2
import numpy as np

from .contracts import CandidateObservation


@dataclass(frozen=True, slots=True)
class CandidateFeatures:
    identifier: int
    area_px2: float
    perimeter_px: float
    circularity: float
    solidity: float
    convexity: float
    extent: float
    aspect_ratio: float
    major_axis_px: float | None
    minor_axis_px: float | None
    eccentricity: float | None
    orientation_deg: float | None
    mean_intensity: float
    intensity_stddev: float
    edge_density: float
    local_contrast: float
    distance_peak: float
    estimated_multiplicity: float


@dataclass(frozen=True, slots=True)
class FeatureExtractionConfig:
    local_padding_px: int = 8
    edge_low_threshold: int = 40
    edge_high_threshold: int = 120
    reference_single_area_px2: float | None = None

    def __post_init__(self) -> None:
        if self.local_padding_px < 0:
            raise ValueError("local_padding_px cannot be negative.")
        if not 0 <= self.edge_low_threshold < self.edge_high_threshold <= 255:
            raise ValueError("Edge thresholds must satisfy 0 <= low < high <= 255.")
        if self.reference_single_area_px2 is not None and self.reference_single_area_px2 <= 0:
            raise ValueError("reference_single_area_px2 must be positive when provided.")


class CandidateFeatureExtractor:
    """Extract geometric and appearance evidence from tablet candidates."""

    def __init__(self, config: FeatureExtractionConfig | None = None) -> None:
        self._config = config or FeatureExtractionConfig()

    def extract(
        self,
        candidate: CandidateObservation,
        grayscale: np.ndarray,
    ) -> CandidateFeatures:
        gray = self._validate_gray(grayscale, candidate.mask.shape)
        contour = candidate.contour
        x, y, width, height = candidate.bounding_box_xywh

        hull = cv2.convexHull(contour)
        hull_perimeter = float(cv2.arcLength(hull, True))
        convexity = hull_perimeter / candidate.perimeter_px if candidate.perimeter_px > 0 else 0.0
        convexity = max(0.0, min(1.0, convexity))

        bounding_area = float(width * height)
        extent = candidate.area_px2 / bounding_area if bounding_area > 0 else 0.0

        major_axis, minor_axis, eccentricity, orientation = self._ellipse_features(contour)

        pixels = gray[candidate.mask > 0]
        intensity_stddev = float(np.std(pixels)) if pixels.size else 0.0

        local = self._local_crop(gray, x, y, width, height)
        local_mask = self._local_crop(candidate.mask, x, y, width, height)
        local_contrast = self._local_contrast(local, local_mask)
        edge_density = self._edge_density(local, local_mask)
        distance_peak = self._distance_peak(candidate.mask)

        reference_area = self._config.reference_single_area_px2
        estimated_multiplicity = (
            candidate.area_px2 / reference_area if reference_area is not None else 1.0
        )

        return CandidateFeatures(
            identifier=candidate.identifier,
            area_px2=candidate.area_px2,
            perimeter_px=candidate.perimeter_px,
            circularity=candidate.circularity,
            solidity=candidate.solidity,
            convexity=convexity,
            extent=max(0.0, min(1.0, extent)),
            aspect_ratio=candidate.aspect_ratio,
            major_axis_px=major_axis,
            minor_axis_px=minor_axis,
            eccentricity=eccentricity,
            orientation_deg=orientation,
            mean_intensity=candidate.mean_intensity,
            intensity_stddev=intensity_stddev,
            edge_density=edge_density,
            local_contrast=local_contrast,
            distance_peak=distance_peak,
            estimated_multiplicity=max(0.0, estimated_multiplicity),
        )

    @staticmethod
    def _ellipse_features(
        contour: np.ndarray,
    ) -> tuple[float | None, float | None, float | None, float | None]:
        if len(contour) < 5:
            return None, None, None, None

        (_, _), (axis_a, axis_b), angle = cv2.fitEllipse(contour)
        major = float(max(axis_a, axis_b))
        minor = float(min(axis_a, axis_b))
        if major <= 0:
            return None, None, None, None

        eccentricity = float(np.sqrt(max(0.0, 1.0 - (minor * minor) / (major * major))))
        orientation = float(angle if axis_a >= axis_b else (angle + 90.0) % 180.0)
        return major, minor, eccentricity, orientation

    def _local_crop(
        self,
        image: np.ndarray,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> np.ndarray:
        padding = self._config.local_padding_px
        y0 = max(0, y - padding)
        x0 = max(0, x - padding)
        y1 = min(image.shape[0], y + height + padding)
        x1 = min(image.shape[1], x + width + padding)
        return image[y0:y1, x0:x1]

    @staticmethod
    def _local_contrast(local_gray: np.ndarray, local_mask: np.ndarray) -> float:
        foreground = local_gray[local_mask > 0]
        background = local_gray[local_mask == 0]
        if foreground.size == 0 or background.size == 0:
            return 0.0
        return float(abs(float(np.mean(foreground)) - float(np.mean(background))))

    def _edge_density(self, local_gray: np.ndarray, local_mask: np.ndarray) -> float:
        edges = cv2.Canny(
            local_gray,
            self._config.edge_low_threshold,
            self._config.edge_high_threshold,
        )
        foreground_pixels = int(np.count_nonzero(local_mask))
        if foreground_pixels == 0:
            return 0.0
        edge_pixels = int(np.count_nonzero((edges > 0) & (local_mask > 0)))
        return float(edge_pixels / foreground_pixels)

    @staticmethod
    def _distance_peak(mask: np.ndarray) -> float:
        distance = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        return float(distance.max()) if distance.size else 0.0

    @staticmethod
    def _validate_gray(gray: np.ndarray, expected_shape: tuple[int, int]) -> np.ndarray:
        if not isinstance(gray, np.ndarray):
            raise TypeError("grayscale must be a numpy array.")
        if gray.ndim != 2 or gray.shape != expected_shape:
            raise ValueError("grayscale must be 2D and match candidate mask shape.")
        if gray.dtype != np.uint8:
            gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        return gray
