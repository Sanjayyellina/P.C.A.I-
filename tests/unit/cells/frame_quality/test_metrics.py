"""Unit tests for deterministic frame-quality metrics."""

from __future__ import annotations

import cv2
import numpy as np

from pcai.cells.frame_quality.metrics import (
    bright_pixel_ratio,
    dark_pixel_ratio,
    focus_score,
    glare_pixel_ratio,
)


def test_dark_pixel_ratio_is_one_for_black_image() -> None:
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    assert dark_pixel_ratio(image, threshold=10) == 1.0


def test_bright_pixel_ratio_is_one_for_white_image() -> None:
    image = np.full((10, 10, 3), 255, dtype=np.uint8)
    assert bright_pixel_ratio(image, threshold=245) == 1.0


def test_glare_ratio_detects_white_low_saturation_pixels() -> None:
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    image[:5, :, :] = 255
    assert glare_pixel_ratio(image, value_threshold=245, saturation_threshold=25) == 0.5


def test_sharp_pattern_has_higher_focus_score_than_blurred_pattern() -> None:
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    image[:, ::2] = 255
    blurred = cv2.GaussianBlur(image, (9, 9), 0)

    assert focus_score(image) > focus_score(blurred)
