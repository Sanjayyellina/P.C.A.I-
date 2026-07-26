---
title: "P.C.A.I. Visual Atlas"
subtitle: "Intent, Cell Activation Graphs, Synapses, Blackboard and Pill-Counting Cognition"
version: "0.3"
status: "Active visual engineering baseline"
date: "2026-07-26"
supersedes: "PCAI_VISUAL_ATLAS.md v0.2 for new visual work; v0.2 remains preserved"
---

# P.C.A.I. Visual Atlas v0.3

## Version note

This file continues from `PCAI_VISUAL_ATLAS.md` v0.2. The previous file is preserved as a historical baseline. All new major visual architecture work continues here.

The central refinement introduced in this version is **Intent-driven Cell activation**. P.C.A.I. is not a fixed pipeline and not a single engine. It is a cognitive platform composed of bounded Cells connected through typed Synapses, coordinated through explicit Intent, and sharing session-scoped working knowledge through the Blackboard.

Pill counting remains the first product capability and first end-to-end implementation target.

# 1. Cognitive system overview

```mermaid
flowchart LR
    Reality[Physical reality]
    Intent[Explicit intent]
    Planner[C-000 Planner Cell]
    Graph[Activation graph]
    Cells[Specialised Cells]
    Synapses[Typed Synapses]
    Blackboard[(Session Blackboard)]
    Evidence[Evidence]
    Verification[Verification]
    Policy[Policy]
    Human[Authorised human]
    History[Immutable history]

    Reality --> Cells
    Intent --> Planner --> Graph --> Cells
    Cells --> Synapses --> Blackboard
    Blackboard --> Evidence --> Verification --> Policy --> Human --> History
```

# 2. Intent model

An Intent defines the bounded outcome the system is trying to achieve. It must be explicit, typed, versioned and linked to a session.

```mermaid
classDiagram
    class Intent {
      +IntentId intent_id
      +IntentType intent_type
      +IntentVersion version
      +SessionId session_id
      +ActorId requested_by
      +Constraint[] constraints
      +RequiredOutcome required_outcome
      +Timestamp created_at
      +Timestamp expires_at
    }

    class RequiredOutcome {
      +OutcomeType type
      +EvidenceRequirement[] evidence_requirements
      +PolicyRequirement[] policy_requirements
      +HumanRole final_authority
    }

    Intent --> RequiredOutcome
```

Initial intent types:

```text
COUNT_PILLS
VERIFY_EXPECTED_MEDICINE
IDENTIFY_MEDICINE_CANDIDATES
INSPECT_TRAY
EXPLAIN_SESSION
REPLAY_SESSION
ASSESS_SYSTEM_HEALTH
```

Only `COUNT_PILLS` is required for the first working product milestone.

# 3. C-000 Planner Cell

## 3.1 Mission

Translate an approved Intent into a bounded activation graph of Cells and Synapses.

The Planner Cell is an orchestrator, not an authority. It may select the required execution graph, but it may not count pills, change policy, skip verification, fabricate evidence or advance the session directly.

## 3.2 Authority boundary

```mermaid
flowchart TD
    Intent[Approved Intent]
    Planner[C-000 Planner Cell]
    Graph[Activation Graph]
    Runtime[C-019 Runtime Cell]

    Intent --> Planner --> Graph --> Runtime

    Planner -. prohibited .-> Count[Count pills]
    Planner -. prohibited .-> Verify[Approve verification]
    Planner -. prohibited .-> Policy[Override policy]
    Planner -. prohibited .-> Session[Mutate session state]
    Planner -. prohibited .-> Evidence[Create evidence without Cells]
```

## 3.3 Planner output

```mermaid
classDiagram
    class ActivationGraph {
      +GraphId graph_id
      +IntentId intent_id
      +GraphVersion version
      +CellNode[] cells
      +SynapseEdge[] synapses
      +StopCondition[] stop_conditions
      +ResourceBudget resource_budget
      +FailurePolicy failure_policy
    }

    class CellNode {
      +CellId cell_id
      +CellContractVersion contract_version
      +ExecutionMode execution_mode
      +Dependency[] dependencies
    }

    class SynapseEdge {
      +SynapseId synapse_id
      +CellId producer
      +CellId consumer
      +SchemaVersion schema_version
    }

    ActivationGraph --> CellNode
    ActivationGraph --> SynapseEdge
```

# 4. Intent-to-activation examples

## 4.1 Count pills

