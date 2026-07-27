"""Deterministic image-quality measurements for C-002."""

from __future__ import annotations

import cv2
import numpy as np


def focus_score(image_bgr: np.ndarray) -> float:
    """Return variance of the grayscale Laplacian as a focus proxy."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def dark_pixel_ratio(image_bgr: np.ndarray, *, threshold: int) -> float:
    """Return ratio of grayscale pixels at or below the dark threshold."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray <= threshold))


def bright_pixel_ratio(image_bgr: np.ndarray, *, threshold: int) -> float:
    """Return ratio of grayscale pixels at or above the bright threshold."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray >= threshold))


def glare_pixel_ratio(
    image_bgr: np.ndarray,
    *,
    value_threshold: int,
    saturation_threshold: int,
) -> float:
    """Return ratio of bright, low-saturation pixels likely to represent glare."""
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    glare_mask = (value >= value_threshold) & (saturation <= saturation_threshold)
    return float(np.mean(glare_mask))
