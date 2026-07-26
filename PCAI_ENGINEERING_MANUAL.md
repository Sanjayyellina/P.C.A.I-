---
title: "P.C.A.I. Engineering Manual"
subtitle: "Implementation Contracts, Engineering Standards and Executable System Design"
version: "0.1"
status: "Active engineering working baseline"
date: "2026-07-26"
relationship_to_architecture_bible: "Derived from PCAI_ARCHITECTURE_BIBLE.md; may evolve through engineering evidence without silently rewriting the Bible"
---

# P.C.A.I. Engineering Manual

## Purpose

This manual is the implementation-facing source of truth for engineers building P.C.A.I. It translates the Architecture Bible into concrete domain contracts, module boundaries, commands, events, invariants, failure semantics, interfaces, test requirements and code-quality expectations.

The Architecture Bible remains the governing product and architecture baseline. This Engineering Manual is deliberately allowed to evolve faster because implementation work may reveal better structures, naming, boundaries or sequencing. Any engineering decision that changes a binding architectural principle, human-authority rule, trust boundary, intended use, data-authority rule, security control or validated operating envelope must be promoted through an Architecture Decision Record and, where appropriate, reflected back into the Architecture Bible.

This file must be understandable to a new engineer who has not participated in prior discussions. It therefore explains not only what P.C.A.I. should implement, but also why the system is structured this way, what assumptions remain unproven, what behaviours are prohibited and how each implementation decision preserves safety, evidence and replayability.

## Governing engineering principle

> P.C.A.I. never claims certainty beyond its evidence. It either produces a result inside a validated operating envelope, or it refuses safely and requests review.

## Relationship between documents

| Document | Purpose | Change rate | Authority |
|---|---|---|---|
| `PCAI_ARCHITECTURE_BIBLE.md` | Product vision, architecture baseline, non-negotiable principles and long-term system design. | Slow | Governing architecture source. |
| `PCAI_ENGINEERING_MANUAL.md` | Concrete implementation contracts, refined engineering design, coding standards and build sequence. | Moderate | Engineering source of truth. |
| ADRs | Explain material decisions, alternatives and consequences. | As needed | Decision authority for accepted changes. |
| Requirements and tests | Trace implementation to intended behaviour and evidence. | Continuous | Verification authority. |

## Decision-status vocabulary

| Status | Meaning |
|---|---|
| **APPROVED** | Binding for the current engineering baseline. |
| **REQUIRED** | Must exist before the affected capability can be released. |
| **PROPOSED** | Preferred direction that still requires implementation or benchmark evidence. |
| **EXPERIMENTAL** | Hypothesis to be tested under controlled conditions. |
| **DEFERRED** | Intentionally outside the current implementation scope. |
| **PROHIBITED** | Must not be implemented without formally changing architecture and intended use. |

# 1. Engineering philosophy

## 1.1 Build evidence before automation

P.C.A.I. is not built around a model response. It is built around a chain of observation, fact, evidence, verification, policy and human confirmation. The codebase must preserve that chain explicitly.

A capability may fail, disagree or return unknown. The surrounding system must remain understandable and recoverable. No component may convert uncertainty into a convenient result merely to keep a workflow moving.

## 1.2 Domain truth is separate from infrastructure

The domain defines what a valid pharmacy counting workflow means. FastAPI, PostgreSQL, OpenCV, TensorRT, React, Docker and local LLM runtimes are replaceable implementation technologies.

Domain code must not import web frameworks, database frameworks, model runtimes or host-specific libraries. Infrastructure implements interfaces owned by the application and domain layers.

## 1.3 Workflow state is not model state

The `CountingSession` aggregate governs workflow truth. It does not perform image processing, OCR, identification, policy interpretation or file storage. It only accepts evidence and decisions through typed contracts and enforces whether the workflow may advance.

## 1.4 Human authority remains explicit

A machine proposal is not a human decision. A human correction does not erase the machine proposal. A final confirmation must identify the exact evidence and decision version that the human reviewed.

