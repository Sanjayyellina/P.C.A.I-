# LIVE-BASELINE-002

## Record

| Field | Value |
|---|---|
| Date | 2026-08-20 |
| Setup | Jetson Orin Nano with USB webcam; black rectangular tray |
| Frame mode | 1920 x 1080 at requested 30 FPS |
| Scene class | Five clearly separated white tablets on the tray |
| Ground truth | 5 white tablets |
| Trial | Existing unchanged `tools/run_classical_webcam_trial.py` |
| Trial length | 300 frames; stability window 30 |
| Final raw count | 0 |
| Final stable count | 0 |
| Final measured speed | Approximately 9.6 FPS |
| Artifacts | Jetson temporary path `/tmp/pcai-live-baseline-5`; final overlay retained locally during review |
| Decision | FAIL — complete miss in a visually clean scene |

## Observation

The final image visibly contains five white tablets.  The script selected
`dark-on-bright`, because its workspace was a broad fixed-margin crop that
included non-tray background.  It consequently treated the black tray as the
foreground region, rejected that oversized contour, and returned zero.

## Required follow-up

Detect or calibrate the tray before selecting segmentation polarity.  The
polarity decision and all segmentation must be calculated only within the tray
mask.  A clean five-tablet arrangement must become a held-out regression test.
