from __future__ import annotations

from dataclasses import dataclass
from math import pi

import cv2
import numpy as np

from .contracts import CandidateObservation


@dataclass(frozen=True, slots=True)
class CandidateExtractionConfig:
    minimum_area_px2: float = 100.0
    maximum_area_ratio: float = 0.25
    minimum_perimeter_px: float = 20.0
    minimum_solidity: float = 0.45
    maximum_aspect_ratio: float = 4.0
    reject_border_touching: bool = True
    border_margin_px: int = 1

    def __post_init__(self) -> None:
        if self.minimum_area_px2 < 0:
            raise ValueError("minimum_area_px2 cannot be negative.")
        if not 0.0 < self.maximum_area_ratio <= 1.0:
            raise ValueError("maximum_area_ratio must be between 0 and 1.")
        if self.minimum_perimeter_px < 0:
            raise ValueError("minimum_perimeter_px cannot be negative.")
        if not 0.0 <= self.minimum_solidity <= 1.0:
            raise ValueError("minimum_solidity must be between 0 and 1.")
        if self.maximum_aspect_ratio < 1.0:
            raise ValueError("maximum_aspect_ratio must be at least 1.")
        if self.border_margin_px < 0:
            raise ValueError("border_margin_px cannot be negative.")


class CandidateExtractor:
    """Convert a binary mask into measured tablet candidate observations."""

    def __init__(self, config: CandidateExtractionConfig | None = None) -> None:
        self._config = config or CandidateExtractionConfig()

    def extract(
        self,
        binary_mask: np.ndarray,
        grayscale: np.ndarray,
    ) -> tuple[CandidateObservation, ...]:
        mask = self._validate_mask(binary_mask)
        gray = self._validate_gray(grayscale, mask.shape)
        image_area = float(mask.shape[0] * mask.shape[1])
        maximum_area = image_area * self._config.maximum_area_ratio

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        candidates: list[CandidateObservation] = []
        for contour in sorted(contours, key=cv2.contourArea, reverse=True):
            area = float(cv2.contourArea(contour))
            if not self._config.minimum_area_px2 <= area <= maximum_area:
                continue

            perimeter = float(cv2.arcLength(contour, True))
            if perimeter < self._config.minimum_perimeter_px:
                continue

            x, y, width, height = cv2.boundingRect(contour)
            if width <= 0 or height <= 0:
                continue
            if self._touches_border(x, y, width, height, mask.shape):
                continue

            hull = cv2.convexHull(contour)
            hull_area = float(cv2.contourArea(hull))
            solidity = area / hull_area if hull_area > 0 else 0.0
            if solidity < self._config.minimum_solidity:
                continue

            aspect_ratio = max(width / height, height / width)
            if aspect_ratio > self._config.maximum_aspect_ratio:
                continue

            moments = cv2.moments(contour)
            if moments["m00"] == 0:
                continue
            centroid_x = float(moments["m10"] / moments["m00"])
            centroid_y = float(moments["m01"] / moments["m00"])

            circularity = 0.0
            if perimeter > 0:
                circularity = float(4.0 * pi * area / (perimeter * perimeter))
                circularity = max(0.0, min(1.0, circularity))

            candidate_mask = np.zeros_like(mask)
            cv2.drawContours(candidate_mask, [contour], -1, 255, thickness=-1)
            mean_intensity = float(cv2.mean(gray, mask=candidate_mask)[0])

            candidates.append(
                CandidateObservation(
                    identifier=len(candidates),
                    mask=candidate_mask,
                    contour=contour.copy(),
                    centroid_xy=(centroid_x, centroid_y),
                    bounding_box_xywh=(x, y, width, height),
                    area_px2=area,
                    perimeter_px=perimeter,
                    circularity=circularity,
                    solidity=solidity,
                    aspect_ratio=float(aspect_ratio),
                    mean_intensity=mean_intensity,
                )
            )

        return tuple(candidates)

    def _touches_border(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        shape: tuple[int, int],
    ) -> bool:
        if not self._config.reject_border_touching:
            return False
        image_height, image_width = shape
        margin = self._config.border_margin_px
        return (
            x <= margin
            or y <= margin
            or x + width >= image_width - margin
            or y + height >= image_height - margin
        )

    @staticmethod
    def _validate_mask(mask: np.ndarray) -> np.ndarray:
        if not isinstance(mask, np.ndarray):
            raise TypeError("binary_mask must be a numpy array.")
        if mask.ndim != 2 or mask.size == 0:
            raise ValueError("binary_mask must be a non-empty 2D array.")
        if mask.dtype != np.uint8:
            mask = (mask > 0).astype(np.uint8) * 255
        else:
            mask = np.where(mask > 0, 255, 0).astype(np.uint8)
        return mask

    @staticmethod
    def _validate_gray(gray: np.ndarray, expected_shape: tuple[int, int]) -> np.ndarray:
        if not isinstance(gray, np.ndarray):
            raise TypeError("grayscale must be a numpy array.")
        if gray.ndim != 2 or gray.shape != expected_shape:
            raise ValueError("grayscale must be 2D and match binary_mask shape.")
        if gray.dtype != np.uint8:
            gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        return gray