## 1.5 Beautiful engineering is a correctness tool

Code quality is not decorative. Clear naming, narrow interfaces, immutable value objects, explicit units, stable error codes, deterministic domain behaviour and well-structured tests reduce ambiguity and make future validation possible.

The codebase should be pleasant to read because engineers must be able to inspect it under pressure, during incidents, audits and model failures.

# 2. Initial repository shape

The repository should begin with only the modules required by the first executable vertical slice.

```text
pcai/
  README.md
  PCAI_ARCHITECTURE_BIBLE.md
  PCAI_ENGINEERING_MANUAL.md
  pyproject.toml
  package.json

  apps/
    api/
    web/
    site_agent/

  pcai_core/
    identity/
    stations/
    sessions/
    observations/
    evidence/
    decisions/
    events/
    replay/

  contracts/
    api/
    commands/
    events/
    capabilities/
    agents/

  infrastructure/
    postgres/
    object_store/
    security/
    telemetry/

  tests/
    unit/
    property/
    contract/
    integration/
    resilience/
    security/
    e2e/
```

Do not create empty future modules merely to mirror the complete long-term architecture. New folders should appear when a real contract and responsibility exist.

# 3. First executable vertical slice

The first vertical slice proves the trust architecture before implementing pill counting.

An authorised user must be able to:

1. Open P.C.A.I. in a browser.
2. Authenticate.
3. Create a session.
4. Prepare a station and capture request.
5. Request a frame from a paired site agent.
6. Store that frame in content-addressed evidence storage.
7. Run deterministic frame-quality checks.
8. Record every significant step as immutable events.
9. View the current session and replay its timeline.
10. Ask the local assistant to explain the structured frame-quality result using read-only tools.
11. Complete, cancel or safely recover the session according to state.

The first slice intentionally excludes pill counting and medicine identification. It proves the architecture that later makes those capabilities trustworthy.

# 4. CountingSession aggregate

## 4.1 Responsibility

`CountingSession` is the authoritative workflow aggregate for one bounded pharmacy counting operation.

It owns:

- lifecycle state;
- pharmacy ownership;
- assigned station reference;
- expected medicine context reference;
- target count requirement and value;
- active capture request reference;
- accepted frame references;
- current processing-run reference;
- current evidence-bundle reference;
- current machine-decision reference;
- current human-decision reference;
- review reasons;
- terminal reason;
- aggregate stream revision.

It does not own:

- image bytes;
- masks, annotations or OCR crops;
- model artefacts;
- medicine-profile definitions;
- user credentials;
- station calibration objects;
- quality-measurement payloads;
- projections;
- technical logs;
- datasets.

Those objects are referenced through immutable identifiers and versioned provenance.

## 4.2 State model

The durable lifecycle states are:

```text
CREATED
PREPARING
READY
CAPTURING
PROCESSING
VERIFYING
REVIEW_REQUIRED
VERIFIED
CONFIRMED
COMPLETED
ARCHIVED
CANCELLED
FAILED
ABANDONED
```

`CAPTURE_REQUESTED` and `FRAME_RECEIVED` are not aggregate lifecycle states. They are durable facts represented through events and fields while the aggregate remains in `CAPTURING`.

### State meaning

| State | Meaning |
|---|---|
| `CREATED` | Session exists but preparation has not begun. |
| `PREPARING` | Required context, station and readiness checks are being assembled. |
| `READY` | Required prerequisites are valid and capture may begin. |
| `CAPTURING` | A capture workflow is active or accepted frames are being assembled. |
| `PROCESSING` | Vision, quality, counting, OCR or identification capabilities are producing observations and hypotheses. |
| `VERIFYING` | Evidence sufficiency, contradictions and deterministic policy are being evaluated. |
| `REVIEW_REQUIRED` | The workflow cannot safely advance without corrective action or authorised human resolution. |
| `VERIFIED` | The machine workflow has produced a policy-permitted evidence-supported proposal. |
| `CONFIRMED` | An authorised human has explicitly accepted, corrected or manually resolved the result. |
| `COMPLETED` | The final decision and required evidence are durable and the operational workflow is closed. |
| `ARCHIVED` | The completed session has moved into long-term lifecycle handling; history remains immutable and queryable. |
| `CANCELLED` | An authorised actor intentionally stopped the workflow. |
| `FAILED` | An unrecoverable technical or integrity failure terminated the workflow. |
| `ABANDONED` | A governed inactivity policy closed the workflow after recovery review. |

