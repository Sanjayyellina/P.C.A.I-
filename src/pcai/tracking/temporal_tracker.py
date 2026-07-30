from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import hypot

from .contracts import TrackingFrameResult, TrackState


@dataclass(frozen=True, slots=True)
class TemporalStabilityConfig:
    window_size: int = 12
    minimum_ready_frames: int = 5
    maximum_count_range: int = 0
    maximum_mean_track_motion_px: float = 2.5
    maximum_confidence_range: float = 0.08
    minimum_mean_confidence: float = 0.80
    require_all_tracks_confirmed: bool = True

    def __post_init__(self) -> None:
        if self.window_size < 2:
            raise ValueError("window_size must be at least 2.")
        if not 2 <= self.minimum_ready_frames <= self.window_size:
            raise ValueError(
                "minimum_ready_frames must be between 2 and window_size."
            )
        if self.maximum_count_range < 0:
            raise ValueError("maximum_count_range cannot be negative.")
        if self.maximum_mean_track_motion_px < 0:
            raise ValueError("maximum_mean_track_motion_px cannot be negative.")
        if not 0.0 <= self.maximum_confidence_range <= 1.0:
            raise ValueError("maximum_confidence_range must be between 0 and 1.")
        if not 0.0 <= self.minimum_mean_confidence <= 1.0:
            raise ValueError("minimum_mean_confidence must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class TemporalSceneMetrics:
    frame_sequence: int
    observed_count: int
    count_range: int | None
    mean_track_motion_px: float | None
    confidence_range: float | None
    mean_confidence: float | None
    stable_frames: int
    scene_stable: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _FrameSnapshot:
    frame_sequence: int
    observed_count: int
    mean_confidence: float
    centroids_by_track: dict[int, tuple[float, float]]
    all_tracks_confirmed: bool
    topology_changed: bool


class TemporalSceneTracker:
    """Evaluate whether tracked tablet evidence is stable across live frames."""

    def __init__(self, config: TemporalStabilityConfig | None = None) -> None:
        self._config = config or TemporalStabilityConfig()
        self._history: deque[_FrameSnapshot] = deque(maxlen=self._config.window_size)
        self._consecutive_stable_frames = 0

    @property
    def consecutive_stable_frames(self) -> int:
        return self._consecutive_stable_frames

    def update(self, tracking: TrackingFrameResult) -> TemporalSceneMetrics:
        snapshot = self._snapshot(tracking)
        self._history.append(snapshot)

        if len(self._history) < self._config.minimum_ready_frames:
            self._consecutive_stable_frames = 0
            return TemporalSceneMetrics(
                frame_sequence=tracking.frame_sequence,
                observed_count=snapshot.observed_count,
                count_range=None,
                mean_track_motion_px=None,
                confidence_range=None,
                mean_confidence=None,
                stable_frames=0,
                scene_stable=False,
                reason_codes=("TEMPORAL_HISTORY_INSUFFICIENT",),
            )

        window = tuple(self._history)[-self._config.minimum_ready_frames :]
        counts = tuple(item.observed_count for item in window)
        confidences = tuple(item.mean_confidence for item in window)

        count_range = max(counts) - min(counts)
        confidence_range = max(confidences) - min(confidences)
        mean_confidence = sum(confidences) / len(confidences)
        mean_motion = self._mean_motion(window)

        reasons: list[str] = []
        if count_range > self._config.maximum_count_range:
            reasons.append("TEMPORAL_COUNT_UNSTABLE")
        if mean_motion > self._config.maximum_mean_track_motion_px:
            reasons.append("TRACK_MOTION_HIGH")
        if confidence_range > self._config.maximum_confidence_range:
            reasons.append("TEMPORAL_CONFIDENCE_UNSTABLE")
        if mean_confidence < self._config.minimum_mean_confidence:
            reasons.append("TEMPORAL_CONFIDENCE_LOW")
        if any(item.topology_changed for item in window):
            reasons.append("TRACK_TOPOLOGY_CHANGED")
        if (
            self._config.require_all_tracks_confirmed
            and not all(item.all_tracks_confirmed for item in window)
        ):
            reasons.append("UNCONFIRMED_TRACKS_PRESENT")

        stable = not reasons
        self._consecutive_stable_frames = (
            self._consecutive_stable_frames + 1 if stable else 0
        )

        return TemporalSceneMetrics(
            frame_sequence=tracking.frame_sequence,
            observed_count=snapshot.observed_count,
            count_range=count_range,
            mean_track_motion_px=round(mean_motion, 4),
            confidence_range=round(confidence_range, 4),
            mean_confidence=round(mean_confidence, 4),
            stable_frames=self._consecutive_stable_frames,
            scene_stable=stable,
            reason_codes=tuple(reasons),
        )

    def reset(self) -> None:
        self._history.clear()
        self._consecutive_stable_frames = 0

    @staticmethod
    def _snapshot(tracking: TrackingFrameResult) -> _FrameSnapshot:
        confirmed_tracks = tuple(
            track
            for track in tracking.tracks
            if track.state is TrackState.CONFIRMED
        )
        visible_tracks = tuple(
            track
            for track in tracking.tracks
            if track.state in {TrackState.TENTATIVE, TrackState.CONFIRMED}
        )

        observed_count = sum(track.estimated_count for track in confirmed_tracks)
        mean_confidence = (
            sum(track.confidence for track in confirmed_tracks) / len(confirmed_tracks)
            if confirmed_tracks
            else 0.0
        )
        centroids = {
            track.track_id: track.centroid_xy
            for track in visible_tracks
        }
        all_confirmed = bool(visible_tracks) and all(
            track.state is TrackState.CONFIRMED for track in visible_tracks
        )
        topology_changed = bool(
            tracking.created_tracks
            or tracking.removed_track_ids
            or any(track.state is TrackState.LOST for track in tracking.tracks)
        )

        return _FrameSnapshot(
            frame_sequence=tracking.frame_sequence,
            observed_count=observed_count,
            mean_confidence=mean_confidence,
            centroids_by_track=centroids,
            all_tracks_confirmed=all_confirmed,
            topology_changed=topology_changed,
        )

    @staticmethod
    def _mean_motion(window: tuple[_FrameSnapshot, ...]) -> float:
        distances: list[float] = []
        for previous, current in zip(window, window[1:], strict=True):
            shared_track_ids = (
                previous.centroids_by_track.keys()
                & current.centroids_by_track.keys()
            )
            for track_id in shared_track_ids:
                before = previous.centroids_by_track[track_id]
                after = current.centroids_by_track[track_id]
                distances.append(hypot(after[0] - before[0], after[1] - before[1]))

        return sum(distances) / len(distances) if distances else 0.0
