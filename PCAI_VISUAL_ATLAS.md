---
title: "P.C.A.I. Visual Atlas"
subtitle: "System Maps, Cell Architecture, State Machines, Sequence Diagrams and Pill-Counting Flows"
version: "0.2"
status: "Active visual engineering baseline"
date: "2026-07-26"
---

# P.C.A.I. Visual Atlas

## Purpose

This file is the visual companion to `PCAI_ARCHITECTURE_BIBLE.md` and `PCAI_ENGINEERING_MANUAL.md`.

It exists so that a new engineer can understand the system quickly before reading detailed contracts. Every diagram is expected to remain consistent with the engineering manual. When implementation changes, the corresponding diagram must be updated in the same pull request.

The diagrams in this file are editable Mermaid unless a raster image is preserved for historical or review purposes.

# 1. Document relationship map

```mermaid
flowchart LR
    Bible[Architecture Bible\nWhy and non-negotiable principles]
    Manual[Engineering Manual\nHow the system is implemented]
    Atlas[Visual Atlas\nHow the system is understood quickly]
    ADR[Architecture Decision Records\nWhy a material change was accepted]
    Code[Source Code and Tests\nExecutable truth]

    Bible --> Manual
    Bible --> Atlas
    Manual --> Atlas
    Manual --> Code
    ADR --> Bible
    ADR --> Manual
    ADR --> Atlas
    Code --> Manual
```

# 2. P.C.A.I. product priority map

Pill counting is the first product capability. Identification, agents, inventory and robotics build on top of a working count workflow.

```mermaid
flowchart TD
    P0[Controlled tray and optics]
    P1[Capture and frame quality]
    P2[Pill candidate observation]
    P3[Classical counting Cell]
    P4[Segmentation counting Cell]
    P5[Count reconciliation Cell]
    P6[Verification and policy Cells]
    P7[Human review and confirmation]
    P8[Event replay and evidence history]
    P9[Expected medicine verification]
    P10[OCR and visual fingerprints]
    P11[Broader multi-Cell intelligence]
    P12[Inventory and analytics]
    P13[Robotics with local safety]

    P0 --> P1 --> P2
    P2 --> P3
    P2 --> P4
    P3 --> P5
    P4 --> P5
    P5 --> P6 --> P7 --> P8
    P8 --> P9 --> P10 --> P11 --> P12 --> P13
```

# 3. P.C.A.I. Cell Society

P.C.A.I. is composed of specialised logical Cells. A Cell is defined by mission, authority, contracts, tools, evidence responsibilities and failure behaviour. A Cell does not necessarily mean a separate process, container or model.

```mermaid
flowchart TB
    Runtime[Runtime Cell\ncoordinates workflow]
    Session[Session Cell\nstate and allowed next action]
    Capture[Capture Cell\ntrusted station capture]
    Quality[Frame Quality Cell\nfocus exposure geometry]
    Classical[Classical Counting Cell\ncontours components watershed]
    Segmentation[Segmentation Counting Cell\ninstance masks]
    Inspection[Inspection Cell\nforeign objects mixed populations damage]
    OCR[OCR Cell\nimprint observations]
    Medicine[Medicine Cell\nranked identity hypotheses]
    Verification[Verification Cell\nchallenge and contradiction]
    Policy[Policy Cell\ndeterministic rules]
    Evidence[Evidence Cell\nimmutable evidence bundles]
    Knowledge[Knowledge Cell\napproved retrieval]
    Replay[Replay Cell\nhistorical reconstruction]
    Operations[Operations Cell\nhealth capacity and recovery]
    Human[Authorised Human\nfinal operational authority]

    Runtime --> Session
    Runtime --> Capture
    Runtime --> Quality
    Runtime --> Classical
    Runtime --> Segmentation
    Runtime --> Inspection
    Runtime --> OCR
    Runtime --> Medicine

    Capture --> Evidence
    Quality --> Evidence
    Classical --> Evidence
    Segmentation --> Evidence
    Inspection --> Evidence
    OCR --> Evidence
    Medicine --> Evidence

    Evidence --> Verification
    Knowledge --> Verification
    Verification --> Policy
    Policy --> Runtime
    Runtime --> Human
    Human --> Evidence
    Evidence --> Replay
    Operations --> Runtime
```

