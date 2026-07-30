from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import cv2
import numpy as np


class TabletPolarity(StrEnum):
    LIGHT_ON_DARK = "light_on_dark"
    DARK_ON_LIGHT = "dark_on_light"
    AUTO = "auto"


@dataclass(frozen=True, slots=True)
class AdaptiveThresholdConfig:
    polarity: TabletPolarity = TabletPolarity.AUTO
    adaptive_block_size: int = 51
    adaptive_c: float = 4.0
    opening_kernel_size: int = 3
    closing_kernel_size: int = 7
    minimum_component_area_px2: int = 80
    maximum_component_area_ratio: float = 0.30
    border_margin_px: int = 2

    def __post_init__(self) -> None:
        if self.adaptive_block_size <= 1 or self.adaptive_block_size % 2 == 0:
            raise ValueError("adaptive_block_size must be an odd integer greater than 1.")
        for name in ("opening_kernel_size", "closing_kernel_size"):
            value = getattr(self, name)
            if value <= 0 or value % 2 == 0:
                raise ValueError(f"{name} must be a positive odd integer.")
        if self.minimum_component_area_px2 < 0:
            raise ValueError("minimum_component_area_px2 cannot be negative.")
        if not 0.0 < self.maximum_component_area_ratio <= 1.0:
            raise ValueError("maximum_component_area_ratio must be between 0 and 1.")
        if self.border_margin_px < 0:
            raise ValueError("border_margin_px cannot be negative.")


@dataclass(frozen=True, slots=True)
class ThresholdResult:
    binary_mask: np.ndarray
    adaptive_mask: np.ndarray
    otsu_mask: np.ndarray
    selected_polarity: TabletPolarity
    foreground_ratio: float


class AdaptiveTabletSegmenter:
    """Create a tablet foreground mask from an illumination-normalized tray."""

    def __init__(self, config: AdaptiveThresholdConfig | None = None) -> None:
        self._config = config or AdaptiveThresholdConfig()

    def segment(self, normalized_gray: np.ndarray) -> ThresholdResult:
        gray = self._validate_gray(normalized_gray)

        candidate_polarities = (
            (TabletPolarity.LIGHT_ON_DARK, TabletPolarity.DARK_ON_LIGHT)
            if self._config.polarity is TabletPolarity.AUTO
            else (self._config.polarity,)
        )

        best: tuple[float, TabletPolarity, np.ndarray, np.ndarray, np.ndarray] | None = None
        for polarity in candidate_polarities:
            adaptive = self._adaptive(gray, polarity)
            otsu = self._otsu(gray, polarity)
            combined = cv2.bitwise_and(adaptive, otsu)
            cleaned = self._clean(combined)
            score = self._mask_score(cleaned)
            if best is None or score > best[0]:
                best = (score, polarity, adaptive, otsu, cleaned)

        assert best is not None
        _, polarity, adaptive, otsu, cleaned = best
        return ThresholdResult(
            binary_mask=cleaned,
            adaptive_mask=adaptive,
            otsu_mask=otsu,
            selected_polarity=polarity,
            foreground_ratio=float(np.mean(cleaned > 0)),
        )

    def _adaptive(self, gray: np.ndarray, polarity: TabletPolarity) -> np.ndarray:
        threshold_type = (
            cv2.THRESH_BINARY
            if polarity is TabletPolarity.LIGHT_ON_DARK
            else cv2.THRESH_BINARY_INV
        )
        return cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            threshold_type,
            self._config.adaptive_block_size,
            self._config.adaptive_c,
        )

    @staticmethod
    def _otsu(gray: np.ndarray, polarity: TabletPolarity) -> np.ndarray:
        threshold_type = (
            cv2.THRESH_BINARY
            if polarity is TabletPolarity.LIGHT_ON_DARK
            else cv2.THRESH_BINARY_INV
        )
        _, mask = cv2.threshold(
            gray,
            0,
            255,
            threshold_type | cv2.THRESH_OTSU,
        )
        return mask

    def _clean(self, mask: np.ndarray) -> np.ndarray:
        opening_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self._config.opening_kernel_size, self._config.opening_kernel_size),
        )
        closing_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self._config.closing_kernel_size, self._config.closing_kernel_size),
        )
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, opening_kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, closing_kernel)
        cleaned = self._filter_components(cleaned)

        margin = self._config.border_margin_px
        if margin > 0:
            cleaned[:margin, :] = 0
            cleaned[-margin:, :] = 0
            cleaned[:, :margin] = 0
            cleaned[:, -margin:] = 0
        return cleaned

    def _filter_components(self, mask: np.ndarray) -> np.ndarray:
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        output = np.zeros_like(mask)
        image_area = float(mask.shape[0] * mask.shape[1])
        maximum_area = image_area * self._config.maximum_component_area_ratio

        for label in range(1, count):
            area = int(stats[label, cv2.CC_STAT_AREA])
            if self._config.minimum_component_area_px2 <= area <= maximum_area:
                output[labels == label] = 255
        return output

    @staticmethod
    def _mask_score(mask: np.ndarray) -> float:
        foreground_ratio = float(np.mean(mask > 0))
        if foreground_ratio <= 0.0 or foreground_ratio >= 0.80:
            return -1.0

        component_count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        areas = stats[1:, cv2.CC_STAT_AREA] if component_count > 1 else np.empty(0)
        nontrivial = float(np.sum(areas >= 80))
        occupancy_score = max(0.0, 1.0 - abs(foreground_ratio - 0.12) / 0.12)
        component_score = min(1.0, nontrivial / 10.0)
        return 0.6 * occupancy_score + 0.4 * component_score

    @staticmethod
    def _validate_gray(image: np.ndarray) -> np.ndarray:
        if not isinstance(image, np.ndarray):
            raise TypeError("normalized_gray must be a numpy array.")
        if image.ndim != 2:
            raise ValueError("normalized_gray must have shape (height, width).")
        if image.size == 0:
            raise ValueError("normalized_gray cannot be empty.")
        if image.dtype != np.uint8:
            image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        return image
