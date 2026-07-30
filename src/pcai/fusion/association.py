from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from pcai.segmentation.contracts import CandidateObservation
from pcai.yolo_engine.contracts import YoloInstance

from .contracts import CandidateAssociation


@dataclass(frozen=True, slots=True)
class AssociationConfig:
    minimum_iou: float = 0.20
    maximum_centroid_distance_px: float = 80.0
    iou_weight: float = 0.75
    centroid_weight: float = 0.25

    def __post_init__(self) -> None:
        if not 0.0 <= self.minimum_iou <= 1.0:
            raise ValueError("minimum_iou must be between 0 and 1.")
        if self.maximum_centroid_distance_px <= 0:
            raise ValueError("maximum_centroid_distance_px must be positive.")
        if self.iou_weight < 0 or self.centroid_weight < 0:
            raise ValueError("Association weights cannot be negative.")
        if abs(self.iou_weight + self.centroid_weight - 1.0) > 1e-6:
            raise ValueError("Association weights must sum to 1.0.")


@dataclass(frozen=True, slots=True)
class AssociationResult:
    associations: tuple[CandidateAssociation, ...]
    matched_pairs: int
    unmatched_classical_ids: tuple[int, ...]
    unmatched_yolo_ids: tuple[int, ...]


class CandidateAssociator:
    """Associate classical candidates with YOLO instances using geometry."""

    def __init__(self, config: AssociationConfig | None = None) -> None:
        self._config = config or AssociationConfig()

    def associate(
        self,
        classical_candidates: tuple[CandidateObservation, ...],
        yolo_instances: tuple[YoloInstance, ...],
    ) -> AssociationResult:
        pair_scores: list[
            tuple[float, float, float, CandidateObservation, YoloInstance]
        ] = []

        for classical in classical_candidates:
            classical_box = self._xywh_to_xyxy(classical.bounding_box_xywh)
            for yolo in yolo_instances:
                iou = self._iou(classical_box, yolo.bounding_box_xyxy)
                distance = self._centroid_distance(
                    classical.centroid_xy,
                    yolo.centroid_xy,
                )
                if iou < self._config.minimum_iou and distance > self._config.maximum_centroid_distance_px:
                    continue

                distance_score = max(
                    0.0,
                    1.0 - distance / self._config.maximum_centroid_distance_px,
                )
                score = (
                    self._config.iou_weight * iou
                    + self._config.centroid_weight * distance_score
                )
                pair_scores.append((score, iou, distance, classical, yolo))

        pair_scores.sort(key=lambda item: item[0], reverse=True)
        used_classical: set[int] = set()
        used_yolo: set[int] = set()
        associations: list[CandidateAssociation] = []

        for _, iou, distance, classical, yolo in pair_scores:
            if classical.identifier in used_classical or yolo.identifier in used_yolo:
                continue
            used_classical.add(classical.identifier)
            used_yolo.add(yolo.identifier)
            associations.append(
                CandidateAssociation(
                    classical_candidate_id=classical.identifier,
                    yolo_instance_id=yolo.identifier,
                    iou=round(iou, 4),
                    centroid_distance_px=round(distance, 3),
                    matched=True,
                )
            )

        unmatched_classical = tuple(
            candidate.identifier
            for candidate in classical_candidates
            if candidate.identifier not in used_classical
        )
        unmatched_yolo = tuple(
            instance.identifier
            for instance in yolo_instances
            if instance.identifier not in used_yolo
        )

        for candidate_id in unmatched_classical:
            associations.append(
                CandidateAssociation(
                    classical_candidate_id=candidate_id,
                    yolo_instance_id=None,
                    iou=0.0,
                    centroid_distance_px=None,
                    matched=False,
                )
            )

        for instance_id in unmatched_yolo:
            associations.append(
                CandidateAssociation(
                    classical_candidate_id=None,
                    yolo_instance_id=instance_id,
                    iou=0.0,
                    centroid_distance_px=None,
                    matched=False,
                )
            )

        return AssociationResult(
            associations=tuple(associations),
            matched_pairs=len(used_classical),
            unmatched_classical_ids=unmatched_classical,
            unmatched_yolo_ids=unmatched_yolo,
        )

    @staticmethod
    def _xywh_to_xyxy(
        box_xywh: tuple[int, int, int, int],
    ) -> tuple[float, float, float, float]:
        x, y, width, height = box_xywh
        return float(x), float(y), float(x + width), float(y + height)

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

        first_area = max(0.0, first_x2 - first_x1) * max(0.0, first_y2 - first_y1)
        second_area = max(0.0, second_x2 - second_x1) * max(0.0, second_y2 - second_y1)
        union = first_area + second_area - intersection_area
        if union <= 0:
            return 0.0
        return max(0.0, min(1.0, intersection_area / union))
