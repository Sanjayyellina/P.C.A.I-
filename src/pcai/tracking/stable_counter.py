from __future__ import annotations

from dataclasses import dataclass

from .contracts import CountPublicationDecision, StableCountResult
from .temporal_tracker import TemporalSceneMetrics


@dataclass(frozen=True, slots=True)
class StableCounterConfig:
    minimum_publish_frames: int = 8
    minimum_scene_confidence: float = 0.90
    clear_after_unstable_frames: int = 15


class StableCounter:
    """Publish counts only after temporal stability requirements are met."""

    def __init__(self, config: StableCounterConfig | None = None) -> None:
        self._config = config or StableCounterConfig()
        self._published_count: int | None = None
        self._unstable_frames = 0

    def update(self, metrics: TemporalSceneMetrics) -> StableCountResult:
        if metrics.scene_stable:
            self._unstable_frames = 0
            if (metrics.stable_frames >= self._config.minimum_publish_frames and
                (metrics.mean_confidence or 0.0) >= self._config.minimum_scene_confidence):
                self._published_count = metrics.observed_count
                return StableCountResult(metrics.frame_sequence,metrics.observed_count,self._published_count,metrics.mean_confidence or 0.0,metrics.stable_frames,CountPublicationDecision.PUBLISH,("COUNT_STABLE",))
            return StableCountResult(metrics.frame_sequence,metrics.observed_count,self._published_count,metrics.mean_confidence or 0.0,metrics.stable_frames,CountPublicationDecision.HOLD,("WAITING_FOR_STABILITY",))
        self._unstable_frames += 1
        if self._unstable_frames >= self._config.clear_after_unstable_frames:
            self._published_count=None
            return StableCountResult(metrics.frame_sequence,metrics.observed_count,None,metrics.mean_confidence or 0.0,0,CountPublicationDecision.CLEAR,("SCENE_RESET",))
        return StableCountResult(metrics.frame_sequence,metrics.observed_count,self._published_count,metrics.mean_confidence or 0.0,metrics.stable_frames,CountPublicationDecision.HOLD,tuple(metrics.reason_codes))