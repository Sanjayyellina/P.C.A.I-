# LIVE-ANALYSIS-003

## Record

| Field | Value |
|---|---|
| Date | 2026-08-20 |
| Input | Final annotated frame retained from `LIVE-BASELINE-002` |
| Ground truth | 5 white tablets |
| Analysis | Temporary tray-only crop, bright foreground threshold 200, 5 px elliptical opening |
| Accepted area bounds | 1,000–20,000 px² |
| Candidate areas | 4,415.0; 4,436.5; 4,492.0; 4,494.5; 4,729.5 px² |
| Resulting count | 5 |
| Decision | DIAGNOSTIC ONLY — confirms the failure mechanism; not an independent evaluation result |

## Observation

The same frame for which the existing broad-crop script published zero yields
five valid bright-on-dark candidate regions when analysis is limited to the
interior of the black tray.  This demonstrates that tablet identity data is
not needed to resolve the observed failure.

## Limitations

The tray crop was manually derived from this already-observed frame.  It must
not be tuned or presented as a validated production calibration.  The next
implementation step is a reproducible tray calibration/configuration followed
by evaluation on new, held-out physical arrangements.