### Allowed transitions

```text
CREATED -> PREPARING | CANCELLED
PREPARING -> READY | REVIEW_REQUIRED | CANCELLED | FAILED
READY -> CAPTURING | CANCELLED | FAILED
CAPTURING -> PROCESSING | READY | REVIEW_REQUIRED | CANCELLED | FAILED
PROCESSING -> VERIFYING | REVIEW_REQUIRED | FAILED
VERIFYING -> VERIFIED | REVIEW_REQUIRED | FAILED
REVIEW_REQUIRED -> PREPARING | READY | CAPTURING | PROCESSING | CONFIRMED | CANCELLED | FAILED
VERIFIED -> CONFIRMED | REVIEW_REQUIRED | FAILED
CONFIRMED -> COMPLETED | REVIEW_REQUIRED | FAILED
COMPLETED -> ARCHIVED
```

No transition not listed here is permitted.

## 4.3 Core invariants

### Ownership

- Every session belongs to exactly one pharmacy.
- Pharmacy ownership is immutable.
- A station must belong to the same pharmacy.
- A station may be assigned only in `CREATED` or `PREPARING`.
- Station assignment becomes immutable after the first capture request.
- Changing station after capture begins requires cancelling the session and creating a new one.

### Preparation

A session may enter `READY` only when:

- the station is active;
- the paired site agent is trusted;
- the camera identity is known;
- required calibration is valid;
- the camera configuration matches the approved manifest;
- evidence storage has sufficient safe capacity;
- the event store is writable;
- expected medicine context is present when required by the workflow;
- target count is present when required by the workflow.

### Target count

The aggregate stores:

```text
target_count_requirement = REQUIRED | OPTIONAL | NOT_APPLICABLE
target_count = positive integer or null
```

Workflow configuration determines whether a target count is required.

### Capture

A frame may be accepted only when:

- the session is in `CAPTURING`;
- a current capture request exists;
- the request is unexpired;
- station and device identity match the request;
- request nonce and source sequence are valid;
- object bytes are durably stored and hash verified;
- calibration and camera configuration match the request;
- the upload is not a replay with conflicting bytes.

A duplicate upload with the same request, sequence and hash returns the original accepted result. A repeated sequence with different bytes is an integrity incident.

### Processing

Processing may begin only when:

- at least one required frame is durably registered;
- all required object hashes verify;
- the frame set has not been invalidated;
- required capability providers are approved;
- the resource scheduler admits the work.

Only one processing run may be current. Results from superseded processing runs may remain historical but cannot become current decisions.

### Verification

A session may enter `VERIFIED` only when:

- required frame-quality checks pass;
- the station remains inside the approved operating envelope;
- required count evidence exists;
- required identity evidence exists for the configured workflow;
- no unresolved hard contradiction exists;
- verification returns a passing result for required dimensions;
- deterministic policy permits a machine proposal;
- evidence, model, profile, calibration, policy and configuration provenance are durable;
- the decision references the current processing run.

### Human confirmation

A session may enter `CONFIRMED` only when:

- the actor has the required role;
- the current machine decision or review state is explicit;
- count and identity outcomes are confirmed separately;
- the human was shown the referenced evidence bundle;
- no non-overridable policy block exists;
- the confirmation identifies the exact current decision and evidence versions;
- the command carries an idempotency key.

A later change to the relevant evidence, expected medicine, target context or processing run invalidates the confirmation and returns the session to `REVIEW_REQUIRED`.