# 4. Pill-counting-first Cell architecture

```mermaid
flowchart LR
    Frame[Controlled frame]
    Quality[Frame Quality Cell]
    Tray[Tray Geometry Cell]
    Candidates[Pill Candidate Cell]
    Classical[Classical Counting Cell]
    Segmentation[Segmentation Counting Cell]
    Separation[Touching-Pill Separation Cell]
    Fusion[Count Reconciliation Cell]
    Inspection[Inspection Cell]
    Evidence[Count Evidence Cell]
    Verification[Verification Cell]
    Policy[Policy Cell]
    Human[Human confirmation]

    Frame --> Quality
    Quality -->|Pass| Tray
    Quality -->|Reject| Human
    Tray --> Candidates
    Candidates --> Classical
    Candidates --> Segmentation
    Classical --> Fusion
    Segmentation --> Fusion
    Segmentation --> Separation
    Separation --> Fusion
    Candidates --> Inspection
    Inspection --> Evidence
    Fusion --> Evidence
    Evidence --> Verification
    Verification --> Policy
    Policy -->|Verified proposal| Human
    Policy -->|Recapture or review| Human
```

# 5. First working product flow

```mermaid
flowchart TD
    Start([Start])
    Login[User logs in]
    Create[Create counting session]
    Prepare[Prepare station and tray]
    Capture[Capture tray frame]
    Quality{Frame quality passes?}
    Recapture[Show reason and request recapture]
    Observe[Generate pill candidates]
    Classical[Classical count]
    Segment[Segmentation count]
    Reconcile{Counts and evidence agree?}
    Review[Human review required]
    Propose[Propose verified count]
    Confirm[Human confirms or corrects]
    Complete[Complete session]
    Replay[Replay event and evidence timeline]

    Start --> Login --> Create --> Prepare --> Capture --> Quality
    Quality -- No --> Recapture --> Capture
    Quality -- Yes --> Observe
    Observe --> Classical
    Observe --> Segment
    Classical --> Reconcile
    Segment --> Reconcile
    Reconcile -- No --> Review --> Confirm
    Reconcile -- Yes --> Propose --> Confirm
    Confirm --> Complete --> Replay
```

# 6. CountingSession state machine

The following Mermaid diagram is the editable representation of the founder-provided state visual.

```mermaid
stateDiagram-v2
    [*] --> CREATED

    CREATED --> PREPARING
    CREATED --> CANCELLED

    PREPARING --> READY
    PREPARING --> REVIEW_REQUIRED
    PREPARING --> CANCELLED
    PREPARING --> FAILED

    READY --> CAPTURING
    READY --> CANCELLED
    READY --> FAILED

    CAPTURING --> PROCESSING
    CAPTURING --> READY
    CAPTURING --> REVIEW_REQUIRED
    CAPTURING --> CANCELLED
    CAPTURING --> FAILED

    PROCESSING --> VERIFYING
    PROCESSING --> REVIEW_REQUIRED
    PROCESSING --> FAILED

    VERIFYING --> VERIFIED
    VERIFYING --> REVIEW_REQUIRED
    VERIFYING --> FAILED

    REVIEW_REQUIRED --> PREPARING
    REVIEW_REQUIRED --> READY
    REVIEW_REQUIRED --> CAPTURING
    REVIEW_REQUIRED --> PROCESSING
    REVIEW_REQUIRED --> CONFIRMED
    REVIEW_REQUIRED --> CANCELLED
    REVIEW_REQUIRED --> FAILED

    VERIFIED --> CONFIRMED
    VERIFIED --> REVIEW_REQUIRED
    VERIFIED --> FAILED

    CONFIRMED --> COMPLETED
    CONFIRMED --> REVIEW_REQUIRED
    CONFIRMED --> FAILED

    COMPLETED --> ARCHIVED
```

