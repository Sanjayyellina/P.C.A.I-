from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .feature_extraction import CandidateFeatures


@dataclass(frozen=True, slots=True)
class TouchingTabletConfig:
    reference_single_area_px2: float
    area_pair_threshold: float = 1.55
    area_cluster_threshold: float = 2.45
    minimum_solidity_for_single: float = 0.90
    minimum_circularity_for_single: float = 0.55
    maximum_single_aspect_ratio: float = 2.4
    minimum_distance_peak_ratio: float = 0.22

    def __post_init__(self) -> None:
        if self.reference_single_area_px2 <= 0:
            raise ValueError("reference_single_area_px2 must be positive.")
        if not 1.0 < self.area_pair_threshold < self.area_cluster_threshold:
            raise ValueError("Area thresholds must satisfy 1 < pair < cluster.")
        if not 0.0 <= self.minimum_solidity_for_single <= 1.0:
            raise ValueError("minimum_solidity_for_single must be between 0 and 1.")
        if not 0.0 <= self.minimum_circularity_for_single <= 1.0:
            raise ValueError("minimum_circularity_for_single must be between 0 and 1.")
        if self.maximum_single_aspect_ratio < 1.0:
            raise ValueError("maximum_single_aspect_ratio must be at least 1.")
        if self.minimum_distance_peak_ratio < 0:
            raise ValueError("minimum_distance_peak_ratio cannot be negative.")


@dataclass(frozen=True, slots=True)
class TouchingTabletAssessment:
    identifier: int
    estimated_count: int
    confidence: float
    requires_split: bool
    reason_codes: tuple[str, ...]


class TouchingTabletAnalyzer:
    """Estimate whether a candidate contains one or multiple touching tablets."""

    def __init__(self, config: TouchingTabletConfig) -> None:
        self._config = config

    def assess(self, features: CandidateFeatures) -> TouchingTabletAssessment:
        area_ratio = features.area_px2 / self._config.reference_single_area_px2
        reasons: list[str] = []

        shape_consistent_single = (
            features.solidity >= self._config.minimum_solidity_for_single
            and features.circularity >= self._config.minimum_circularity_for_single
            and features.aspect_ratio <= self._config.maximum_single_aspect_ratio
        )

        if area_ratio < self._config.area_pair_threshold and shape_consistent_single:
            return TouchingTabletAssessment(
                identifier=features.identifier,
                estimated_count=1,
                confidence=self._single_confidence(area_ratio, features),
                requires_split=False,
                reason_codes=(),
            )

        if area_ratio >= self._config.area_pair_threshold:
            reasons.append("AREA_ABOVE_SINGLE")
        if features.solidity < self._config.minimum_solidity_for_single:
            reasons.append("SOLIDITY_LOW")
        if features.circularity < self._config.minimum_circularity_for_single:
            reasons.append("CIRCULARITY_LOW")
        if features.aspect_ratio > self._config.maximum_single_aspect_ratio:
            reasons.append("ASPECT_RATIO_HIGH")

        distance_ratio = self._distance_peak_ratio(features)
        if distance_ratio < self._config.minimum_distance_peak_ratio:
            reasons.append("DISTANCE_PEAK_LOW")

        estimated_count = self._estimate_count(area_ratio)
        requires_split = estimated_count > 1
        confidence = self._cluster_confidence(area_ratio, estimated_count, features)

        return TouchingTabletAssessment(
            identifier=features.identifier,
            estimated_count=estimated_count,
            confidence=confidence,
            requires_split=requires_split,
            reason_codes=tuple(reasons),
        )

    def _estimate_count(self, area_ratio: float) -> int:
        if area_ratio < self._config.area_pair_threshold:
            return 1
        if area_ratio < self._config.area_cluster_threshold:
            return 2
        return max(2, int(round(area_ratio)))

    @staticmethod
    def _distance_peak_ratio(features: CandidateFeatures) -> float:
        if features.minor_axis_px is not None and features.minor_axis_px > 0:
            return features.distance_peak / features.minor_axis_px
        if features.major_axis_px is not None and features.major_axis_px > 0:
            return features.distance_peak / features.major_axis_px
        return 0.0

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _single_confidence(
        self,
        area_ratio: float,
        features: CandidateFeatures,
    ) -> float:
        area_score = self._clamp(1.0 - abs(area_ratio - 1.0))
        shape_score = (
            0.4 * features.solidity
            + 0.35 * features.circularity
            + 0.25 * self._clamp(1.0 / max(features.aspect_ratio, 1.0))
        )
        return round(self._clamp(0.55 * area_score + 0.45 * shape_score), 4)

    def _cluster_confidence(
        self,
        area_ratio: float,
        estimated_count: int,
        features: CandidateFeatures,
    ) -> float:
        expected_ratio = float(estimated_count)
        area_score = self._clamp(1.0 - abs(area_ratio - expected_ratio) / max(expected_ratio, 1.0))
        irregularity_score = self._clamp(
            0.5 * (1.0 - features.solidity)
            + 0.3 * (1.0 - features.circularity)
            + 0.2 * self._clamp((features.aspect_ratio - 1.0) / 3.0)
        )
        return round(self._clamp(0.7 * area_score + 0.3 * irregularity_score), 4)
