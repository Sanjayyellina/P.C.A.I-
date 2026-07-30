from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic_ns

import numpy as np

from pcai.acquisition import (
    AcquisitionDiagnostics,
    AcquisitionHealth,
    AcquisitionSessionConfig,
    AcquisitionSnapshot,
    CameraConfig,
    CameraFrame,
    CameraState,
    DiagnosticsConfig,
    FrameMetadata,
)


def test_session_config_validates_queue_size() -> None:
    try:
        AcquisitionSessionConfig(queue_size=0)
    except ValueError as error:
        assert "queue_size" in str(error)
    else:
        raise AssertionError("Expected queue_size validation failure.")


def test_session_config_accepts_wireless_camera_source() -> None:
    config = AcquisitionSessionConfig(
        camera=CameraConfig(
            source="rtsp://camera.local/live",
            backend=None,
            camera_id="wireless-camera-1",
        )
    )

    assert config.camera.source == "rtsp://camera.local/live"
    assert config.camera.camera_id == "wireless-camera-1"


def test_diagnostics_accepts_running_session_snapshot() -> None:
    snapshot = AcquisitionSnapshot(
        state=CameraState.RUNNING,
        frames_captured=120,
        frames_dropped=2,
        measured_fps=29.8,
        queue_depth=1,
        last_frame_age_ms=14.0,
        last_error=None,
    )
    diagnostics = AcquisitionDiagnostics(
        DiagnosticsConfig(
            minimum_fps=20.0,
            maximum_frame_age_ms=200.0,
            maximum_drop_ratio=0.10,
        )
    )

    report = diagnostics.evaluate(snapshot)

    assert report.health is AcquisitionHealth.HEALTHY
    assert report.reason_codes == ()


def test_camera_frame_contract_preserves_live_metadata() -> None:
    image = np.zeros((16, 24, 3), dtype=np.uint8)
    metadata = FrameMetadata(
        sequence=7,
        captured_at_utc=datetime.now(timezone.utc),
        monotonic_ns=monotonic_ns(),
        camera_id="wireless-camera-1",
        width_px=24,
        height_px=16,
    )

    frame = CameraFrame(image_bgr=image, metadata=metadata)

    assert frame.metadata.sequence == 7
    assert frame.metadata.camera_id == "wireless-camera-1"
    assert frame.image_bgr.shape == (16, 24, 3)