### Completion

A session may enter `COMPLETED` only when:

- current state is `CONFIRMED`;
- final human decision is durable;
- all required evidence objects exist and pass integrity checks;
- no unresolved blocking incident exists;
- the completion event and outbox entry can commit atomically.

Projection success is not a transactional precondition for completion. A projection failure creates degraded operational status but does not undo a committed completion.

## 4.4 Session-owned state

Prefer references over duplicated derived values.

```text
session_id
pharmacy_id
station_id
created_by
created_at
current_state
expected_medicine_profile_id
expected_medicine_profile_version
expected_context_source
target_count_requirement
target_count
active_capture_request_id
capture_request_status
accepted_frame_ids
current_frame_set_id
current_processing_run_id
current_evidence_bundle_id
current_machine_decision_id
current_human_decision_id
review_reason_codes
terminal_reason_code
stream_revision
```

Final count and identity values belong in decision records and projections, not duplicated aggregate fields.

## 4.5 Commands

The initial command set is:

```text
CreateSession
AssignStation
SelectExpectedMedicine
ResetSessionContext
SetTargetCount
PrepareSession
RequestCapture
RegisterCapturedFrame
RecordFrameQualityAssessment
RequestRecapture
RecordAuthorisedQualityOverride
StartProcessingRun
RecordEvidenceBundle
StartVerification
RecordVerificationResult
RecordPolicyResult
ProposeMachineDecision
RequireReview
RecordHumanDecision
CompleteSession
ArchiveSession
CancelSession
MarkSessionFailed
AbandonSession
```

Browser-facing commands are distinct from internal process-manager actions. `StartProcessingRun`, `RecordEvidenceBundle`, `StartVerification`, `RecordVerificationResult`, `RecordPolicyResult` and `ProposeMachineDecision` are normally invoked by trusted application services, not directly by the browser.

## 4.6 Context reset

Changing expected medicine or other context after accepted evidence exists requires `ResetSessionContext`.

The reset may emit:

```text
session.expected_medicine.changed
session.processing_results.superseded
evidence.bundle.superseded
decision.machine.superseded
decision.human_confirmation.invalidated
```

Only applicable events are emitted. Existing observations remain historical and replayable but cannot automatically support the new context.

## 4.7 Review-reason codes

```text
FRAME_BLUR
FRAME_OVEREXPOSED
FRAME_UNDEREXPOSED
TRAY_NOT_VISIBLE
CALIBRATION_INVALID
CAMERA_CONFIGURATION_MISMATCH
OBJECTS_TOUCHING
OBJECTS_STACKED
OCCLUSION_UNRESOLVED
FOREIGN_OBJECT_DETECTED
MIXED_POPULATION_DETECTED
COUNT_METHOD_DISAGREEMENT
IMPRINT_UNREADABLE
IMPRINT_CONTRADICTION
EXPECTED_MEDICINE_MISMATCH
UNKNOWN_MEDICINE
OUTSIDE_OPERATING_ENVELOPE
MODEL_UNAVAILABLE
CAPABILITY_TIMEOUT
EVIDENCE_INCOMPLETE
EVIDENCE_INTEGRITY_FAILURE
POLICY_BLOCK
HUMAN_REVIEW_REQUESTED
```

These are stable machine-readable codes. User-facing copy may evolve independently.

## 4.8 Failure codes

