"""Binary-mask helpers for P.C.A.I. vision Cells."""

from __future__ import annotations

import cv2
import numpy as np


def apply_binary_mask(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Return image pixels inside the binary mask."""
    return cv2.bitwise_and(image, image, mask=mask)


def touches_mask_border(contour: np.ndarray, mask: np.ndarray) -> bool:
    """Return whether a contour intersects the invalid exterior of a tray mask."""
    contour_mask = np.zeros_like(mask, dtype=np.uint8)
    cv2.drawContours(contour_mask, [contour], -1, 255, thickness=-1)
    eroded = cv2.erode(
        mask,
        np.ones((3, 3), dtype=np.uint8),
        iterations=1,
        borderType=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    border_band = cv2.subtract(mask, eroded)
    return bool(np.any((contour_mask > 0) & (border_band > 0)))
