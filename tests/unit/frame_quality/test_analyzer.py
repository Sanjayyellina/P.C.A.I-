from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic_ns

import cv2
import numpy as np

from pcai.acquisition import CameraFrame, FrameMetadata
from pcai.frame_quality import (
    FrameQualityAnalyzer,
    FrameQualityDecision,
    FrameQualityThresholds,
)


def make_frame(image: np.ndarray, sequence: int = 0) -> CameraFrame:
    height, width = image.shape[:2]
    return CameraFrame(
        image_bgr=image,
        metadata=FrameMetadata(
            sequence=sequence,
            captured_at_utc=datetime.now(timezone.utc),
            monotonic_ns=monotonic_ns(),
            camera_id="test-camera",
            width_px=width,
            height_px=height,
        ),
    )


def checkerboard(size: int = 256, cell: int = 16) -> np.ndarray:
    rows, cols = np.indices((size, size))
    pattern = ((rows // cell + cols // cell) % 2) * 255
    gray = pattern.astype(np.uint8)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def test_sharp_balanced_frame_is_accepted() -> None:
    analyzer = FrameQualityAnalyzer(
        FrameQualityThresholds(
            minimum_focus_score=50.0,
            minimum_brightness=40.0,
            maximum_brightness=220.0,
            maximum_dark_clip_ratio=0.60,
            maximum_bright_clip_ratio=0.60,
            minimum_contrast=20.0,
            maximum_glare_ratio=0.60,
            maximum_motion_score=30.0,
            minimum_overall_score=60.0,
        )
    )

    report = analyzer.analyze(make_frame(checkerboard()))

    assert report.decision is FrameQualityDecision.ACCEPT
    assert report.accepted is True
    assert report.reason_codes == ()
    assert report.overall_score >= 60.0


def test_uniform_dark_frame_is_rejected() -> None:
    analyzer = FrameQualityAnalyzer()
    image = np.full((128, 128, 3), 5, dtype=np.uint8)

    report = analyzer.analyze(make_frame(image))

    assert report.decision is FrameQualityDecision.REJECT
    assert "FRAME_TOO_DARK" in report.reason_codes
    assert "FOCUS_LOW" in report.reason_codes
    assert report.recommended_action is not None


def test_uniform_bright_frame_is_rejected() -> None:
    analyzer = FrameQualityAnalyzer()
    image = np.full((128, 128, 3), 252, dtype=np.uint8)

    report = analyzer.analyze(make_frame(image))

    assert report.decision is FrameQualityDecision.REJECT
    assert "FRAME_TOO_BRIGHT" in report.reason_codes
    assert "BRIGHT_CLIPPING_HIGH" in report.reason_codes


def test_blurred_frame_has_lower_focus_than_sharp_frame() -> None:
    thresholds = FrameQualityThresholds(
        minimum_focus_score=1.0,
        minimum_brightness=1.0,
        maximum_brightness=254.0,
        maximum_dark_clip_ratio=1.0,
        maximum_bright_clip_ratio=1.0,
        minimum_contrast=1.0,
        maximum_glare_ratio=1.0,
        maximum_motion_score=255.0,
        minimum_overall_score=0.0,
    )
    analyzer = FrameQualityAnalyzer(thresholds)
    sharp = checkerboard()
    blurred = cv2.GaussianBlur(sharp, (31, 31), 0)

    sharp_report = analyzer.analyze(make_frame(sharp, sequence=1))
    blurred_report = analyzer.analyze(make_frame(blurred, sequence=2))

    assert sharp_report.metrics.focus_score > blurred_report.metrics.focus_score


def test_large_frame_change_returns_wait_for_motion() -> None:
    analyzer = FrameQualityAnalyzer(
        FrameQualityThresholds(
            minimum_focus_score=0.0,
            minimum_brightness=0.0,
            maximum_brightness=255.0,
            maximum_dark_clip_ratio=1.0,
            maximum_bright_clip_ratio=1.0,
            minimum_contrast=0.0,
            maximum_glare_ratio=1.0,
            maximum_motion_score=5.0,
            minimum_overall_score=0.0,
        )
    )

    analyzer.analyze(make_frame(np.zeros((64, 64, 3), dtype=np.uint8), sequence=1))
    report = analyzer.analyze(
        make_frame(np.full((64, 64, 3), 200, dtype=np.uint8), sequence=2)
    )

    assert report.decision is FrameQualityDecision.WAIT
    assert "MOTION_HIGH" in report.reason_codes
    assert report.recommended_action == "Hold the tray and camera still."


def test_shape_change_resets_motion_comparison() -> None:
    analyzer = FrameQualityAnalyzer(
        FrameQualityThresholds(
            minimum_focus_score=0.0,
            minimum_brightness=0.0,
            maximum_brightness=255.0,
            maximum_dark_clip_ratio=1.0,
            maximum_bright_clip_ratio=1.0,
            minimum_contrast=0.0,
            maximum_glare_ratio=1.0,
            maximum_motion_score=1.0,
            minimum_overall_score=0.0,
        )
    )

    analyzer.analyze(make_frame(np.zeros((32, 32, 3), dtype=np.uint8), sequence=1))
    report = analyzer.analyze(
        make_frame(np.zeros((64, 64, 3), dtype=np.uint8), sequence=2)
    )

    assert report.metrics.motion_score is None