```text
SESSION_NOT_FOUND
SESSION_TERMINAL
SESSION_INVALID_TRANSITION
SESSION_STATION_REQUIRED
STATION_NOT_FOUND
STATION_TENANT_MISMATCH
STATION_DISABLED
CAMERA_UNAVAILABLE
CALIBRATION_REQUIRED
CALIBRATION_EXPIRED
CAMERA_CONFIGURATION_INVALID
CAPTURE_REQUEST_NOT_FOUND
CAPTURE_REQUEST_EXPIRED
CAPTURE_REQUEST_MISMATCH
CAPTURE_REPLAY_DETECTED
FRAME_HASH_MISMATCH
FRAME_OBJECT_MISSING
FRAME_ALREADY_REGISTERED
PROCESSING_ALREADY_ACTIVE
PROCESSING_RUN_SUPERSEDED
MODEL_NOT_APPROVED
MODEL_UNAVAILABLE
RESOURCE_EXHAUSTED
EVIDENCE_INCOMPLETE
EVIDENCE_CONTRADICTORY
EVIDENCE_BUNDLE_SUPERSEDED
POLICY_BLOCKED
CONFIRMATION_ROLE_REQUIRED
CONFIRMATION_STALE
IDEMPOTENCY_KEY_REUSED
STREAM_REVISION_CONFLICT
EVENT_STORE_UNAVAILABLE
OBJECT_STORE_UNAVAILABLE
```

Recoverable technical failures do not automatically terminally fail the session.

## 4.9 Idempotency

Idempotency records are scoped by:

```text
tenant_id
actor_or_service_identity
command_type
aggregate_id where applicable
idempotency_key
request_payload_hash
```

The same key with the same request returns the original result and event IDs. The same key with a different payload returns `IDEMPOTENCY_KEY_REUSED`.

Human decisions are never automatically retried after a stream-revision conflict.

## 4.10 Restart recovery

After restart, P.C.A.I. rehydrates every non-terminal session and evaluates:

- latest durable state;
- active capture request and expiry;
- accepted evidence integrity;
- interrupted processing run;
- current decision and confirmation validity;
- configuration, calibration or model changes during interruption.

Recovery rules:

| Last durable condition | Recovery behaviour |
|---|---|
| Active unexpired capture request | Resume waiting for capture. |
| Expired capture request | Return to `READY` and emit expiry event. |
| Accepted valid frame set | Resume or schedule processing. |
| Interrupted processing run | Mark the run interrupted and create a new run if policy permits. |
| Current machine proposal | Preserve it and await human action. |
| Human decision durable, completion absent | Revalidate evidence and allow idempotent completion. |
| Required evidence missing or corrupt | Move to `REVIEW_REQUIRED` or `FAILED` according to recoverability. |

No recovery path repeats a human confirmation.

# 5. Decision and evidence architecture

## 5.1 Separation of records

P.C.A.I. uses distinct immutable records for machine proposals, human decisions, evidence bundles, verification results and policy results.

This separation prevents the common failure where a model output, policy decision and human confirmation are collapsed into one mutable row.

## 5.2 MachineDecision

A machine decision is the system's structured proposal for a particular processing run.

```text
machine_decision_id
session_id
processing_run_id
evidence_bundle_id
count_outcome
identity_outcome
inspection_outcome
verification_result_id
policy_result_id
created_at
provenance
status
```

Status values:

```text
CURRENT
SUPERSEDED
REJECTED_BY_HUMAN
ACCEPTED_BY_HUMAN
```

A machine decision is never edited.

## 5.3 HumanDecision

A human decision records the authorised operational judgement.

```text
human_decision_id
session_id
machine_decision_id
evidence_bundle_id
actor_id
actor_role
decision_action
count_outcome
identity_outcome
reason_codes
safe_note
display_acknowledgement
created_at
```

Decision actions:

```text
ACCEPT_MACHINE_PROPOSAL
CORRECT_COUNT
CORRECT_IDENTITY
CORRECT_COUNT_AND_IDENTITY
MANUAL_RESOLUTION
REJECT_AND_RECAPTURE
CANCEL_WORKFLOW
```

The human decision never removes or rewrites the machine decision.

## 5.4 Count outcome

Machine count outcome:

```json
{
  "status": "VERIFIED | REVIEW_REQUIRED | NOT_EVALUATED",
  "candidate_count": 90,
  "method_results": [
    {
      "method": "instance_segmentation",
      "count": 90,
      "evidence_ref": "..."
    },
    {
      "method": "classical_crosscheck",
      "count": 90,
      "evidence_ref": "..."
    }
  ],
  "contradictions": [],
  "limitations": []
}
```

