"""Tests for shared contour helpers."""

from __future__ import annotations

import cv2
import numpy as np

from pcai.vision.contours import contour_circularity, contour_solidity, external_contours


def test_external_contours_are_returned_in_stable_order() -> None:
    mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(mask, (70, 70), 8, 255, -1)
    cv2.circle(mask, (20, 20), 8, 255, -1)

    contours = external_contours(mask)

    first_x, first_y, _width, _height = cv2.boundingRect(contours[0])
    assert first_x < 30
    assert first_y < 30


def test_circle_has_high_circularity_and_solidity() -> None:
    mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 20, 255, -1)
    contour = external_contours(mask)[0]

    assert contour_circularity(contour) > 0.8
    assert contour_solidity(contour) > 0.95