## 6.1 State transition classes

```mermaid
flowchart LR
    Setup[Setup states\nCREATED PREPARING READY]
    Capture[Capture state\nCAPTURING]
    Intelligence[Intelligence states\nPROCESSING VERIFYING]
    Decision[Decision states\nREVIEW_REQUIRED VERIFIED CONFIRMED]
    Success[Successful terminal path\nCOMPLETED ARCHIVED]
    Other[Other terminal states\nCANCELLED FAILED ABANDONED]

    Setup --> Capture --> Intelligence --> Decision --> Success
    Setup --> Other
    Capture --> Other
    Intelligence --> Other
    Decision --> Other
    Decision --> Setup
    Decision --> Capture
    Decision --> Intelligence
```

# 7. Counting session sequence diagram

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant API
    participant Session as Session Cell
    participant EventStore
    participant SiteAgent
    participant Camera
    participant Quality as Frame Quality Cell
    participant Classical as Classical Counting Cell
    participant Segment as Segmentation Counting Cell
    participant Verify as Verification Cell
    participant Policy as Policy Cell

    User->>Browser: Start counting session
    Browser->>API: CreateSession
    API->>Session: Validate command
    Session-->>API: session.created
    API->>EventStore: Append event

    Browser->>API: RequestCapture
    API->>SiteAgent: Signed capture request
    SiteAgent->>Camera: Capture stable frame
    Camera-->>SiteAgent: Frame bytes and metadata
    SiteAgent->>API: Upload hashed frame
    API->>EventStore: Append observation.frame.captured

    API->>Quality: Assess frame
    Quality-->>API: Structured quality result

    alt Frame rejected
        API->>EventStore: Append observation.frame.rejected
        API-->>Browser: Explain and request recapture
    else Frame accepted
        API->>Classical: Estimate classical count
        API->>Segment: Estimate instance count
        Classical-->>API: Count evidence
        Segment-->>API: Masks and count evidence
        API->>Verify: Verify count evidence
        Verify->>Policy: Evaluate rules
        Policy-->>API: Verified proposal or review required
        API-->>Browser: Display count and evidence
        User->>Browser: Confirm or correct
        Browser->>API: RecordHumanDecision
        API->>EventStore: Append human decision and completion
    end
```

# 8. Counting Cell dependency tree

```mermaid
mindmap
  root((Counting Cells))
    Capture
      Camera identity
      Locked settings
      Frame hash
      Source sequence
    Quality
      Focus
      Exposure
      Glare
      Geometry
      Motion
      Contamination
    Candidate Observation
      Tray mask
      Foreground regions
      Shape facts
      Size facts
      Neighbour graph
    Classical Counting
      Thresholding
      Connected components
      Contours
      Watershed
    Segmentation Counting
      Instance masks
      Duplicate detection
      Merge detection
    Separation
      Distance transform
      Marker generation
      Watershed split
      Learned boundary evidence
    Reconciliation
      Agreement
      Contradiction
      Missing evidence
      Confidence calibration
    Verification
      Operating envelope
      Hard rules
      False-verified prevention
    Human Authority
      Review
      Correction
      Confirmation
```

# 9. Count evidence flow

```mermaid
flowchart LR
    Original[Original frame]
    Quality[Quality measurements]
    Tray[Tray mask and calibration]
    Classical[Classical observations]
    Segmentation[Segmentation observations]
    Inspection[Anomaly observations]
    Facts[Normalised facts]
    Bundle[Count evidence bundle]
    Verification[Verification result]
    Policy[Policy result]
    Machine[Machine decision]
    Human[Human decision]
    Event[Immutable events]

    Original --> Quality
    Original --> Tray
    Tray --> Classical
    Tray --> Segmentation
    Original --> Inspection
    Quality --> Facts
    Classical --> Facts
    Segmentation --> Facts
    Inspection --> Facts
    Facts --> Bundle --> Verification --> Policy --> Machine --> Human --> Event
