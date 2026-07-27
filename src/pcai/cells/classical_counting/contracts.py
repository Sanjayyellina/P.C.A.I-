"""P.C.A.I. — C-005 Classical Counting Cell contracts."""

from __future__ import annotations

from dataclasses import dataclass

from pcai.cells.candidate_observation.contracts import CandidateSet
from pcai.shared.identifiers import FrameId


@dataclass(frozen=True, slots=True)
class ClassicalCountingConfiguration:
    allow_touching_regions: bool
    reject_unknown_regions: bool
    reject_partial_objects: bool
    reject_possible_stacks: bool


@dataclass(frozen=True, slots=True)
class ClassicalCountingInput:
    frame_id: FrameId
    candidate_set: CandidateSet
    configuration: ClassicalCountingConfiguration
