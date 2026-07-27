"""
P.C.A.I. — C-005 Classical Counting Cell.

Mission
-------
Produce a truthful classical count from structured candidate observations.

Authority
---------
May count accepted single candidates, exclude artifacts, and require review
when unsupported candidate states are present.

Prohibited
----------
Must not inspect raw pixels, split touching regions, infer hidden pills,
identify medicine, or authorise dispensing.
"""

from __future__ import annotations

from typing import Protocol

from pcai.cells.candidate_observation.contracts import CandidateObservation, CandidateStatus
from pcai.cells.classical_counting.contracts import (
    ClassicalCountingConfiguration,
    ClassicalCountingInput,
)
from pcai.domain.counting import ClassicalCountObservation, CountStatus


class ClassicalCountingCell(Protocol):
    """Public C-005 capability contract."""

    def count(self, input_: ClassicalCountingInput) -> ClassicalCountObservation:
        """Produce one classical count observation."""


class StrictClassicalCountingCell:
    """Conservative deterministic implementation of C-005."""

    def count(self, input_: ClassicalCountingInput) -> ClassicalCountObservation:
        candidates = input_.candidate_set.candidates
        groups = self._group_by_status(candidates)
        reason_codes = self._blocking_reasons(
            groups=groups,
            configuration=input_.configuration,
        )

        accepted_ids = tuple(
            candidate.candidate_id
            for candidate in groups[CandidateStatus.SINGLE_CANDIDATE]
        )
        artifact_ids = tuple(
            candidate.candidate_id for candidate in groups[CandidateStatus.ARTIFACT]
        )
        excluded_ids = tuple(
            candidate.candidate_id
            for candidate in candidates
            if candidate.status is not CandidateStatus.SINGLE_CANDIDATE
        )

        if reason_codes:
            return ClassicalCountObservation(
                frame_id=input_.frame_id,
                status=CountStatus.REVIEW_REQUIRED,
                candidate_count=None,
                accepted_candidate_ids=accepted_ids,
                excluded_candidate_ids=excluded_ids,
                touching_region_ids=self._ids(groups[CandidateStatus.TOUCHING_REGION]),
                unknown_region_ids=self._ids(groups[CandidateStatus.UNKNOWN]),
                partial_region_ids=self._ids(groups[CandidateStatus.PARTIAL_OBJECT]),
                artifact_region_ids=artifact_ids,
                reason_codes=reason_codes,
            )

        return ClassicalCountObservation(
            frame_id=input_.frame_id,
            status=CountStatus.COUNTED,
            candidate_count=len(accepted_ids),
            accepted_candidate_ids=accepted_ids,
            excluded_candidate_ids=artifact_ids,
            touching_region_ids=(),
            unknown_region_ids=(),
            partial_region_ids=(),
            artifact_region_ids=artifact_ids,
            reason_codes=(),
        )

    @staticmethod
    def _group_by_status(
        candidates: tuple[CandidateObservation, ...],
    ) -> dict[CandidateStatus, tuple[CandidateObservation, ...]]:
        return {
            status: tuple(candidate for candidate in candidates if candidate.status is status)
            for status in CandidateStatus
        }

    @staticmethod
    def _blocking_reasons(
        *,
        groups: dict[CandidateStatus, tuple[CandidateObservation, ...]],
        configuration: ClassicalCountingConfiguration,
    ) -> tuple[str, ...]:
        reasons: list[str] = []

        if groups[CandidateStatus.TOUCHING_REGION] and not configuration.allow_touching_regions:
            reasons.append("TOUCHING_REGIONS_PRESENT")
        if groups[CandidateStatus.UNKNOWN] and configuration.reject_unknown_regions:
            reasons.append("UNKNOWN_REGIONS_PRESENT")
        if groups[CandidateStatus.PARTIAL_OBJECT] and configuration.reject_partial_objects:
            reasons.append("PARTIAL_OBJECTS_PRESENT")
        if groups[CandidateStatus.POSSIBLE_STACK] and configuration.reject_possible_stacks:
            reasons.append("POSSIBLE_STACKS_PRESENT")
        if groups[CandidateStatus.FOREIGN_OBJECT]:
            reasons.append("FOREIGN_OBJECTS_PRESENT")

        return tuple(reasons)

    @staticmethod
    def _ids(candidates: tuple[CandidateObservation, ...]) -> tuple[str, ...]:
        return tuple(candidate.candidate_id for candidate in candidates)
