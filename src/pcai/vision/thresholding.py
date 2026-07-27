"""Deterministic thresholding helpers for P.C.A.I. vision Cells."""

from __future__ import annotations

import cv2
import numpy as np


def grayscale(image_bgr: np.ndarray) -> np.ndarray:
    """Convert a three-channel BGR image to grayscale."""
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)


def binary_inverse_threshold(
    gray: np.ndarray,
    *,
    threshold_value: int,
) -> np.ndarray:
    """Return a binary inverse mask using one explicit threshold."""
    _value, mask = cv2.threshold(
        gray,
        threshold_value,
        255,
        cv2.THRESH_BINARY_INV,
    )
    return mask
