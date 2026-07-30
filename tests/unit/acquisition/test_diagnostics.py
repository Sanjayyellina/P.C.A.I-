from __future__ import annotations

from pcai.acquisition import (
    AcquisitionDiagnostics,
    AcquisitionHealth,
    AcquisitionSnapshot,
    CameraState,
    DiagnosticsConfig,
)


def make_snapshot(**overrides: object) -> AcquisitionSnapshot:
    values: dict[str, object] = {
        "state": CameraState.RUNNING,
        "frames_captured": 100,
        "frames_dropped": 0,
        "measured_fps": 30.0,
        "queue_depth": 1,
        "last_frame_age_ms": 20.0,
        "last_error": None,
    }
    values.update(overrides)
    return AcquisitionSnapshot(**values)  # type: ignore[arg-type]


def test_healthy_snapshot_is_reported_healthy() -> None:
    report = AcquisitionDiagnostics().evaluate(make_snapshot())

    assert report.health is AcquisitionHealth.HEALTHY
    assert report.reason_codes == ()


def test_closed_camera_is_reported_stopped() -> None:
    report = AcquisitionDiagnostics().evaluate(
        make_snapshot(state=CameraState.CLOSED)
    )

    assert report.health is AcquisitionHealth.STOPPED
    assert report.reason_codes == ("CAMERA_CLOSED",)


def test_stale_frame_is_reported_unhealthy() -> None:
    diagnostics = AcquisitionDiagnostics(
        DiagnosticsConfig(maximum_frame_age_ms=100.0)
    )

    report = diagnostics.evaluate(make_snapshot(last_frame_age_ms=250.0))

    assert report.health is AcquisitionHealth.UNHEALTHY
    assert "FRAME_STALE" in report.reason_codes


def test_low_fps_is_reported_degraded() -> None:
    diagnostics = AcquisitionDiagnostics(DiagnosticsConfig(minimum_fps=20.0))

    report = diagnostics.evaluate(make_snapshot(measured_fps=10.0))

    assert report.health is AcquisitionHealth.DEGRADED
    assert "FPS_LOW" in report.reason_codes


def test_high_drop_ratio_is_reported_degraded() -> None:
    diagnostics = AcquisitionDiagnostics(
        DiagnosticsConfig(maximum_drop_ratio=0.10)
    )

    report = diagnostics.evaluate(
        make_snapshot(frames_captured=80, frames_dropped=20)
    )

    assert report.health is AcquisitionHealth.DEGRADED
    assert "DROP_RATIO_HIGH" in report.reason_codes


def test_failed_camera_with_error_is_unhealthy() -> None:
    report = AcquisitionDiagnostics().evaluate(
        make_snapshot(
            state=CameraState.FAILED,
            last_error="CameraReadError: disconnected",
        )
    )

    assert report.health is AcquisitionHealth.UNHEALTHY
    assert "CAMERA_FAILED" in report.reason_codes
    assert "LAST_ERROR_PRESENT" in report.reason_codes