```

# 10. Candidate observation model

```mermaid
classDiagram
    class FrameObservation {
      +FrameId frame_id
      +ObjectId original_object_id
      +CalibrationVersion calibration_version
      +CameraConfigurationHash camera_configuration_hash
    }

    class PillCandidate {
      +CandidateId candidate_id
      +BoundingBox bounding_box
      +MaskRef mask_ref
      +Point centroid
      +Measurement area
      +Measurement major_axis
      +Measurement minor_axis
      +float circularity
      +float solidity
      +CandidateStatus status
    }

    class NeighbourEdge {
      +CandidateId source
      +CandidateId target
      +float distance
      +float boundary_contact
    }

    class CountObservation {
      +CountMethod method
      +int candidate_count
      +EvidenceRef[] evidence_refs
      +WarningCode[] warnings
    }

    FrameObservation "1" --> "many" PillCandidate
    PillCandidate "many" --> "many" NeighbourEdge
    PillCandidate "many" --> "1" CountObservation
```

# 11. Candidate classification decision tree

```mermaid
flowchart TD
    Region[Observed foreground region]
    Valid{Inside tray and geometrically valid?}
    Artifact[Mark INVALID or ARTIFACT]
    PillLike{Pill-like shape, size and texture?}
    Foreign[Mark FOREIGN_OBJECT or UNKNOWN]
    Single{Single separable instance?}
    Candidate[Mark TABLET or CAPSULE candidate]
    Touching{Touching but separable?}
    Separate[Run separation Cell]
    Stack{Possible hidden or stacked pills?}
    Review[REVIEW_REQUIRED]

    Region --> Valid
    Valid -- No --> Artifact
    Valid -- Yes --> PillLike
    PillLike -- No --> Foreign
    PillLike -- Yes --> Single
    Single -- Yes --> Candidate
    Single -- No --> Touching
    Touching -- Yes --> Separate
    Touching -- No --> Stack
    Stack -- Yes --> Review
    Stack -- No --> Review
```

# 12. Count reconciliation decision tree

```mermaid
flowchart TD
    Inputs[Classical, segmentation and inspection evidence]
    Quality{Quality and calibration valid?}
    Recapture[Require recapture]
    Unsupported{Unsupported or hidden objects?}
    Review[Require human review]
    Agree{Independent count methods agree?}
    Contradiction[Locate differing candidates and contradiction]
    Resolvable{Contradiction safely resolvable?}
    Count[Create candidate count]
    Policy{Verification policy permits proposal?}
    Proposal[Create verified machine proposal]

    Inputs --> Quality
    Quality -- No --> Recapture
    Quality -- Yes --> Unsupported
    Unsupported -- Yes --> Review
    Unsupported -- No --> Agree
    Agree -- No --> Contradiction --> Resolvable
    Resolvable -- No --> Review
    Resolvable -- Yes --> Count
    Agree -- Yes --> Count
    Count --> Policy
    Policy -- No --> Review
    Policy -- Yes --> Proposal
```

# 13. Cell authority boundaries

```mermaid
flowchart LR
    ObservationCells[Observation Cells\nCapture Quality Classical Segmentation OCR]
    EvidenceCell[Evidence Cell]
    VerificationCell[Verification Cell]
    PolicyCell[Policy Cell]
    SessionCell[Session Cell]
    Human[Authorised Human]

    ObservationCells -->|may observe and measure| EvidenceCell
    EvidenceCell -->|may package support contradiction and missing evidence| VerificationCell
    VerificationCell -->|may pass review or fail evidence sufficiency| PolicyCell
    PolicyCell -->|may allow require review recapture or block| SessionCell
    SessionCell -->|may advance only through valid transitions| Human
    Human -->|final operational confirmation or correction| SessionCell
