from __future__ import annotations

from dataclasses import dataclass, replace
from math import hypot

from .contracts import (
    TrackObservation,
    TrackedObject,
    TrackingFrameResult,
    TrackState,
)


@dataclass(frozen=True, slots=True)
class ObjectTrackerConfig:
    maximum_centroid_distance_px: float = 80.0
    minimum_iou: float = 0.10
    confirmation_hits: int = 3
    maximum_missed_frames: int = 5
    count_history_size: int = 12

    def __post_init__(self) -> None:
        if self.maximum_centroid_distance_px <= 0:
            raise ValueError("maximum_centroid_distance_px must be positive.")
        if not 0.0 <= self.minimum_iou <= 1.0:
            raise ValueError("minimum_iou must be between 0 and 1.")
        if self.confirmation_hits <= 0:
            raise ValueError("confirmation_hits must be positive.")
        if self.maximum_missed_frames < 0:
            raise ValueError("maximum_missed_frames cannot be negative.")
        if self.count_history_size <= 0:
            raise ValueError("count_history_size must be positive.")


class TemporalObjectTracker:
    """Maintain persistent object identities across successive live frames."""

    def __init__(self, config: ObjectTrackerConfig | None = None) -> None:
        self._config = config or ObjectTrackerConfig()
        self._tracks: dict[int, TrackedObject] = {}
        self._next_track_id = 0

    @property
    def tracks(self) -> tuple[TrackedObject, ...]:
        return tuple(sorted(self._tracks.values(), key=lambda item: item.track_id))

    def update(
        self,
        frame_sequence: int,
        observations: tuple[TrackObservation, ...],
    ) -> TrackingFrameResult:
        if frame_sequence < 0:
            raise ValueError("frame_sequence cannot be negative.")
        if any(item.frame_sequence != frame_sequence for item in observations):
            raise ValueError("All observations must match frame_sequence.")

        active_track_ids = {
            track_id
            for track_id, track in self._tracks.items()
            if track.state is not TrackState.REMOVED
        }
        assignments = self._associate(active_track_ids, observations)

        matched_track_ids: set[int] = set()
        matched_observation_indexes: set[int] = set()

        for track_id, observation_index in assignments:
            observation = observations[observation_index]
            self._tracks[track_id] = self._update_track(
                self._tracks[track_id],
                observation,
            )
            matched_track_ids.add(track_id)
            matched_observation_indexes.add(observation_index)

        removed_track_ids: list[int] = []
        for track_id in sorted(active_track_ids - matched_track_ids):
            updated = self._mark_missed(self._tracks[track_id], frame_sequence)
            self._tracks[track_id] = updated
            if updated.state is TrackState.REMOVED:
                removed_track_ids.append(track_id)

        created_tracks = 0
        for observation_index, observation in enumerate(observations):
            if observation_index in matched_observation_indexes:
                continue
            track = self._create_track(observation)
            self._tracks[track.track_id] = track
            created_tracks += 1

        visible_tracks = tuple(
            track
            for track in self.tracks
            if track.state is not TrackState.REMOVED
        )
        confirmed_tracks = sum(
            track.state is TrackState.CONFIRMED for track in visible_tracks
        )

        reasons: list[str] = []
        if created_tracks:
            reasons.append("TRACKS_CREATED")
        if removed_track_ids:
            reasons.append("TRACKS_REMOVED")
        if any(track.state is TrackState.LOST for track in visible_tracks):
            reasons.append("LOST_TRACKS_PRESENT")

        return TrackingFrameResult(
            frame_sequence=frame_sequence,
            tracks=visible_tracks,
            active_tracks=len(visible_tracks),
            confirmed_tracks=confirmed_tracks,
            created_tracks=created_tracks,
            removed_track_ids=tuple(removed_track_ids),
            reason_codes=tuple(reasons),
        )

    def reset(self) -> None:
        self._tracks.clear()
        self._next_track_id = 0

    def _associate(
        self,
        active_track_ids: set[int],
        observations: tuple[TrackObservation, ...],
    ) -> tuple[tuple[int, int], ...]:
        candidates: list[tuple[float, int, int]] = []

        for track_id in active_track_ids:
            track = self._tracks[track_id]
            for observation_index, observation in enumerate(observations):
                distance = self._centroid_distance(
                    track.centroid_xy,
                    observation.centroid_xy,
                )
                iou = self._iou(
                    track.bounding_box_xyxy,
                    observation.bounding_box_xyxy,
                )
                if (
                    distance > self._config.maximum_centroid_distance_px
                    and iou < self._config.minimum_iou
                ):
                    continue

                distance_score = max(
                    0.0,
                    1.0 - distance / self._config.maximum_centroid_distance_px,
                )
                count_score = (
                    1.0
                    if track.estimated_count == observation.estimated_count
                    else 0.0
                )
                score = 0.55 * iou + 0.35 * distance_score + 0.10 * count_score
                candidates.append((score, track_id, observation_index))

        candidates.sort(key=lambda item: item[0], reverse=True)
        used_tracks: set[int] = set()
        used_observations: set[int] = set()
        assignments: list[tuple[int, int]] = []

        for _, track_id, observation_index in candidates:
            if track_id in used_tracks or observation_index in used_observations:
                continue
            used_tracks.add(track_id)
            used_observations.add(observation_index)
            assignments.append((track_id, observation_index))

        return tuple(assignments)

    def _create_track(self, observation: TrackObservation) -> TrackedObject:
        track_id = self._next_track_id
        self._next_track_id += 1
        state = (
            TrackState.CONFIRMED
            if self._config.confirmation_hits <= 1
            else TrackState.TENTATIVE
        )
        return TrackedObject(
            track_id=track_id,
            state=state,
            first_frame_sequence=observation.frame_sequence,
            last_frame_sequence=observation.frame_sequence,
            age_frames=1,
            hit_count=1,
            missed_frames=0,
            centroid_xy=observation.centroid_xy,
            bounding_box_xyxy=observation.bounding_box_xyxy,
            estimated_count=observation.estimated_count,
            confidence=observation.confidence,
            count_history=(observation.estimated_count,),
        )

    def _update_track(
        self,
        track: TrackedObject,
        observation: TrackObservation,
    ) -> TrackedObject:
        history = (
            track.count_history + (observation.estimated_count,)
        )[-self._config.count_history_size :]
        estimated_count = self._mode(history)
        hit_count = track.hit_count + 1
        state = (
            TrackState.CONFIRMED
            if hit_count >= self._config.confirmation_hits
            else TrackState.TENTATIVE
        )

        confidence = max(
            0.0,
            min(1.0, 0.65 * track.confidence + 0.35 * observation.confidence),
        )

        return replace(
            track,
            state=state,
            last_frame_sequence=observation.frame_sequence,
            age_frames=track.age_frames + 1,
            hit_count=hit_count,
            missed_frames=0,
            centroid_xy=observation.centroid_xy,
            bounding_box_xyxy=observation.bounding_box_xyxy,
            estimated_count=estimated_count,
            confidence=round(confidence, 4),
            count_history=history,
        )

    def _mark_missed(
        self,
        track: TrackedObject,
        frame_sequence: int,
    ) -> TrackedObject:
        missed = track.missed_frames + 1
        state = (
            TrackState.REMOVED
            if missed > self._config.maximum_missed_frames
            else TrackState.LOST
        )
        return replace(
            track,
            state=state,
            last_frame_sequence=max(track.last_frame_sequence, frame_sequence),
            age_frames=track.age_frames + 1,
            missed_frames=missed,
        )

    @staticmethod
    def _mode(values: tuple[int, ...]) -> int:
        counts: dict[int, int] = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        return max(counts, key=lambda value: (counts[value], value))

    @staticmethod
    def _centroid_distance(
        first: tuple[float, float],
        second: tuple[float, float],
    ) -> float:
        return hypot(first[0] - second[0], first[1] - second[1])

    @staticmethod
    def _iou(
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> float:
        first_x1, first_y1, first_x2, first_y2 = first
        second_x1, second_y1, second_x2, second_y2 = second

        intersection_x1 = max(first_x1, second_x1)
        intersection_y1 = max(first_y1, second_y1)
        intersection_x2 = min(first_x2, second_x2)
        intersection_y2 = min(first_y2, second_y2)

        intersection_width = max(0.0, intersection_x2 - intersection_x1)
        intersection_height = max(0.0, intersection_y2 - intersection_y1)
        intersection_area = intersection_width * intersection_height

        first_area = max(0.0, first_x2 - first_x1) * max(
            0.0,
            first_y2 - first_y1,
        )
        second_area = max(0.0, second_x2 - second_x1) * max(
            0.0,
            second_y2 - second_y1,
        )
        union = first_area + second_area - intersection_area
        if union <= 0:
            return 0.0
        return max(0.0, min(1.0, intersection_area / union))
