"""Deterministic morphology helpers for P.C.A.I. vision Cells."""

from __future__ import annotations

import cv2
import numpy as np


def elliptical_kernel(size_px: int) -> np.ndarray:
    """Return an odd-sized elliptical morphology kernel."""
    if size_px <= 0 or size_px % 2 == 0:
        raise ValueError("Morphology kernel size must be a positive odd integer.")
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size_px, size_px))


def open_mask(mask: np.ndarray, *, kernel_size_px: int, iterations: int = 1) -> np.ndarray:
    """Remove isolated foreground noise from a binary mask."""
    kernel = elliptical_kernel(kernel_size_px)
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=iterations)


def close_mask(mask: np.ndarray, *, kernel_size_px: int, iterations: int = 1) -> np.ndarray:
    """Close small holes and gaps inside foreground regions."""
    kernel = elliptical_kernel(kernel_size_px)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=iterations)