```

No Cell may independently authorise dispensing. No Cell may edit raw observations or prior events.

# 14. Deployment overview

```mermaid
flowchart LR
    Pharmacy[Pharmacy site]
    Browser[Secure browser]
    Camera[Controlled camera]
    SiteAgent[Site Agent]
    Network[mTLS or approved private connectivity]
    Proxy[Reverse proxy]
    API[P.C.A.I. API and Cells]
    Vision[Vision Cell runtime]
    Database[PostgreSQL event store and projections]
    Objects[OWC content-addressed evidence storage]
    LLM[Local language-model runtime]

    Pharmacy --> Browser
    Camera --> SiteAgent
    Browser --> Network
    SiteAgent --> Network
    Network --> Proxy --> API
    API --> Vision
    API --> Database
    API --> Objects
    API --> LLM
```

# 15. Permanent Cell catalogue

Cell IDs are stable vocabulary across architecture, engineering, code, logs, events, tests and support documentation. A Cell may evolve internally without changing its permanent ID.

| Cell ID | Name | Primary mission | Initial priority |
|---|---|---|---|
| `C-001` | Observation Cell | Register trustworthy physical observations. | NOW |
| `C-002` | Frame Quality Cell | Determine whether a frame is fit for counting. | NOW |
| `C-003` | Tray Geometry Cell | Establish the calibrated tray region and scale. | NOW |
| `C-004` | Candidate Observation Cell | Convert foreground regions into pill candidates and facts. | NOW |
| `C-005` | Classical Counting Cell | Produce an interpretable classical-vision count. | NOW |
| `C-006` | Segmentation Counting Cell | Produce instance masks and a learned count. | NOW |
| `C-007` | Touching-Pill Separation Cell | Resolve touching regions only inside validated limits. | NOW |
| `C-008` | Count Reconciliation Cell | Compare count methods and locate disagreement. | NOW |
| `C-009` | Evidence Cell | Build immutable evidence bundles. | NOW |
| `C-010` | Verification Cell | Challenge evidence and identify contradictions or gaps. | NOW |
| `C-011` | Policy Cell | Apply deterministic workflow and safety rules. | NOW |
| `C-012` | Session Cell | Govern workflow state and valid transitions. | NOW |
| `C-013` | Knowledge Cell | Retrieve approved medicine and operating knowledge. | NEXT |
| `C-014` | Replay Cell | Reconstruct historical events, evidence and decisions. | NOW |
| `C-015` | Operations Cell | Observe health, capacity, recovery and drift. | NOW |
| `C-016` | OCR Cell | Produce imprint observations and alternatives. | NEXT |
| `C-017` | Medicine Cell | Rank medicine hypotheses against approved profiles. | NEXT |
| `C-018` | Inspection Cell | Detect mixed populations, damage, debris and foreign objects. | NOW |
| `C-019` | Runtime Cell | Coordinate bounded Cell plans and resource admission. | NOW |

# 16. Synapses

A Synapse is a typed, versioned communication contract between Cells. Cells do not exchange unrestricted chat. A Synapse transports validated references, facts, evidence requests, capability results or workflow signals.

```mermaid
flowchart LR
    Observation[C-001 Observation]
    Quality[C-002 Frame Quality]
    Geometry[C-003 Tray Geometry]
    Candidates[C-004 Candidate Observation]
    Classical[C-005 Classical Counting]
    Segment[C-006 Segmentation Counting]
    Reconcile[C-008 Count Reconciliation]
    Evidence[C-009 Evidence]
    Verify[C-010 Verification]
    Policy[C-011 Policy]
    Session[C-012 Session]

    Observation -- S-001 FrameObservation --> Quality
    Observation -- S-002 FrameObservation --> Geometry
    Geometry -- S-003 TrayGeometryFacts --> Candidates
    Candidates -- S-004 CandidateSet --> Classical
    Candidates -- S-005 CandidateSet --> Segment
    Classical -- S-006 CountObservation --> Reconcile
    Segment -- S-007 CountObservation --> Reconcile
    Reconcile -- S-008 ReconciledCountFacts --> Evidence
    Evidence -- S-009 EvidenceBundle --> Verify
    Verify -- S-010 VerificationResult --> Policy
    Policy -- S-011 PolicyResult --> Session
