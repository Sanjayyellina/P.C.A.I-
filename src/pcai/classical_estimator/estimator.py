from __future__ import annotations

from dataclasses import dataclass
from math import exp

from pcai.segmentation.feature_extraction import CandidateFeatures
from pcai.segmentation.touching_tablets import TouchingTabletAssessment
from pcai.segmentation.watershed_split import WatershedSplitResult

from .contracts import (
    ClassicalCountEstimate,
    CountProbability,
    HypothesisDecision,
    TabletHypothesis,
)


@dataclass(frozen=True, slots=True)
class ClassicalEstimatorConfig:
    minimum_accept_confidence: float = 0.80
    minimum_review_confidence: float = 0.45
    maximum_supported_count_per_candidate: int = 12
    watershed_weight: float = 0.45
    area_weight: float = 0.35
    shape_weight: float = 0.20

    def __post_init__(self) -> None:
        if not 0.0 <= self.minimum_review_confidence <= self.minimum_accept_confidence <= 1.0:
            raise ValueError(
                "Confidence thresholds must satisfy 0 <= review <= accept <= 1."
            )
        if self.maximum_supported_count_per_candidate <= 0:
            raise ValueError("maximum_supported_count_per_candidate must be positive.")
        weights = self.watershed_weight + self.area_weight + self.shape_weight
        if abs(weights - 1.0) > 1e-6:
            raise ValueError("Estimator weights must sum to 1.0.")
        if min(self.watershed_weight, self.area_weight, self.shape_weight) < 0:
            raise ValueError("Estimator weights cannot be negative.")


class ClassicalTabletEstimator:
    """Convert deterministic candidate evidence into count hypotheses."""

    def __init__(self, config: ClassicalEstimatorConfig | None = None) -> None:
        self._config = config or ClassicalEstimatorConfig()

    def estimate_candidate(
        self,
        features: CandidateFeatures,
        touching: TouchingTabletAssessment,
        watershed: WatershedSplitResult | None = None,
    ) -> TabletHypothesis:
        area_count = self._bounded_count(round(max(1.0, features.estimated_multiplicity)))
        touching_count = self._bounded_count(touching.estimated_count)
        watershed_count = (
            self._bounded_count(len(watershed.regions))
            if watershed is not None and watershed.split_applied
            else None
        )

        score_by_count: dict[int, float] = {}
        self._add_score(
            score_by_count,
            area_count,
            self._config.area_weight * self._area_confidence(features, area_count),
        )
        self._add_score(
            score_by_count,
            touching_count,
            self._config.shape_weight * touching.confidence,
        )

        reasons = list(touching.reason_codes)
        split_region_count: int | None = None
        if watershed_count is not None:
            split_region_count = watershed_count
            self._add_score(
                score_by_count,
                watershed_count,
                self._config.watershed_weight,
            )
            reasons.append("WATERSHED_SPLIT_CONFIRMED")
        else:
            self._add_score(
                score_by_count,
                touching_count,
                self._config.watershed_weight * 0.45,
            )
            if touching.requires_split:
                reasons.append("SPLIT_UNCONFIRMED")

        shape_single_score = self._single_shape_score(features)
        self._add_score(
            score_by_count,
            1,
            self._config.shape_weight * shape_single_score,
        )

        probabilities = self._normalize_scores(score_by_count)
        best = max(probabilities, key=lambda item: item.probability)
        confidence = best.probability
        decision = self._decision(confidence, reasons)

        if decision is HypothesisDecision.REJECT:
            reasons.append("CLASSICAL_CONFIDENCE_TOO_LOW")
        elif decision is HypothesisDecision.REVIEW:
            reasons.append("CLASSICAL_REVIEW_REQUIRED")

        return TabletHypothesis(
            candidate_id=features.identifier,
            estimated_count=best.count,
            confidence=round(confidence, 4),
            decision=decision,
            probabilities=probabilities,
            reason_codes=tuple(dict.fromkeys(reasons)),
            split_region_count=split_region_count,
        )

    def estimate_total(
        self,
        hypotheses: tuple[TabletHypothesis, ...],
    ) -> ClassicalCountEstimate:
        accepted = tuple(
            item for item in hypotheses if item.decision is HypothesisDecision.ACCEPT
        )
        review = tuple(
            item for item in hypotheses if item.decision is HypothesisDecision.REVIEW
        )
        rejected = tuple(
            item for item in hypotheses if item.decision is HypothesisDecision.REJECT
        )

        total = sum(item.estimated_count for item in accepted)
        reasons: list[str] = []
        if review:
            reasons.append("REVIEW_CANDIDATES_PRESENT")
        if rejected:
            reasons.append("REJECTED_CANDIDATES_PRESENT")

        if not hypotheses:
            confidence = 1.0
        else:
            accepted_confidence = sum(item.confidence for item in accepted)
            unresolved_penalty = 0.5 * len(review) + 1.0 * len(rejected)
            confidence = max(
                0.0,
                min(
                    1.0,
                    (accepted_confidence - unresolved_penalty) / len(hypotheses),
                ),
            )

        return ClassicalCountEstimate(
            total_count=total,
            confidence=round(confidence, 4),
            hypotheses=hypotheses,
            accepted_candidates=len(accepted),
            review_candidates=len(review),
            rejected_candidates=len(rejected),
            reason_codes=tuple(reasons),
        )

    def _decision(
        self,
        confidence: float,
        reasons: list[str],
    ) -> HypothesisDecision:
        if confidence >= self._config.minimum_accept_confidence and "SPLIT_UNCONFIRMED" not in reasons:
            return HypothesisDecision.ACCEPT
        if confidence >= self._config.minimum_review_confidence:
            return HypothesisDecision.REVIEW
        return HypothesisDecision.REJECT

    def _bounded_count(self, count: int) -> int:
        return max(1, min(self._config.maximum_supported_count_per_candidate, int(count)))

    @staticmethod
    def _add_score(score_by_count: dict[int, float], count: int, score: float) -> None:
        score_by_count[count] = score_by_count.get(count, 0.0) + max(0.0, score)

    @staticmethod
    def _single_shape_score(features: CandidateFeatures) -> float:
        aspect_score = 1.0 / max(features.aspect_ratio, 1.0)
        return max(
            0.0,
            min(
                1.0,
                0.45 * features.solidity
                + 0.35 * features.circularity
                + 0.20 * aspect_score,
            ),
        )

    @staticmethod
    def _area_confidence(features: CandidateFeatures, count: int) -> float:
        expected = float(max(count, 1))
        ratio = max(features.estimated_multiplicity, 0.0)
        return max(0.0, min(1.0, exp(-abs(ratio - expected))))

    @staticmethod
    def _normalize_scores(score_by_count: dict[int, float]) -> tuple[CountProbability, ...]:
        if not score_by_count:
            return (CountProbability(count=1, probability=1.0),)
        total = sum(score_by_count.values())
        if total <= 0:
            return (CountProbability(count=1, probability=1.0),)
        probabilities = [
            CountProbability(count=count, probability=score / total)
            for count, score in sorted(score_by_count.items())
        ]
        correction = 1.0 - sum(item.probability for item in probabilities)
        if probabilities and abs(correction) > 1e-12:
            last = probabilities[-1]
            probabilities[-1] = CountProbability(
                count=last.count,
                probability=max(0.0, min(1.0, last.probability + correction)),
            )
        return tuple(probabilities)
