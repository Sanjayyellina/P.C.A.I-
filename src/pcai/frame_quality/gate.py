from __future__ import annotations

from dataclasses import dataclass

from pcai.acquisition import CameraFrame

from .analyzer import FrameQualityAnalyzer
from .contracts import FrameQualityDecision, FrameQualityReport
from .stability import StabilityMetrics, TemporalFrameStability


@dataclass(frozen=True, slots=True)
class FrameGateResult:
    frame: CameraFrame
    quality: FrameQualityReport
    stability: StabilityMetrics
    ready_for_counting: bool
    reason_codes: tuple[str, ...]


class LiveFrameQualityGate:
    """Combine single-frame quality and temporal stability decisions."""

    def __init__(
        self,
        analyzer: FrameQualityAnalyzer | None = None,
        stability: TemporalFrameStability | None = None,
    ) -> None:
        self._analyzer = analyzer or FrameQualityAnalyzer()
        self._stability = stability or TemporalFrameStability()

    def evaluate(self, frame: CameraFrame) -> FrameGateResult:
        quality = self._analyzer.analyze(frame)
        stability = self._stability.update(frame.image_bgr)

        reasons = list(quality.reason_codes)
        if not stability.stable:
            if stability.histogram_similarity is None:
                reasons.append("STABILITY_HISTORY_INSUFFICIENT")
            else:
                if stability.histogram_similarity < 0.90:
                    reasons.append("HISTOGRAM_UNSTABLE")
                if stability.brightness_drift is not None and stability.brightness_drift > 10.0:
                    reasons.append("BRIGHTNESS_DRIFT_HIGH")
                if stability.color_drift is not None and stability.color_drift > 12.0:
                    reasons.append("COLOR_DRIFT_HIGH")

        ready = (
            quality.decision is FrameQualityDecision.ACCEPT
            and stability.stable
        )

        return FrameGateResult(
            frame=frame,
            quality=quality,
            stability=stability,
            ready_for_counting=ready,
            reason_codes=tuple(dict.fromkeys(reasons)),
        )

    def reset(self) -> None:
        self._stability.reset()
