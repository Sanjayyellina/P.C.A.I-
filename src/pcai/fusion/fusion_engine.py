from __future__ import annotations

from dataclasses import dataclass

from pcai.classical_estimator.contracts import (
    ClassicalCountEstimate,
    HypothesisDecision,
    TabletHypothesis,
)
from pcai.segmentation.contracts import CandidateObservation
from pcai.yolo_engine.contracts import YoloInferenceResult, YoloInstance

from .association import AssociationConfig, CandidateAssociator
from .confidence import FusionConfidenceScorer
from .contracts import (
    FusedCandidateHypothesis,
    FusedCountEstimate,
    FusionDecision,
)
from .decision_matrix import FusionDecisionMatrix


@dataclass(frozen=True, slots=True)
class EvidenceFusionConfig:
    maximum_centroid_distance_px: float = 80.0
    yolo_instance_count: int = 1

    def __post_init__(self) -> None:
        if self.maximum_centroid_distance_px <= 0:
            raise ValueError("maximum_centroid_distance_px must be positive.")
        if self.yolo_instance_count <= 0:
            raise ValueError("yolo_instance_count must be positive.")


class EvidenceFusionEngine:
    """Fuse classical count hypotheses with YOLO instance evidence."""

    def __init__(
        self,
        config: EvidenceFusionConfig | None = None,
        associator: CandidateAssociator | None = None,
        confidence_scorer: FusionConfidenceScorer | None = None,
        decision_matrix: FusionDecisionMatrix | None = None,
    ) -> None:
        self._config = config or EvidenceFusionConfig()
        self._associator = associator or CandidateAssociator(
            AssociationConfig(
                maximum_centroid_distance_px=self._config.maximum_centroid_distance_px
            )
        )
        self._confidence = confidence_scorer or FusionConfidenceScorer()
        self._decisions = decision_matrix or FusionDecisionMatrix()

    def fuse(
        self,
        classical_candidates: tuple[CandidateObservation, ...],
        classical_estimate: ClassicalCountEstimate,
        yolo_result: YoloInferenceResult,
    ) -> FusedCountEstimate:
        associations = self._associator.associate(
            classical_candidates,
            yolo_result.instances,
        )

        classical_by_id = {
            hypothesis.candidate_id: hypothesis
            for hypothesis in classical_estimate.hypotheses
        }
        yolo_by_id = {
            instance.identifier: instance
            for instance in yolo_result.instances
        }

        fused_candidates: list[FusedCandidateHypothesis] = []

        for association in associations.associations:
            if association.matched:
                assert association.classical_candidate_id is not None
                assert association.yolo_instance_id is not None
                classical = classical_by_id.get(association.classical_candidate_id)
                yolo = yolo_by_id.get(association.yolo_instance_id)
                if classical is None or yolo is None:
                    continue
                fused_candidates.append(
                    self._fuse_matched(
                        len(fused_candidates),
                        classical,
                        yolo,
                        association.iou,
                        association.centroid_distance_px,
                    )
                )
                continue

            if association.classical_candidate_id is not None:
                classical = classical_by_id.get(association.classical_candidate_id)
                if classical is not None:
                    fused_candidates.append(
                        self._fuse_unmatched_classical(
                            len(fused_candidates),
                            classical,
                        )
                    )
                continue

            if association.yolo_instance_id is not None:
                yolo = yolo_by_id.get(association.yolo_instance_id)
                if yolo is not None:
                    fused_candidates.append(
                        self._fuse_unmatched_yolo(
                            len(fused_candidates),
                            yolo,
                        )
                    )

        accepted = tuple(
            item for item in fused_candidates if item.decision is FusionDecision.ACCEPT
        )
        waiting = tuple(
            item for item in fused_candidates if item.decision is FusionDecision.WAIT
        )
        rejected = tuple(
            item for item in fused_candidates if item.decision is FusionDecision.REJECT
        )

        scene_confidence = self._confidence.scene_confidence(
            tuple(item.confidence for item in fused_candidates),
            unresolved_candidates=len(waiting) + len(rejected),
        )
        scene_decision = self._decisions.decide_scene(
            scene_confidence=scene_confidence,
            accepted_candidates=len(accepted),
            waiting_candidates=len(waiting),
            rejected_candidates=len(rejected),
        )

        total_count = sum(item.estimated_count for item in accepted)
        reasons = list(scene_decision.reason_codes)
        if classical_estimate.review_candidates:
            reasons.append("CLASSICAL_REVIEW_CANDIDATES_PRESENT")
        if yolo_result.reason_codes:
            reasons.extend(yolo_result.reason_codes)
        if associations.unmatched_classical_ids:
            reasons.append("UNMATCHED_CLASSICAL_CANDIDATES_PRESENT")
        if associations.unmatched_yolo_ids:
            reasons.append("UNMATCHED_YOLO_INSTANCES_PRESENT")

        return FusedCountEstimate(
            frame_sequence=yolo_result.frame_sequence,
            camera_id=yolo_result.camera_id,
            total_count=total_count,
            confidence=scene_confidence,
            decision=scene_decision.decision,
            candidates=tuple(fused_candidates),
            matched_pairs=associations.matched_pairs,
            unmatched_classical=len(associations.unmatched_classical_ids),
            unmatched_yolo=len(associations.unmatched_yolo_ids),
            reason_codes=tuple(dict.fromkeys(reasons)),
        )

    def _fuse_matched(
        self,
        identifier: int,
        classical: TabletHypothesis,
        yolo: YoloInstance,
        iou: float,
        centroid_distance_px: float | None,
    ) -> FusedCandidateHypothesis:
        yolo_count = self._config.yolo_instance_count
        counts_agree = classical.estimated_count == yolo_count
        agreement = self._confidence.agreement_score(
            iou,
            centroid_distance_px,
            self._config.maximum_centroid_distance_px,
        )
        fused_confidence = self._confidence.matched_confidence(
            classical.confidence,
            yolo.confidence,
            agreement,
            counts_agree,
        )
        decision = self._decisions.decide_matched(
            fused_confidence=fused_confidence,
            agreement_score=agreement,
            classical_count=classical.estimated_count,
            yolo_count=yolo_count,
            classical_confidence=classical.confidence,
            yolo_confidence=yolo.confidence,
        )

        estimated_count = self._resolve_count(
            classical_count=classical.estimated_count,
            classical_confidence=classical.confidence,
            yolo_count=yolo_count,
            yolo_confidence=yolo.confidence,
        )
        reasons = list(classical.reason_codes)
        reasons.extend(decision.reason_codes)

        return FusedCandidateHypothesis(
            identifier=identifier,
            classical_candidate_id=classical.candidate_id,
            yolo_instance_id=yolo.identifier,
            estimated_count=estimated_count,
            confidence=fused_confidence,
            decision=decision.decision,
            classical_confidence=classical.confidence,
            yolo_confidence=yolo.confidence,
            agreement_score=agreement,
            reason_codes=tuple(dict.fromkeys(reasons)),
        )

    def _fuse_unmatched_classical(
        self,
        identifier: int,
        classical: TabletHypothesis,
    ) -> FusedCandidateHypothesis:
        confidence = self._confidence.unmatched_classical_confidence(
            classical.confidence
        )
        decision = self._decisions.decide_unmatched(
            source="classical",
            confidence=confidence,
        )
        reasons = list(classical.reason_codes)
        reasons.extend(decision.reason_codes)
        if classical.decision is HypothesisDecision.REJECT:
            reasons.append("CLASSICAL_SOURCE_REJECTED")

        return FusedCandidateHypothesis(
            identifier=identifier,
            classical_candidate_id=classical.candidate_id,
            yolo_instance_id=None,
            estimated_count=classical.estimated_count,
            confidence=confidence,
            decision=decision.decision,
            classical_confidence=classical.confidence,
            yolo_confidence=None,
            agreement_score=0.0,
            reason_codes=tuple(dict.fromkeys(reasons)),
        )

    def _fuse_unmatched_yolo(
        self,
        identifier: int,
        yolo: YoloInstance,
    ) -> FusedCandidateHypothesis:
        confidence = self._confidence.unmatched_yolo_confidence(yolo.confidence)
        decision = self._decisions.decide_unmatched(
            source="yolo",
            confidence=confidence,
        )

        return FusedCandidateHypothesis(
            identifier=identifier,
            classical_candidate_id=None,
            yolo_instance_id=yolo.identifier,
            estimated_count=self._config.yolo_instance_count,
            confidence=confidence,
            decision=decision.decision,
            classical_confidence=None,
            yolo_confidence=yolo.confidence,
            agreement_score=0.0,
            reason_codes=decision.reason_codes,
        )

    @staticmethod
    def _resolve_count(
        *,
        classical_count: int,
        classical_confidence: float,
        yolo_count: int,
        yolo_confidence: float,
    ) -> int:
        if classical_count == yolo_count:
            return classical_count
        if classical_confidence >= yolo_confidence:
            return classical_count
        return yolo_count
