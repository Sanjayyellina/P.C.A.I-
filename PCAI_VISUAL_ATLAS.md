---
title: "P.C.A.I. Visual Atlas"
subtitle: "System Maps, Cell Architecture, State Machines, Sequence Diagrams and Pill-Counting Flows"
version: "0.1"
status: "Active visual engineering baseline"
date: "2026-07-26"
---

# P.C.A.I. Visual Atlas

## Purpose

This file is the visual companion to `PCAI_ARCHITECTURE_BIBLE.md` and `PCAI_ENGINEERING_MANUAL.md`.

It exists so that a new engineer can understand the system quickly before reading detailed contracts. Every diagram is expected to remain consistent with the engineering manual. When the implementation changes, the corresponding diagram must be updated in the same pull request.

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
    P3[Classical counting cell]
    P4[Segmentation counting cell]
    P5[Count reconciliation cell]
    P6[Verification and policy cells]
    P7[Human review and confirmation]
    P8[Event replay and evidence history]
    P9[Expected medicine verification]
    P10[OCR and visual fingerprints]
    P11[Broader multi-cell intelligence]
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

The following Mermaid diagram is the editable representation of the state model shown in the founder-provided visual snapshot.

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

# 15. Visual maintenance rules

- Every major state machine must have an editable Mermaid representation.
- Every asynchronous workflow must have a sequence diagram.
- Every Cell must have an authority-boundary diagram or table.
- Every evidence-producing pipeline must show source, transformation and durable output.
- Every recoverable failure path must be visible in at least one diagram.
- Diagrams must not imply independence where Cells share the same model or source evidence.
- A diagram changed by code or contract changes must be updated in the same pull request.
- Diagrams explain architecture; they do not replace binding textual invariants and tests.

# 16. Next visual additions

The following diagrams will be added as engineering progresses:

- Detailed event-store append and outbox sequence.
- PostgreSQL event and projection entity-relationship diagram.
- Object-storage registration and reconciliation flow.
- Frame-quality measurement tree.
- Classical Counting Cell internal algorithm flow.
- Segmentation Counting Cell training and inference flow.
- Touching-pill separation challenge matrix.
- Count benchmark dataset lineage.
- Model promotion and rollback lifecycle.
- Site-agent pairing and certificate-rotation sequence.
- Boot, degradation and recovery state diagrams.