```mermaid
flowchart TD
    Intent[COUNT_PILLS]
    Planner[C-000 Planner]
    Observation[C-001 Observation]
    Quality[C-002 Frame Quality]
    Geometry[C-003 Tray Geometry]
    Candidates[C-004 Candidate Observation]
    Classical[C-005 Classical Counting]
    Segmentation[C-006 Segmentation Counting]
    Separation[C-007 Touching-Pill Separation]
    Reconcile[C-008 Count Reconciliation]
    Inspection[C-018 Inspection]
    Evidence[C-009 Evidence]
    Verify[C-010 Verification]
    Policy[C-011 Policy]
    Session[C-012 Session]
    Human[Authorised Human]

    Intent --> Planner
    Planner --> Observation --> Quality --> Geometry --> Candidates
    Candidates --> Classical
    Candidates --> Segmentation
    Segmentation --> Separation
    Classical --> Reconcile
    Segmentation --> Reconcile
    Separation --> Reconcile
    Candidates --> Inspection
    Reconcile --> Evidence
    Inspection --> Evidence
    Evidence --> Verify --> Policy --> Session --> Human
```

## 4.2 Explain session

```mermaid
flowchart TD
    Intent[EXPLAIN_SESSION]
    Planner[C-000 Planner]
    Replay[C-014 Replay]
    Knowledge[C-013 Knowledge]
    Evidence[C-009 Evidence]
    Runtime[C-019 Runtime]
    Human[User]

    Intent --> Planner
    Planner --> Replay
    Planner --> Knowledge
    Replay --> Evidence
    Knowledge --> Runtime
    Evidence --> Runtime
    Runtime --> Human
```

# 5. Dynamic activation graph

The Planner selects Cells according to Intent and current evidence. It does not activate every Cell unnecessarily.

```mermaid
flowchart LR
    Intent[Intent]
    Planner[C-000 Planner]
    Mandatory[Mandatory Cells]
    Conditional[Conditional Cells]
    Deferred[Deferred Cells]

    Intent --> Planner
    Planner --> Mandatory
    Planner --> Conditional
    Planner --> Deferred

    Mandatory --> C001[C-001 Observation]
    Mandatory --> C002[C-002 Quality]
    Mandatory --> C003[C-003 Geometry]
    Mandatory --> C004[C-004 Candidates]
    Mandatory --> C005[C-005 Classical Count]
    Mandatory --> C006[C-006 Segmentation Count]
    Mandatory --> C008[C-008 Reconciliation]
    Mandatory --> C009[C-009 Evidence]
    Mandatory --> C010[C-010 Verification]
    Mandatory --> C011[C-011 Policy]

    Conditional --> C007[C-007 Separation]
    Conditional --> C018[C-018 Inspection]
    Conditional --> C016[C-016 OCR]

    Deferred --> C017[C-017 Medicine]
    Deferred --> C013[C-013 Knowledge]
```

# 6. Cell-Synapse-Blackboard relationship

```mermaid
flowchart TB
    Intent[Intent]
    Planner[C-000 Planner]
    Graph[Activation Graph]
    Runtime[C-019 Runtime]

    CellA[Cell A]
    CellB[Cell B]
    CellC[Cell C]

    Synapse1[Typed Synapse]
    Synapse2[Typed Synapse]
    Blackboard[(Blackboard)]
    Events[(Event Store)]

    Intent --> Planner --> Graph --> Runtime
    Runtime --> CellA
    Runtime --> CellB
    Runtime --> CellC

    CellA --> Synapse1 --> Blackboard
    CellB --> Synapse2 --> Blackboard
    Blackboard --> CellC

    Blackboard -->|promoted facts and evidence only| Events
```

# 7. Blackboard knowledge classes

```mermaid
mindmap
  root((Blackboard Entries))
    Observation
      Frame references
      Capture metadata
      Calibration references
    Facts
      Quality measurements
      Geometry facts
      Candidate measurements
      Count observations
    Hypotheses
      Candidate counts
      Overlap hypotheses
      Unknown objects
    Contradictions
      Count disagreement
      Geometry mismatch
      Unsupported objects
    Requests
      Additional frame
      Recapture
      Separation analysis
      Human review
    Decisions
      Verification result
      Policy result
      Machine proposal
```

# 8. Pill-counting knowledge graph

```mermaid
flowchart LR
    Frame[FrameObservation]
    Quality[QualityFacts]
    Geometry[TrayGeometryFacts]
    CandidateSet[CandidateSet]
    Classical[ClassicalCountObservation]
    Segment[SegmentationCountObservation]
    Separation[SeparationObservation]
    Inspection[InspectionObservation]
    Reconciled[ReconciledCountFacts]
    Bundle[CountEvidenceBundle]
    Verification[VerificationResult]
    Policy[PolicyResult]
    Machine[MachineDecision]
    Human[HumanDecision]

    Frame --> Quality
    Frame --> Geometry
    Geometry --> CandidateSet
    CandidateSet --> Classical
    CandidateSet --> Segment
    Segment --> Separation
    CandidateSet --> Inspection
    Classical --> Reconciled
    Segment --> Reconciled
    Separation --> Reconciled
    Inspection --> Bundle
    Reconciled --> Bundle
    Quality --> Bundle
    Geometry --> Bundle
    Bundle --> Verification --> Policy --> Machine --> Human
```