```

## 16.1 Synapse envelope

```mermaid
classDiagram
    class SynapseMessage {
      +MessageId message_id
      +SynapseId synapse_id
      +CellId producer_cell_id
      +CellId consumer_cell_id
      +SessionId session_id
      +CorrelationId correlation_id
      +SchemaVersion schema_version
      +Reference[] input_refs
      +Reference[] output_refs
      +Uncertainty uncertainty
      +Timestamp created_at
      +Timestamp expires_at
    }
```

A Synapse must be schema validated, permission checked, tenant scoped, traceable to inputs and idempotent where retries are possible.

# 17. Blackboard

The Blackboard is session-scoped structured working memory. It is not the event store and not a free-form chat transcript.

```mermaid
flowchart TB
    Obs[C-001 Observation]
    Quality[C-002 Quality]
    Geometry[C-003 Geometry]
    Candidates[C-004 Candidates]
    Classical[C-005 Classical Count]
    Segment[C-006 Segmentation Count]
    Inspection[C-018 Inspection]

    Blackboard[(Session Blackboard)]

    Reconcile[C-008 Reconciliation]
    Evidence[C-009 Evidence]
    Verify[C-010 Verification]
    Runtime[C-019 Runtime]

    Obs --> Blackboard
    Quality --> Blackboard
    Geometry --> Blackboard
    Candidates --> Blackboard
    Classical --> Blackboard
    Segment --> Blackboard
    Inspection --> Blackboard

    Blackboard --> Reconcile
    Blackboard --> Evidence
    Blackboard --> Verify
    Blackboard --> Runtime
```

## 17.1 Blackboard lifecycle

```mermaid
stateDiagram-v2
    [*] --> ACTIVE
    ACTIVE --> SUPERSEDED
    ACTIVE --> REJECTED
    ACTIVE --> PROMOTED
    ACTIVE --> EXPIRED
    PROMOTED --> [*]
    SUPERSEDED --> [*]
    REJECTED --> [*]
    EXPIRED --> [*]
```

Only promoted entries become durable business evidence or events. Expired working state may be discarded after bounded retention.

# 18. Knowledge progression

```mermaid
flowchart LR
    Reality[Physical reality]
    Observation[Observation]
    Fact[Measured fact]
    Evidence[Evidence linked to hypothesis]
    Verification[Verification and contradiction]
    Policy[Policy outcome]
    Decision[Machine proposal]
    Human[Human confirmation or correction]
    History[Immutable history]
    Learning[Governed learning candidate]

    Reality --> Observation --> Fact --> Evidence --> Verification --> Policy --> Decision --> Human --> History
    History --> Learning
    Learning -. controlled validation and promotion .-> Evidence
```

# 19. C-001 Observation Cell

## 19.1 Mission

Register physical-world observations faithfully and immutably. C-001 does not count pills or interpret medicine identity.

## 19.2 Authority

```mermaid
flowchart LR
    Input[Trusted capture input]
    Cell[C-001 Observation Cell]
    Output[FrameObservation]

    Input --> Cell --> Output

    Cell -. prohibited .-> Count[Count pills]
    Cell -. prohibited .-> Identify[Identify medicine]
    Cell -. prohibited .-> Decide[Advance workflow]
    Cell -. prohibited .-> Rewrite[Modify prior observation]
```

## 19.3 Inputs and outputs

```mermaid
flowchart TD
    Request[Capture request]
    Device[Device and station identity]
    Bytes[Frame bytes]
    Metadata[Camera metadata]
    Time[Wall and monotonic time]
    Calibration[Calibration version]
    Configuration[Camera configuration hash]

    Observation[C-001 Observation Cell]

    Frame[FrameObservation]
    Hash[Content hash]
    Integrity[Integrity status]
    Object[Registered object reference]
    Event[Observation events]

    Request --> Observation
    Device --> Observation
    Bytes --> Observation
    Metadata --> Observation
    Time --> Observation
    Calibration --> Observation
    Configuration --> Observation

    Observation --> Frame
    Observation --> Hash
    Observation --> Integrity
    Observation --> Object
    Observation --> Event
