from __future__ import annotations

import cv2
import numpy as np

from pcai.acquisition import CameraFrame

from .contracts import (
    FrameQualityDecision,
    FrameQualityMetrics,
    FrameQualityReport,
    FrameQualityThresholds,
)


class FrameQualityAnalyzer:
    """Evaluate whether a live frame is safe to send to counting."""

    def __init__(self, thresholds: FrameQualityThresholds | None = None) -> None:
        self._thresholds = thresholds or FrameQualityThresholds()
        self._previous_gray: np.ndarray | None = None

    def analyze(self, frame: CameraFrame) -> FrameQualityReport:
        gray = cv2.cvtColor(frame.image_bgr, cv2.COLOR_BGR2GRAY)

        metrics = FrameQualityMetrics(
            focus_score=self._focus_score(gray),
            mean_brightness=float(np.mean(gray)),
            contrast_score=float(np.std(gray)),
            dark_clip_ratio=float(np.mean(gray <= 8)),
            bright_clip_ratio=float(np.mean(gray >= 247)),
            glare_ratio=self._glare_ratio(frame.image_bgr),
            motion_score=self._motion_score(gray),
        )

        reasons = self._reason_codes(metrics)
        overall_score = self._overall_score(metrics)
        decision = self._decision(reasons, overall_score, metrics.motion_score)

        self._previous_gray = gray.copy()

        return FrameQualityReport(
            frame_sequence=frame.metadata.sequence,
            camera_id=frame.metadata.camera_id,
            metrics=metrics,
            overall_score=overall_score,
            decision=decision,
            reason_codes=tuple(reasons),
            recommended_action=self._recommended_action(reasons),
        )

    @staticmethod
    def _focus_score(gray: np.ndarray) -> float:
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    @staticmethod
    def _glare_ratio(image_bgr: np.ndarray) -> float:
        hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]
        value = hsv[:, :, 2]
        glare_mask = (value >= 245) & (saturation <= 45)
        return float(np.mean(glare_mask))

    def _motion_score(self, gray: np.ndarray) -> float | None:
        if self._previous_gray is None:
            return None
        if self._previous_gray.shape != gray.shape:
            return None
        difference = cv2.absdiff(gray, self._previous_gray)
        return float(np.mean(difference))

    def _reason_codes(self, metrics: FrameQualityMetrics) -> list[str]:
        t = self._thresholds
        reasons: list[str] = []

        if metrics.focus_score < t.minimum_focus_score:
            reasons.append("FOCUS_LOW")
        if metrics.mean_brightness < t.minimum_brightness:
            reasons.append("FRAME_TOO_DARK")
        if metrics.mean_brightness > t.maximum_brightness:
            reasons.append("FRAME_TOO_BRIGHT")
        if metrics.dark_clip_ratio > t.maximum_dark_clip_ratio:
            reasons.append("DARK_CLIPPING_HIGH")
        if metrics.bright_clip_ratio > t.maximum_bright_clip_ratio:
            reasons.append("BRIGHT_CLIPPING_HIGH")
        if metrics.contrast_score < t.minimum_contrast:
            reasons.append("CONTRAST_LOW")
        if metrics.glare_ratio > t.maximum_glare_ratio:
            reasons.append("GLARE_HIGH")
        if (
            metrics.motion_score is not None
            and metrics.motion_score > t.maximum_motion_score
        ):
            reasons.append("MOTION_HIGH")

        return reasons

    def _overall_score(self, metrics: FrameQualityMetrics) -> float:
        t = self._thresholds

        focus = min(1.0, metrics.focus_score / max(t.minimum_focus_score, 1.0))

        brightness_center = (t.minimum_brightness + t.maximum_brightness) / 2.0
        brightness_half_range = (t.maximum_brightness - t.minimum_brightness) / 2.0
        brightness = max(
            0.0,
            1.0 - abs(metrics.mean_brightness - brightness_center) / brightness_half_range,
        )

        contrast = min(1.0, metrics.contrast_score / max(t.minimum_contrast, 1.0))
        dark_clip = 1.0 - min(
            1.0,
            metrics.dark_clip_ratio / max(t.maximum_dark_clip_ratio, 1e-6),
        )
        bright_clip = 1.0 - min(
            1.0,
            metrics.bright_clip_ratio / max(t.maximum_bright_clip_ratio, 1e-6),
        )
        glare = 1.0 - min(
            1.0,
            metrics.glare_ratio / max(t.maximum_glare_ratio, 1e-6),
        )

        if metrics.motion_score is None:
            motion = 1.0
        else:
            motion = 1.0 - min(
                1.0,
                metrics.motion_score / max(t.maximum_motion_score, 1e-6),
            )

        weighted = (
            0.25 * focus
            + 0.15 * brightness
            + 0.15 * contrast
            + 0.10 * dark_clip
            + 0.10 * bright_clip
            + 0.15 * glare
            + 0.10 * motion
        )
        return round(max(0.0, min(100.0, weighted * 100.0)), 2)

    def _decision(
        self,
        reasons: list[str],
        overall_score: float,
        motion_score: float | None,
    ) -> FrameQualityDecision:
        if motion_score is not None and "MOTION_HIGH" in reasons:
            return FrameQualityDecision.WAIT
        if reasons or overall_score < self._thresholds.minimum_overall_score:
            return FrameQualityDecision.REJECT
        return FrameQualityDecision.ACCEPT

    @staticmethod
    def _recommended_action(reasons: list[str]) -> str | None:
        if not reasons:
            return None
        if "MOTION_HIGH" in reasons:
            return "Hold the tray and camera still."
        if "FOCUS_LOW" in reasons:
            return "Refocus the camera or adjust camera height."
        if "FRAME_TOO_DARK" in reasons or "DARK_CLIPPING_HIGH" in reasons:
            return "Increase tray illumination."
        if "FRAME_TOO_BRIGHT" in reasons or "BRIGHT_CLIPPING_HIGH" in reasons:
            return "Reduce exposure or illumination intensity."
        if "GLARE_HIGH" in reasons:
            return "Reduce reflections or change the light angle."
        if "CONTRAST_LOW" in reasons:
            return "Improve contrast between tablets and tray."
        return "Adjust the camera and lighting setup."