# 9. C-003 Tray Geometry Cell

## 9.1 Mission

Convert a quality-approved frame into a calibrated tray-space representation.

C-003 establishes where valid pill observations may exist and how pixels map to physical measurement. It does not classify or count pills.

## 9.2 Inputs and outputs

```mermaid
flowchart LR
    Frame[FrameObservation]
    Calibration[Calibration version]
    Fiducials[Fiducial observations]
    Config[Tray configuration]

    Geometry[C-003 Tray Geometry Cell]

    Mask[Tray mask]
    Homography[Homography]
    Scale[Pixel-to-mm mapping]
    Residual[Geometry residual]
    Status[Geometry status]

    Frame --> Geometry
    Calibration --> Geometry
    Fiducials --> Geometry
    Config --> Geometry

    Geometry --> Mask
    Geometry --> Homography
    Geometry --> Scale
    Geometry --> Residual
    Geometry --> Status
```

## 9.3 Geometry flow

```mermaid
flowchart TD
    Frame[Quality-approved frame]
    Detect[Detect approved fiducials]
    Count{Required fiducials visible?}
    Reject[Require recapture or recalibration]
    Solve[Estimate homography]
    Residual{Residual within approved limit?}
    Mask[Build tray mask]
    Scale[Calculate pixel-to-mm transform]
    Output[Emit TrayGeometryFacts]

    Frame --> Detect --> Count
    Count -- No --> Reject
    Count -- Yes --> Solve --> Residual
    Residual -- No --> Reject
    Residual -- Yes --> Mask --> Scale --> Output
```

## 9.4 Output contract

```mermaid
classDiagram
    class TrayGeometryFacts {
      +GeometryFactsId geometry_facts_id
      +FrameId frame_id
      +CalibrationVersion calibration_version
      +ObjectRef tray_mask_ref
      +Matrix3x3 homography
      +Measurement pixel_scale_x
      +Measurement pixel_scale_y
      +float reprojection_error_px
      +GeometryStatus status
      +ReasonCode[] warnings
    }
```

## 9.5 Failure modes

```text
FIDUCIALS_MISSING
FIDUCIAL_PATTERN_MISMATCH
TRAY_PARTIALLY_OUTSIDE_FRAME
HOMOGRAPHY_UNSTABLE
REPROJECTION_ERROR_HIGH
CALIBRATION_VERSION_MISMATCH
PIXEL_SCALE_UNAVAILABLE
```

# 10. C-004 Candidate Observation Cell

## 10.1 Mission

Transform the calibrated tray region into a set of observed foreground candidates and measurable properties.

A candidate is not yet assumed to be one pill. It may be a tablet, capsule, merged group, fragment, foreign object, reflection, shadow or unknown region.

## 10.2 Candidate generation flow

```mermaid
flowchart TD
    Frame[Corrected tray frame]
    Mask[Tray mask]
    Normalise[Approved colour and illumination normalisation]
    Foreground[Generate foreground regions]
    Regions[Connected regions]
    Features[Extract geometric and visual facts]
    Graph[Build candidate neighbour graph]
    Classify[Assign observation status]
    Output[Emit CandidateSet]

    Frame --> Normalise
    Mask --> Normalise
    Normalise --> Foreground --> Regions --> Features --> Graph --> Classify --> Output
```

## 10.3 Candidate status model

```mermaid
stateDiagram-v2
    [*] --> OBSERVED
    OBSERVED --> SINGLE_CANDIDATE
    OBSERVED --> TOUCHING_REGION
    OBSERVED --> POSSIBLE_STACK
    OBSERVED --> FOREIGN_OBJECT
    OBSERVED --> PARTIAL_OBJECT
    OBSERVED --> ARTIFACT
    OBSERVED --> UNKNOWN
```

## 10.4 Candidate object

```mermaid
classDiagram
    class CandidateObservation {
      +CandidateId candidate_id
      +FrameId frame_id
      +ObjectRef mask_ref
      +BoundingBox bounding_box
      +Point centroid
      +Measurement area
      +Measurement perimeter
      +Measurement major_axis
      +Measurement minor_axis
      +float circularity
      +float solidity
      +float convexity
      +float edge_confidence
      +CandidateStatus status
      +ReasonCode[] warnings
    }

    class CandidateNeighbour {
      +CandidateId source
      +CandidateId target
      +Measurement centroid_distance
      +float boundary_contact_ratio
      +float overlap_risk
    }

    CandidateObservation "many" --> "many" CandidateNeighbour
```

