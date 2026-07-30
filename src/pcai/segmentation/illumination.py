from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True, slots=True)
class IlluminationConfig:
    background_kernel_size: int = 61
    clahe_clip_limit: float = 2.0
    clahe_grid_size: int = 8

    def __post_init__(self) -> None:
        if self.background_kernel_size <= 1 or self.background_kernel_size % 2 == 0:
            raise ValueError("background_kernel_size must be an odd integer greater than 1.")
        if self.clahe_clip_limit <= 0:
            raise ValueError("clahe_clip_limit must be positive.")
        if self.clahe_grid_size <= 0:
            raise ValueError("clahe_grid_size must be positive.")


@dataclass(frozen=True, slots=True)
class IlluminationResult:
    grayscale: np.ndarray
    background: np.ndarray
    normalized: np.ndarray


class IlluminationNormalizer:
    """Reduce slow lighting gradients while preserving tablet boundaries."""

    def __init__(self, config: IlluminationConfig | None = None) -> None:
        self._config = config or IlluminationConfig()
        self._clahe = cv2.createCLAHE(
            clipLimit=self._config.clahe_clip_limit,
            tileGridSize=(self._config.clahe_grid_size, self._config.clahe_grid_size),
        )

    def normalize(self, image_bgr: np.ndarray) -> IlluminationResult:
        self._validate_image(image_bgr)
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

        background = cv2.GaussianBlur(
            gray,
            (
                self._config.background_kernel_size,
                self._config.background_kernel_size,
            ),
            0,
        )
        divided = cv2.divide(gray, background, scale=128.0)
        normalized = self._clahe.apply(divided)

        return IlluminationResult(
            grayscale=gray,
            background=background,
            normalized=normalized,
        )

    @staticmethod
    def _validate_image(image_bgr: np.ndarray) -> None:
        if not isinstance(image_bgr, np.ndarray):
            raise TypeError("image_bgr must be a numpy array.")
        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise ValueError("image_bgr must have shape (height, width, 3).")
        if image_bgr.size == 0:
            raise ValueError("image_bgr cannot be empty.")
