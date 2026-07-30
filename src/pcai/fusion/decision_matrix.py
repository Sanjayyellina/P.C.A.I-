from __future__ import annotations

from dataclasses import dataclass

from .contracts import FusionDecision


@dataclass(frozen=True, slots=True)
class FusionDecisionConfig:
    minimum_accept_confidence: float = 0.82
    minimum_wait_confidence: float = 0.45
    minimum_agreement_score: float = 0.45
    high_confidence_threshold: float = 0.85
    allow_single_source_accept: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.minimum_wait_confidence <= self.minimum_accept_confidence <= 1.0:
            raise ValueError(
                "Confidence thresholds must satisfy 0 <= wait <= accept <= 1."
            )
        if not 0.0 <= self.minimum_agreement_score <= 1.0:
            raise ValueError("minimum_agreement_score must be between 0 and 1.")
        if not 0.0 <= self.high_confidence_threshold <= 1.0:
            raise ValueError("high_confidence_threshold must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class FusionDecisionResult:
    decision: FusionDecision
    reason_codes: tuple[str, ...]


class FusionDecisionMatrix:
    """Convert fused evidence quality into accept, wait, or reject decisions."""

    def __init__(self, config: FusionDecisionConfig | None = None) -> None:
        self._config = config or FusionDecisionConfig()

    def decide_matched(
        self,
        *,
        fused_confidence: float,
        agreement_score: float,
        classical_count: int,
        yolo_count: int,
        classical_confidence: float,
        yolo_confidence: float,
    ) -> FusionDecisionResult:
        self._validate_probability(fused_confidence, "fused_confidence")
        self._validate_probability(agreement_score, "agreement_score")
        self._validate_probability(classical_confidence, "classical_confidence")
        self._validate_probability(yolo_confidence, "yolo_confidence")

        reasons: list[str] = []
        counts_agree = classical_count == yolo_count

        if counts_agree:
            reasons.append("COUNT_AGREEMENT")
        else:
            reasons.append("COUNT_DISAGREEMENT")

        if agreement_score < self._config.minimum_agreement_score:
            reasons.append("GEOMETRIC_AGREEMENT_LOW")

        both_high = (
            classical_confidence >= self._config.high_confidence_threshold
            and yolo_confidence >= self._config.high_confidence_threshold
        )

        if (
            counts_agree
            and agreement_score >= self._config.minimum_agreement_score
            and fused_confidence >= self._config.minimum_accept_confidence
        ):
            reasons.append("MATCHED_EVIDENCE_ACCEPTED")
            return FusionDecisionResult(FusionDecision.ACCEPT, tuple(reasons))

        if not counts_agree and both_high:
            reasons.append("HIGH_CONFIDENCE_CONFLICT")
            return FusionDecisionResult(FusionDecision.WAIT, tuple(reasons))

        if fused_confidence >= self._config.minimum_wait_confidence:
            reasons.append("ADDITIONAL_FRAME_REQUIRED")
            return FusionDecisionResult(FusionDecision.WAIT, tuple(reasons))

        reasons.append("FUSED_CONFIDENCE_TOO_LOW")
        return FusionDecisionResult(FusionDecision.REJECT, tuple(reasons))

    def decide_unmatched(
        self,
        *,
        source: str,
        confidence: float,
    ) -> FusionDecisionResult:
        self._validate_probability(confidence, "confidence")
        normalized_source = source.strip().lower()
        if normalized_source not in {"classical", "yolo"}:
            raise ValueError("source must be either 'classical' or 'yolo'.")

        reasons = [f"UNMATCHED_{normalized_source.upper()}_EVIDENCE"]

        if (
            self._config.allow_single_source_accept
            and confidence >= self._config.minimum_accept_confidence
        ):
            reasons.append("SINGLE_SOURCE_ACCEPTED")
            return FusionDecisionResult(FusionDecision.ACCEPT, tuple(reasons))

        if confidence >= self._config.minimum_wait_confidence:
            reasons.append("SECOND_SOURCE_CONFIRMATION_REQUIRED")
            return FusionDecisionResult(FusionDecision.WAIT, tuple(reasons))

        reasons.append("SINGLE_SOURCE_CONFIDENCE_TOO_LOW")
        return FusionDecisionResult(FusionDecision.REJECT, tuple(reasons))

    def decide_scene(
        self,
        *,
        scene_confidence: float,
        accepted_candidates: int,
        waiting_candidates: int,
        rejected_candidates: int,
    ) -> FusionDecisionResult:
        self._validate_probability(scene_confidence, "scene_confidence")
        for name, value in (
            ("accepted_candidates", accepted_candidates),
            ("waiting_candidates", waiting_candidates),
            ("rejected_candidates", rejected_candidates),
        ):
            if value < 0:
                raise ValueError(f"{name} cannot be negative.")

        reasons: list[str] = []
        if waiting_candidates:
            reasons.append("WAITING_CANDIDATES_PRESENT")
        if rejected_candidates:
            reasons.append("REJECTED_CANDIDATES_PRESENT")

        if waiting_candidates > 0:
            return FusionDecisionResult(FusionDecision.WAIT, tuple(reasons))

        if rejected_candidates > 0:
            if accepted_candidates > 0 and scene_confidence >= self._config.minimum_wait_confidence:
                reasons.append("PARTIAL_SCENE_REQUIRES_RECHECK")
                return FusionDecisionResult(FusionDecision.WAIT, tuple(reasons))
            reasons.append("SCENE_EVIDENCE_REJECTED")
            return FusionDecisionResult(FusionDecision.REJECT, tuple(reasons))

        if scene_confidence >= self._config.minimum_accept_confidence:
            reasons.append("SCENE_ACCEPTED")
            return FusionDecisionResult(FusionDecision.ACCEPT, tuple(reasons))

        if scene_confidence >= self._config.minimum_wait_confidence:
            reasons.append("SCENE_CONFIDENCE_REQUIRES_MORE_FRAMES")
            return FusionDecisionResult(FusionDecision.WAIT, tuple(reasons))

        reasons.append("SCENE_CONFIDENCE_TOO_LOW")
        return FusionDecisionResult(FusionDecision.REJECT, tuple(reasons))

    @staticmethod
    def _validate_probability(value: float, field_name: str) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{field_name} must be between 0 and 1.")
