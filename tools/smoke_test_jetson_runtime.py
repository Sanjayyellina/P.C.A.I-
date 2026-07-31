from __future__ import annotations

import argparse
import importlib
import platform
import sys
from dataclasses import dataclass

from pcai.tracking.contracts import CountPublicationDecision, TrackObservation
from pcai.tracking.object_tracker import ObjectTrackerConfig, TemporalObjectTracker
from pcai.tracking.stable_counter import StableCounter, StableCounterConfig
from pcai.tracking.temporal_tracker import TemporalSceneTracker, TemporalStabilityConfig


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def check_import(module_name: str) -> CheckResult:
    try:
        module = importlib.import_module(module_name)
    except Exception as error:
        return CheckResult(module_name, False, f"{type(error).__name__}: {error}")
    return CheckResult(
        module_name,
        True,
        str(getattr(module, "__version__", "version unavailable")),
    )


def run_tracking_smoke_test() -> CheckResult:
    tracker = TemporalObjectTracker(
        ObjectTrackerConfig(
            confirmation_hits=2,
            maximum_missed_frames=2,
            count_history_size=6,
        )
    )
    temporal = TemporalSceneTracker(
        TemporalStabilityConfig(
            window_size=5,
            minimum_ready_frames=3,
            maximum_count_range=0,
            maximum_mean_track_motion_px=2.0,
            maximum_confidence_range=0.05,
            minimum_mean_confidence=0.80,
            require_all_tracks_confirmed=True,
        )
    )
    stable = StableCounter(
        StableCounterConfig(
            minimum_publish_frames=2,
            minimum_scene_confidence=0.80,
            clear_after_unstable_frames=4,
        )
    )

    final_result = None
    for frame_sequence in range(1, 8):
        observations = (
            TrackObservation(
                frame_sequence=frame_sequence,
                fused_candidate_id=0,
                centroid_xy=(100.0, 100.0),
                bounding_box_xyxy=(80.0, 80.0, 120.0, 120.0),
                estimated_count=1,
                confidence=0.95,
            ),
            TrackObservation(
                frame_sequence=frame_sequence,
                fused_candidate_id=1,
                centroid_xy=(200.0, 100.0),
                bounding_box_xyxy=(180.0, 80.0, 220.0, 120.0),
                estimated_count=1,
                confidence=0.94,
            ),
        )
        tracking_result = tracker.update(frame_sequence, observations)
        temporal_result = temporal.update(tracking_result)
        final_result = stable.update(temporal_result)

    if final_result is None:
        return CheckResult("temporal-counting", False, "No result produced")
    if final_result.decision is not CountPublicationDecision.PUBLISH:
        return CheckResult(
            "temporal-counting",
            False,
            f"Expected PUBLISH, received {final_result.decision.value}",
        )
    if final_result.stable_count != 2:
        return CheckResult(
            "temporal-counting",
            False,
            f"Expected stable_count=2, received {final_result.stable_count}",
        )

    return CheckResult(
        "temporal-counting",
        True,
        f"published count={final_result.stable_count}, confidence={final_result.confidence:.3f}",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate core P.C.A.I. runtime imports and temporal counting logic."
    )
    parser.add_argument(
        "--strict-optional",
        action="store_true",
        help="Fail when optional AI/runtime packages are unavailable.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    print("P.C.A.I. Jetson Runtime Smoke Test")
    print("=" * 38)
    print(f"Python:   {sys.version.split()[0]}")
    print(f"Platform: {platform.platform()}")
    print(f"Machine:  {platform.machine()}")
    print()

    required_modules = ("numpy", "cv2", "pcai")
    optional_modules = ("ultralytics", "torch")
    results: list[CheckResult] = []

    for module_name in required_modules:
        results.append(check_import(module_name))

    for module_name in optional_modules:
        result = check_import(module_name)
        if not result.passed and not args.strict_optional:
            result = CheckResult(
                result.name,
                True,
                f"optional package unavailable ({result.detail})",
            )
        results.append(result)

    results.append(run_tracking_smoke_test())

    print("Checks")
    print("------")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")

    failures = tuple(result for result in results if not result.passed)
    print()
    if failures:
        print(f"RESULT: FAILED ({len(failures)} check(s))")
        return 1

    print("RESULT: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