```

## 19.4 Internal pipeline

```mermaid
flowchart TD
    Receive[Receive capture upload]
    Bind[Validate request session station and device binding]
    Sequence[Validate nonce source sequence and expiry]
    Hash[Compute and verify SHA-256]
    Metadata[Validate camera metadata and schema]
    Stage[Write object to staging]
    Verify[Verify stored bytes]
    Promote[Move into content-addressed storage]
    Register[Register immutable object metadata]
    Observe[Create FrameObservation]
    Event[Append observation.frame.captured]

    Receive --> Bind --> Sequence --> Hash --> Metadata --> Stage --> Verify --> Promote --> Register --> Observe --> Event
```

## 19.5 Failure routing

```mermaid
flowchart TD
    Failure[Observation input failure]
    Binding{Binding valid?}
    Deny[Reject and emit security or mismatch event]
    Integrity{Hash and bytes valid?}
    Quarantine[Quarantine object and open integrity incident]
    Metadata{Metadata valid?}
    Reject[Reject observation with stable reason]
    Storage{Durable storage available?}
    Retry[Return retryable storage failure]
    Success[Register observation]

    Failure --> Binding
    Binding -- No --> Deny
    Binding -- Yes --> Integrity
    Integrity -- No --> Quarantine
    Integrity -- Yes --> Metadata
    Metadata -- No --> Reject
    Metadata -- Yes --> Storage
    Storage -- No --> Retry
    Storage -- Yes --> Success
```

## 19.6 Primary events

```text
observation.frame.received
observation.integrity.verified
observation.integrity.failed
observation.frame.captured
observation.registration.failed
```

# 20. C-002 Frame Quality Cell

## 20.1 Mission

Determine whether a registered frame is fit for pill counting inside the active operating envelope. C-002 measures quality; it does not count pills.

## 20.2 Measurement tree

```mermaid
mindmap
  root((Frame Quality))
    Focus
      Fiducial sharpness
      Edge response
      Lens contamination signal
    Exposure
      Dark clipping
      Bright clipping
      Histogram range
    Glare
      Saturated regions
      Specular area
      Candidate interference
    Geometry
      Fiducial visibility
      Homography residual
      Tray coverage
    Motion
      Burst displacement
      Blur estimate
      Stability window
    Colour
      White balance
      Reference patch drift
    Contamination
      Debris
      Stains
      Unexpected foreground
    Integrity
      Decode validity
      Resolution
      Pixel format
      Configuration match
```

## 20.3 Quality decision flow

```mermaid
flowchart TD
    Frame[FrameObservation]
    Decode{Image decodes and format is approved?}
    Geometry{Tray geometry and fiducials valid?}
    Focus{Focus passes?}
    Exposure{Exposure passes?}
    Glare{Glare within limit?}
    Motion{Frame stable?}
    Contamination{Tray clean enough?}
    Pass[Quality PASS]
    Recapture[REQUIRE_RECAPTURE]
    Review[REVIEW_REQUIRED]
    Block[BLOCK STATION OR CAPTURE]

    Frame --> Decode
    Decode -- No --> Block
    Decode -- Yes --> Geometry
    Geometry -- No --> Recapture
    Geometry -- Yes --> Focus
    Focus -- No --> Recapture
    Focus -- Yes --> Exposure
    Exposure -- No --> Recapture
    Exposure -- Yes --> Glare
    Glare -- No --> Recapture
    Glare -- Yes --> Motion
    Motion -- No --> Recapture
    Motion -- Yes --> Contamination
    Contamination -- Severe --> Review
    Contamination -- Acceptable --> Pass