## 10.5 Candidate decision tree

```mermaid
flowchart TD
    Region[Foreground region]
    Inside{Fully inside valid tray?}
    Partial[PARTIAL_OBJECT]
    Size{Within broad supported physical range?}
    Artifact[ARTIFACT or UNKNOWN]
    Shape{Single-object geometry plausible?}
    Single[SINGLE_CANDIDATE]
    Contact{Evidence of multiple touching objects?}
    Touching[TOUCHING_REGION]
    Stack{Possible stack or hidden object?}
    PossibleStack[POSSIBLE_STACK]
    Unknown[UNKNOWN]

    Region --> Inside
    Inside -- No --> Partial
    Inside -- Yes --> Size
    Size -- No --> Artifact
    Size -- Yes --> Shape
    Shape -- Yes --> Single
    Shape -- No --> Contact
    Contact -- Yes --> Touching
    Contact -- No --> Stack
    Stack -- Yes --> PossibleStack
    Stack -- No --> Unknown
```

# 11. Counting-first Cell set

```mermaid
flowchart LR
    C001[C-001 Observation]
    C002[C-002 Quality]
    C003[C-003 Geometry]
    C004[C-004 Candidates]
    C005[C-005 Classical Count]
    C006[C-006 Segmentation Count]
    C007[C-007 Separation]
    C008[C-008 Reconciliation]
    C018[C-018 Inspection]
    C009[C-009 Evidence]
    C010[C-010 Verification]
    C011[C-011 Policy]
    C012[C-012 Session]

    C001 --> C002 --> C003 --> C004
    C004 --> C005
    C004 --> C006
    C006 --> C007
    C005 --> C008
    C006 --> C008
    C007 --> C008
    C004 --> C018
    C008 --> C009
    C018 --> C009
    C009 --> C010 --> C011 --> C012
```

# 12. Cell activation lifecycle

```mermaid
stateDiagram-v2
    [*] --> DECLARED
    DECLARED --> WAITING_FOR_INPUTS
    WAITING_FOR_INPUTS --> READY
    READY --> RUNNING
    RUNNING --> COMPLETED
    RUNNING --> FAILED
    RUNNING --> CANCELLED
    COMPLETED --> PROMOTED
    COMPLETED --> SUPERSEDED
    FAILED --> RETRY_ALLOWED
    FAILED --> TERMINAL_FAILURE
    RETRY_ALLOWED --> READY
```

# 13. Synapse reliability flow

```mermaid
sequenceDiagram
    participant Producer as Producer Cell
    participant Gateway as Synapse Gateway
    participant Blackboard
    participant Consumer as Consumer Cell
    participant Events as Event Store

    Producer->>Gateway: Publish typed message
    Gateway->>Gateway: Validate schema and permissions
    Gateway->>Blackboard: Store session-scoped entry
    Blackboard-->>Consumer: Notify required input available
    Consumer->>Blackboard: Read referenced inputs
    Consumer->>Gateway: Publish result
    Gateway->>Blackboard: Store result

    alt Result promoted to durable evidence
        Gateway->>Events: Append promotion event and references
    else Temporary working state
        Blackboard->>Blackboard: Retain until superseded or expired
    end
```

# 14. Planner safety rules

```mermaid
flowchart TD
    Proposed[Planner proposes activation graph]
    Contracts{All Cells and Synapses approved?}
    Reject[Reject graph]
    Policy{Required policy and verification Cells present?}
    RejectUnsafe[Reject unsafe graph]
    Budget{Within resource budget?}
    Queue[Queue or degrade nonessential work]
    Activate[Runtime activates graph]

    Proposed --> Contracts
    Contracts -- No --> Reject
    Contracts -- Yes --> Policy
    Policy -- No --> RejectUnsafe
    Policy -- Yes --> Budget
    Budget -- No --> Queue --> Activate
    Budget -- Yes --> Activate
```

The Planner must never produce a graph that omits mandatory verification, policy or human-authority steps for the active workflow.

# 15. Versioning rule for visual files

- Minor wording, label, typo or small diagram corrections may update the current file in place.
- A major conceptual addition, new architecture layer, renamed primary abstraction or substantially revised system map creates a new versioned file.
- Previous major versions remain preserved.
- New files state which version they continue or supersede.
- Code and engineering changes must reference the current active Visual Atlas version.

# 16. Next version scope

The next major Visual Atlas version should add:

- C-005 Classical Counting Cell.
- C-006 Segmentation Counting Cell.
- C-007 Touching-Pill Separation Cell.
- C-008 Count Reconciliation Cell.
- Count disagreement localisation diagrams.
- Count evidence object lineage.
- Benchmark dataset and evaluation graphs.
- Event-store append/outbox sequence.
- PostgreSQL ER diagram.
