# LIVE-BASELINE-001

## Record

| Field | Value |
|---|---|
| Date | 2026-08-20 |
| Setup | Jetson Orin Nano with USB webcam; black rectangular tray |
| Frame mode | 1920 x 1080 at requested 30 FPS |
| Scene class | Clean separation, with an external bright object near the tray boundary |
| Ground truth | 10 white tablets |
| Trial | Existing unchanged `tools/run_classical_webcam_trial.py` |
| Trial length | 300 frames; stability window 30 |
| Final raw count | 11 |
| Final stable count | 10 |
| Final measured speed | Approximately 9.9 FPS |
| Artifacts | Jetson temporary path `/tmp/pcai-live-baseline-10` |
| Decision | FAIL — a raw false positive was present even though temporal voting published 10 |

## Observation

The final annotated frame showed ten physical tablets and an additional small
false candidate at the upper-right tray boundary.  Temporal voting matched the
ground truth but must not be accepted as evidence of an accurate detector.

## Required follow-up

Use a tray mask/canonical workspace before segmentation, and add an explicit
near-edge/foreign-object test to the held-out evaluation set.