```

## 20.4 Output contract

```mermaid
classDiagram
    class FrameQualityAssessment {
      +AssessmentId assessment_id
      +FrameId frame_id
      +QualityStatus status
      +QualityCheck[] checks
      +ReasonCode[] reason_codes
      +ActionCode required_action
      +OperatingEnvelopeVersion operating_envelope_version
      +ConfigurationVersion threshold_configuration
      +ProviderVersion provider_version
    }

    class QualityCheck {
      +CheckName name
      +CheckStatus status
      +float measured_value
      +float threshold
      +string unit
      +EvidenceRef evidence_ref
    }

    FrameQualityAssessment "1" --> "many" QualityCheck
```

## 20.5 Quality status semantics

| Status | Meaning | Workflow action |
|---|---|---|
| `PASS` | All mandatory quality checks satisfy the active envelope. | Continue to tray geometry and candidate observation. |
| `REQUIRE_RECAPTURE` | The observation can be repeated after a clear corrective action. | Show operator instruction and capture again. |
| `REVIEW_REQUIRED` | The condition is unusual or potentially unsafe and needs authorised review. | Preserve evidence and stop automatic counting. |
| `BLOCK` | Input integrity, station configuration or calibration is invalid. | Prevent counting until maintenance or configuration correction. |

## 20.6 Events

```text
observation.quality.assessment_started
observation.quality.measured
observation.frame.accepted
observation.frame.rejected
observation.quality.review_required
camera.quality_drift_detected
```

# 21. Counting-first execution map

The first product release must reach a real count before expanding identity features.

```mermaid
gantt
    title P.C.A.I. Counting-First Engineering Sequence
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d

    section Physical Baseline
    Confirm camera tray lighting assumptions     :a1, 2026-07-27, 5d
    Capture representative controlled frames     :a2, after a1, 4d

    section Trusted Observation
    Implement C-001 Observation Cell contracts   :b1, 2026-07-27, 6d
    Implement C-002 Frame Quality Cell baseline  :b2, after b1, 6d

    section Counting Cells
    Implement C-003 tray geometry                :c1, after b2, 5d
    Implement C-004 candidate observations       :c2, after c1, 5d
    Implement C-005 classical count baseline     :c3, after c2, 7d
    Implement C-006 segmentation baseline        :c4, after c2, 10d
    Implement C-007 touching separation          :c5, after c3, 8d
    Implement C-008 reconciliation               :c6, after c4, 5d

    section Trust and User Flow
    Implement C-009 evidence bundle              :d1, after c6, 4d
    Implement C-010 verification and C-011 policy:d2, after d1, 5d
    Implement review confirmation replay UI      :d3, after d2, 7d

    section First Working Count
    Controlled end-to-end count demonstration    :milestone, m1, after d3, 0d
```

Dates are planning placeholders and must not be treated as commitments until hardware availability and engineering capacity are confirmed.

# 22. Visual maintenance rules

- Every major state machine must have an editable Mermaid representation.
- Every asynchronous workflow must have a sequence diagram.
- Every Cell must have an authority-boundary diagram or table.
- Every Synapse must have a typed message contract.
- Every evidence-producing pipeline must show source, transformation and durable output.
- Every recoverable failure path must be visible in at least one diagram.
- Diagrams must not imply independence where Cells share the same model or source evidence.
- A diagram changed by code or contract changes must be updated in the same pull request.
- Diagrams explain architecture; they do not replace binding textual invariants and tests.

# 23. Next visual additions

- C-003 Tray Geometry Cell specification.
- C-004 Candidate Observation Cell specification.
- C-005 Classical Counting Cell internal algorithm flow.
- C-006 Segmentation Counting Cell training and inference flow.
- C-007 Touching-Pill Separation challenge matrix.
- C-008 Count Reconciliation contradiction localisation.
- Detailed event-store append and outbox sequence.
- PostgreSQL event and projection entity-relationship diagram.
- Object-storage registration and reconciliation flow.
- Count benchmark dataset lineage.
- Model promotion and rollback lifecycle.
- Site-agent pairing and certificate-rotation sequence.
- Boot, degradation and recovery state diagrams.