Human count outcome:

```json
{
  "confirmed_count": 90,
  "source": "MACHINE_ACCEPTED | HUMAN_CORRECTED | MANUAL_COUNT",
  "reason_codes": []
}
```

## 5.5 Identity outcome

Identity is not represented as one medicine ID plus one confidence value.

```json
{
  "status": "CONSISTENT_WITH_EXPECTED | CANDIDATE_ONLY | UNKNOWN | CONTRADICTED | NOT_EVALUATED",
  "expected_profile_id": "...",
  "expected_profile_version": 7,
  "ranked_hypotheses": [
    {
      "profile_id": "...",
      "supporting_evidence_refs": ["..."],
      "contradicting_evidence_refs": [],
      "uncertainty": {
        "score_type": "validated_identity_score_v1",
        "value": 0.93
      }
    },
    {
      "hypothesis": "UNKNOWN",
      "supporting_evidence_refs": []
    }
  ],
  "missing_evidence": ["reverse_side_not_observed"]
}
```

Human identity outcomes:

```text
EXPECTED_IDENTITY_CONFIRMED
IDENTITY_CORRECTED
IDENTITY_UNRESOLVED
COUNT_ONLY_WORKFLOW
```

## 5.6 EvidenceBundle

An evidence bundle is immutable. A newer bundle supersedes an older one rather than modifying it.

Required fields:

```text
bundle_id
session_id
processing_run_id
observation_refs
fact_refs
count_evidence
identity_evidence
inspection_evidence
supporting_evidence
contradicting_evidence
missing_evidence
source_independence
operating_envelope_version
model_versions
profile_versions
calibration_version
configuration_version
policy_version
integrity_hash
created_at
```

## 5.7 Evidence source independence

Every evidence item identifies its source family:

```text
SEGMENTATION_MODEL
CLASSICAL_VISION
OCR_MODEL
VISUAL_EMBEDDING
CALIBRATED_MEASUREMENT
EXPECTED_CONTEXT
HUMAN_OBSERVATION
DETERMINISTIC_POLICY
```

Two agents using the same underlying model output are correlated evidence, not independent votes.

```json
{
  "evidence_ref": "...",
  "source_family": "SEGMENTATION_MODEL",
  "provider_id": "count-seg-1.2.0",
  "input_refs": ["frame-1"],
  "correlation_group": "segmentation-frame-1-run-4"
}
```

## 5.8 VerificationResult

```json
{
  "verification_result_id": "...",
  "evidence_bundle_id": "...",
  "count_result": "PASS | REVIEW | FAIL | NOT_EVALUATED",
  "identity_result": "PASS | REVIEW | FAIL | NOT_EVALUATED",
  "inspection_result": "PASS | REVIEW | FAIL | NOT_EVALUATED",
  "hard_contradictions": [],
  "soft_contradictions": [],
  "missing_requirements": [],
  "required_next_actions": [],
  "verification_contract_version": "verification-v1"
}
```

Verification evaluates evidence sufficiency and contradiction. It does not determine user permission or final authority.

## 5.9 PolicyResult

```json
{
  "policy_result_id": "...",
  "policy_version": "policy-v1",
  "outcome": "ALLOW_PROPOSAL | REQUIRE_HUMAN_REVIEW | REQUIRE_RECAPTURE | BLOCK",
  "matched_rule_ids": [],
  "required_human_role": "PHARMACIST",
  "required_actions": [],
  "prohibited_actions": []
}
```

Deterministic policy considers verification, workflow type, user role, expected-context source, calibration, station health, operating envelope, model/profile approval and unresolved incidents.

## 5.10 Binding decision rule

A machine decision may become `VERIFIED` only when:

```text
required verification dimensions pass
AND policy outcome is ALLOW_PROPOSAL
AND referenced evidence and provenance are durable
AND the proposal refers to the current processing run
```

