from __future__ import annotations

from dataclasses import dataclass

from .contracts import CountPublicationDecision, StableCountResult
from .temporal_tracker import TemporalSceneMetrics


@dataclass(frozen=True, slots=True)
class StableCounterConfig:
    minimum_publish_frames: int = 8
    minimum_scene_confidence: float = 0.90
    clear_after_unstable_frames: int = 15

    def __post_init__(self) -> None:
        if self.minimum_publish_frames <= 0:
            raise ValueError("minimum_publish_frames must be positive.")
        if not 0.0 <= self.minimum_scene_confidence <= 1.0:
            raise ValueError("minimum_scene_confidence must be between 0 and 1.")
        if self.clear_after_unstable_frames <= 0:
            raise ValueError("clear_after_unstable_frames must be positive.")


class StableCounter:
    """Publish a count only after the temporal scene is trustworthy."""

    def __init__(self, config: StableCounterConfig | None = None) -> None:
        self._config = config or StableCounterConfig()
        self._published_count: int | None = None
        self._unstable_frames = 0

    @property
    def published_count(self) -> int | None:
        return self._published_count

    def update(self, metrics: TemporalSceneMetrics) -> StableCountResult:
        confidence = metrics.mean_confidence or 0.0

        if metrics.scene_stable:
            self._unstable_frames = 0
            publication_ready = (
                metrics.stable_frames >= self._config.minimum_publish_frames
                and confidence >= self._config.minimum_scene_confidence
            )

            if publication_ready:
                self._published_count = metrics.observed_count
                return StableCountResult(
                    frame_sequence=metrics.frame_sequence,
                    observed_count=metrics.observed_count,
                    stable_count=self._published_count,
                    confidence=confidence,
                    consecutive_stable_frames=metrics.stable_frames,
                    decision=CountPublicationDecision.PUBLISH,
                    reason_codes=("COUNT_STABLE",),
                )

            return StableCountResult(
                frame_sequence=metrics.frame_sequence,
                observed_count=metrics.observed_count,
                stable_count=self._published_count,
                confidence=confidence,
                consecutive_stable_frames=metrics.stable_frames,
                decision=CountPublicationDecision.HOLD,
                reason_codes=("WAITING_FOR_PUBLICATION_THRESHOLD",),
            )

        self._unstable_frames += 1
        if self._unstable_frames >= self._config.clear_after_unstable_frames:
            self._published_count = None
            return StableCountResult(
                frame_sequence=metrics.frame_sequence,
                observed_count=metrics.observed_count,
                stable_count=None,
                confidence=confidence,
                consecutive_stable_frames=0,
                decision=CountPublicationDecision.CLEAR,
                reason_codes=("SCENE_RESET",),
            )

        return StableCountResult(
            frame_sequence=metrics.frame_sequence,
            observed_count=metrics.observed_count,
            stable_count=self._published_count,
            confidence=confidence,
            consecutive_stable_frames=metrics.stable_frames,
            decision=CountPublicationDecision.HOLD,
            reason_codes=tuple(metrics.reason_codes),
        )

    def reset(self) -> None:
        self._published_count = None
        self._unstable_frames = 0
