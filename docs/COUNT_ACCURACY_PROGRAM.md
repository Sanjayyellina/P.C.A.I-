# Count Accuracy Programme

## Scope

This programme concerns physical-instance counting only.  Tablet identity,
imprint reading, medication documents, and drug classification are explicitly
out of scope until this counting baseline is validated.

The safety objective is not a universal claim of 100% accuracy.  It is:

> Publish an exact count only for a validated, supported tray scene; otherwise
> return `REVIEW_REQUIRED` with evidence.

## Source baseline and current evidence

The canonical implementation baseline is
`implementation/counting-cells-v0.1`.  The current Jetson live trial is a
separate experimental script and must not be treated as the production
pipeline.  It uses a fixed frame-margin crop and automatic bright/dark
polarity choice; the first two live tests show that this is inadequate.

| Test | Known count | Final raw | Final stable | Result |
|---|---:|---:|---:|---|
| LIVE-BASELINE-001 | 10 | 11 | 10 | Boundary false positive; not a clean pass |
| LIVE-BASELINE-002 | 5 | 0 | 0 | Complete miss caused by wrong foreground polarity |
| LIVE-ANALYSIS-003 | 5 | 5 | n/a | Diagnostic confirmation only; manually derived tray crop |

## Implementation order

1. Define a fixed/calibrated tray region and reject frames without it.
2. Rectify the tray into canonical coordinates and apply its mask before any
   segmentation.
3. Segment candidates only inside that tray region; record mask and overlay.
4. Classify each region as single, touching, partial, foreign, or unknown.
5. Publish a count only if all acceptance conditions are met; otherwise
   require review.
6. Add temporal stability only as confirmation, never as a way to conceal a
   bad per-frame detection.

## Evaluation rules

Every physical arrangement is one independent scene.  Repeated video frames
from the same arrangement measure stability but do not increase accuracy
evidence.  Ground truth is recorded before processing and is never made
available to the algorithm.

Each test record must include:

- test, dataset, and session identifiers;
- camera, resolution, frame rate, tray, lighting, and calibration identifiers;
- known physical count and scene class;
- code revision, configuration revision, and command;
- raw per-frame counts, published count, stability, and processing speed;
- image, mask, and annotated-overlay artifact locations or hashes; and
- a reviewer decision: `PASS`, `REVIEW_REQUIRED`, or `FAIL`.

## Initial test matrix

Run distinct arrangements for each group before tuning against held-out scenes.

| Scenario | Counts | Purpose |
|---|---|---|
| Empty tray | 0 | Detect false positives |
| Clean separation | 1, 5, 10, 13 | Basic exact counting |
| Near tray edge | 5, 10 | Enforce tray boundary behavior |
| Touching pairs/clusters | 3, 5, 10 | Require review or validated splitting |
| Glare, shadow, blur | 5, 10 | Verify quality gate/refusal behavior |
| Foreign objects | 0, 5 | Prevent confident wrong counts |

No configuration may be declared accurate from a scene used to tune it.  The
final report must separately state per-frame accuracy, published-count
accuracy, review rate, and every false verified count.