A human may resolve `REVIEW_REQUIRED` only when policy allows that resolution and the required role performs it.

A `BLOCK` result cannot be overridden through ordinary session confirmation.

## 5.11 Supersession

A new capture, changed context, changed target or new processing run may supersede active evidence and decisions.

Relevant events:

```text
evidence.bundle.superseded
decision.machine.superseded
decision.human_confirmation.invalidated
```

Historical records remain replayable.

# 6. Initial event set

```text
session.created
session.station.assigned
session.preparation.started
session.ready
session.capture.requested
session.capture.expired
observation.frame.captured
observation.quality.measured
observation.frame.accepted
observation.frame.rejected
session.recapture.requested
processing.run.started
processing.run.interrupted
processing.run.superseded
evidence.bundle.created
evidence.bundle.superseded
verification.started
verification.completed
verification.contradiction.detected
verification.additional_evidence.required
policy.evaluated
policy.review_required
policy.recapture_required
policy.blocked
decision.machine.proposed
decision.machine.superseded
decision.human.accepted
decision.human.corrected
decision.human.manually_resolved
decision.human.rejected
decision.human_confirmation.invalidated
session.completed
session.archived
session.cancelled
session.failed
session.abandoned
```

Event names may be refined before implementation, but semantic meaning must remain stable once events are persisted.

# 7. Code-quality standard

## 7.1 Naming

Names must express domain meaning.

Preferred:

```python
current_evidence_bundle_id
expected_medicine_profile_id
record_frame_quality_assessment
```

Avoid:

```python
data
result
handle
process
manager
utils
```

unless the name is genuinely precise in context.

## 7.2 Types

Use explicit value objects and enums at domain boundaries.

```python
from dataclasses import dataclass
from enum import StrEnum


class SessionState(StrEnum):
    CREATED = "CREATED"
    PREPARING = "PREPARING"
    READY = "READY"
    CAPTURING = "CAPTURING"
    PROCESSING = "PROCESSING"
    VERIFYING = "VERIFYING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    VERIFIED = "VERIFIED"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"


@dataclass(frozen=True, slots=True)
class PositiveCount:
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("count must be greater than zero")
```

## 7.3 Domain methods

Domain methods should be small, deterministic and descriptive.

```python
class CountingSession:
    def request_capture(self, command: RequestCapture) -> tuple[DomainEvent, ...]:
        self._require_state(SessionState.READY)
        self._require_station_assigned()
        self._require_capture_prerequisites(command)

        return (
            CaptureRequested.from_command(
                session_id=self.session_id,
                station_id=self.station_id,
                command=command,
            ),
        )
```

Do not place database, network, object-storage or model calls inside aggregate methods.

## 7.4 Error design

Errors use stable codes and safe messages.

```python
class DomainRuleViolation(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message


def require_state(actual: SessionState, expected: SessionState) -> None:
    if actual is not expected:
        raise DomainRuleViolation(
            code="SESSION_INVALID_TRANSITION",
            message=f"Expected session state {expected}; received {actual}.",
        )
```

Stack traces and sensitive diagnostics belong in restricted logs, not API responses.

## 7.5 Tests as executable documentation

Tests should explain business rules.

```python
def test_session_cannot_complete_without_human_confirmation() -> None:
    session = session_in_state(SessionState.VERIFIED)

    with pytest.raises(DomainRuleViolation) as error:
        session.complete(CompleteSession(idempotency_key="complete-1"))

    assert error.value.code == "SESSION_INVALID_TRANSITION"
```

Every production defect must produce a regression test.

# 8. Next engineering work

The next contract to define is the event-store implementation:

- stream and event schemas;
- append transaction;
- optimistic concurrency;
- idempotency records;
- outbox semantics;
- projection checkpoints;
- event-version evolution;
- integrity hashing;
- test fixtures and failure recovery.

After that, the first code should implement the pure `CountingSession` domain package and its tests before FastAPI or PostgreSQL adapters are introduced.
