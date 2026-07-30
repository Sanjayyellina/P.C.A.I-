from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True, slots=True)
class StabilityMetrics:
    histogram_similarity: float | None
    brightness_drift: float | None
    color_drift: float | None
    stable: bool


@dataclass(frozen=True, slots=True)
class StabilityThresholds:
    minimum_histogram_similarity: float = 0.90
    maximum_brightness_drift: float = 10.0
    maximum_color_drift: float = 12.0
    history_size: int = 5

    def __post_init__(self) -> None:
        if not -1.0 <= self.minimum_histogram_similarity <= 1.0:
            raise ValueError("minimum_histogram_similarity must be between -1 and 1.")
        if self.maximum_brightness_drift < 0 or self.maximum_color_drift < 0:
            raise ValueError("Drift thresholds cannot be negative.")
        if self.history_size < 2:
            raise ValueError("history_size must be at least 2.")


class TemporalFrameStability:
    def __init__(self, thresholds: StabilityThresholds | None = None) -> None:
        self._thresholds = thresholds or StabilityThresholds()
        self._histograms: deque[np.ndarray] = deque(maxlen=self._thresholds.history_size)
        self._brightness: deque[float] = deque(maxlen=self._thresholds.history_size)
        self._color_means: deque[np.ndarray] = deque(maxlen=self._thresholds.history_size)

    def update(self, image_bgr: np.ndarray) -> StabilityMetrics:
        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise ValueError("image_bgr must have shape (height, width, 3).")

        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        histogram = cv2.calcHist([gray], [0], None, [64], [0, 256])
        cv2.normalize(histogram, histogram, alpha=1.0, norm_type=cv2.NORM_L1)
        brightness = float(np.mean(gray))
        color_mean = image_bgr.reshape(-1, 3).mean(axis=0)

        similarity = self._mean_histogram_similarity(histogram)
        brightness_drift = self._drift(brightness, self._brightness)
        color_drift = self._color_drift(color_mean)

        self._histograms.append(histogram)
        self._brightness.append(brightness)
        self._color_means.append(color_mean)

        ready = similarity is not None and brightness_drift is not None and color_drift is not None
        stable = bool(
            ready
            and similarity >= self._thresholds.minimum_histogram_similarity
            and brightness_drift <= self._thresholds.maximum_brightness_drift
            and color_drift <= self._thresholds.maximum_color_drift
        )

        return StabilityMetrics(similarity, brightness_drift, color_drift, stable)

    def reset(self) -> None:
        self._histograms.clear()
        self._brightness.clear()
        self._color_means.clear()

    def _mean_histogram_similarity(self, current: np.ndarray) -> float | None:
        if not self._histograms:
            return None
        values = [cv2.compareHist(previous, current, cv2.HISTCMP_CORREL) for previous in self._histograms]
        return float(np.mean(values))

    @staticmethod
    def _drift(current: float, history: deque[float]) -> float | None:
        if not history:
            return None
        return abs(current - float(np.mean(history)))

    def _color_drift(self, current: np.ndarray) -> float | None:
        if not self._color_means:
            return None
        reference = np.mean(np.stack(tuple(self._color_means)), axis=0)
        return float(np.max(np.abs(current - reference)))
