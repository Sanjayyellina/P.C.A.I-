from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FusionConfidenceConfig:
    classical_weight: float = 0.40
    yolo_weight: float = 0.40
    agreement_weight: float = 0.20
    unmatched_penalty: float = 0.25
    disagreement_penalty: float = 0.35

    def __post_init__(self) -> None:
        weights = self.classical_weight + self.yolo_weight + self.agreement_weight
        if abs(weights - 1.0) > 1e-6:
            raise ValueError("Fusion confidence weights must sum to 1.0.")
        for field_name in (
            "classical_weight",
            "yolo_weight",
            "agreement_weight",
            "unmatched_penalty",
            "disagreement_penalty",
        ):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1.")


class FusionConfidenceScorer:
    """Calculate calibrated confidence for matched and unmatched evidence."""

    def __init__(self, config: FusionConfidenceConfig | None = None) -> None:
        self._config = config or FusionConfidenceConfig()

    def matched_confidence(
        self,
        classical_confidence: float,
        yolo_confidence: float,
        agreement_score: float,
        counts_agree: bool,
    ) -> float:
        self._validate_probability(classical_confidence, "classical_confidence")
        self._validate_probability(yolo_confidence, "yolo_confidence")
        self._validate_probability(agreement_score, "agreement_score")

        confidence = (
            self._config.classical_weight * classical_confidence
            + self._config.yolo_weight * yolo_confidence
            + self._config.agreement_weight * agreement_score
        )
        if not counts_agree:
            confidence *= 1.0 - self._config.disagreement_penalty
        return round(self._clamp(confidence), 4)

    def unmatched_classical_confidence(self, classical_confidence: float) -> float:
        self._validate_probability(classical_confidence, "classical_confidence")
        return round(
            self._clamp(classical_confidence * (1.0 - self._config.unmatched_penalty)),
            4,
        )

    def unmatched_yolo_confidence(self, yolo_confidence: float) -> float:
        self._validate_probability(yolo_confidence, "yolo_confidence")
        return round(
            self._clamp(yolo_confidence * (1.0 - self._config.unmatched_penalty)),
            4,
        )

    @staticmethod
    def agreement_score(
        iou: float,
        centroid_distance_px: float | None,
        maximum_centroid_distance_px: float,
    ) -> float:
        if not 0.0 <= iou <= 1.0:
            raise ValueError("iou must be between 0 and 1.")
        if maximum_centroid_distance_px <= 0:
            raise ValueError("maximum_centroid_distance_px must be positive.")
        if centroid_distance_px is None:
            return round(iou, 4)
        if centroid_distance_px < 0:
            raise ValueError("centroid_distance_px cannot be negative.")

        centroid_score = max(
            0.0,
            1.0 - centroid_distance_px / maximum_centroid_distance_px,
        )
        return round(FusionConfidenceScorer._clamp(0.7 * iou + 0.3 * centroid_score), 4)

    @staticmethod
    def scene_confidence(
        candidate_confidences: tuple[float, ...],
        unresolved_candidates: int,
    ) -> float:
        if unresolved_candidates < 0:
            raise ValueError("unresolved_candidates cannot be negative.")
        if not candidate_confidences:
            return 1.0 if unresolved_candidates == 0 else 0.0
        for confidence in candidate_confidences:
            FusionConfidenceScorer._validate_probability(confidence, "candidate confidence")

        mean_confidence = sum(candidate_confidences) / len(candidate_confidences)
        unresolved_penalty = min(
            1.0,
            unresolved_candidates / max(len(candidate_confidences), 1),
        )
        return round(
            FusionConfidenceScorer._clamp(mean_confidence * (1.0 - 0.5 * unresolved_penalty)),
            4,
        )

    @staticmethod
    def _validate_probability(value: float, field_name: str) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{field_name} must be between 0 and 1.")

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))
