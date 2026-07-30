from __future__ import annotations

import numpy as np
import pytest

from pcai.frame_quality import StabilityThresholds, TemporalFrameStability


def test_first_frame_is_not_stable() -> None:
    stability = TemporalFrameStability()
    image = np.full((64, 64, 3), 120, dtype=np.uint8)

    metrics = stability.update(image)

    assert metrics.histogram_similarity is None
    assert metrics.brightness_drift is None
    assert metrics.color_drift is None
    assert metrics.stable is False


def test_identical_successive_frames_are_stable() -> None:
    stability = TemporalFrameStability()
    image = np.full((64, 64, 3), 120, dtype=np.uint8)

    stability.update(image)
    metrics = stability.update(image.copy())

    assert metrics.histogram_similarity == pytest.approx(1.0)
    assert metrics.brightness_drift == pytest.approx(0.0)
    assert metrics.color_drift == pytest.approx(0.0)
    assert metrics.stable is True


def test_brightness_jump_is_unstable() -> None:
    stability = TemporalFrameStability(
        StabilityThresholds(
            minimum_histogram_similarity=-1.0,
            maximum_brightness_drift=5.0,
            maximum_color_drift=255.0,
            history_size=3,
        )
    )

    stability.update(np.full((64, 64, 3), 80, dtype=np.uint8))
    metrics = stability.update(np.full((64, 64, 3), 160, dtype=np.uint8))

    assert metrics.brightness_drift is not None
    assert metrics.brightness_drift > 5.0
    assert metrics.stable is False


def test_color_shift_is_unstable() -> None:
    stability = TemporalFrameStability(
        StabilityThresholds(
            minimum_histogram_similarity=-1.0,
            maximum_brightness_drift=255.0,
            maximum_color_drift=5.0,
            history_size=3,
        )
    )
    neutral = np.full((64, 64, 3), 100, dtype=np.uint8)
    shifted = neutral.copy()
    shifted[:, :, 2] = 180

    stability.update(neutral)
    metrics = stability.update(shifted)

    assert metrics.color_drift is not None
    assert metrics.color_drift > 5.0
    assert metrics.stable is False


def test_reset_clears_history() -> None:
    stability = TemporalFrameStability()
    image = np.full((32, 32, 3), 100, dtype=np.uint8)

    stability.update(image)
    stability.update(image)
    stability.reset()
    metrics = stability.update(image)

    assert metrics.histogram_similarity is None
    assert metrics.stable is False


def test_invalid_image_shape_is_rejected() -> None:
    stability = TemporalFrameStability()

    with pytest.raises(ValueError, match="shape"):
        stability.update(np.zeros((64, 64), dtype=np.uint8))
