from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from time import monotonic_ns, sleep

import numpy as np

from pcai.acquisition import (
    CameraFrame,
    CameraSource,
    CameraState,
    CaptureWorker,
    CaptureWorkerConfig,
    FrameMetadata,
    FrameQueue,
)


class FakeCamera(CameraSource):
    def __init__(self) -> None:
        self._state = CameraState.CLOSED
        self._sequence = 0
        self._lock = Lock()

    @property
    def state(self) -> CameraState:
        with self._lock:
            return self._state

    def open(self) -> None:
        with self._lock:
            self._state = CameraState.OPEN

    def read(self) -> CameraFrame:
        with self._lock:
            if self._state not in {CameraState.OPEN, CameraState.RUNNING}:
                raise RuntimeError("camera not open")
            sequence = self._sequence
            self._sequence += 1
            self._state = CameraState.RUNNING

        image = np.zeros((8, 12, 3), dtype=np.uint8)
        return CameraFrame(
            image_bgr=image,
            metadata=FrameMetadata(
                sequence=sequence,
                captured_at_utc=datetime.now(timezone.utc),
                monotonic_ns=monotonic_ns(),
                camera_id="fake-camera",
                width_px=12,
                height_px=8,
            ),
        )

    def close(self) -> None:
        with self._lock:
            self._state = CameraState.CLOSED


def test_worker_captures_frames_and_reports_snapshot() -> None:
    camera = FakeCamera()
    queue = FrameQueue(max_size=2)
    worker = CaptureWorker(
        camera=camera,
        queue=queue,
        config=CaptureWorkerConfig(fps_window_s=0.01),
    )

    worker.start()
    frame = queue.get(timeout_s=1.0)
    sleep(0.02)
    snapshot = worker.snapshot()
    worker.stop()

    assert frame is not None
    assert snapshot.frames_captured > 0
    assert snapshot.state in {CameraState.OPEN, CameraState.RUNNING}
    assert snapshot.last_frame_age_ms is not None


def test_start_is_idempotent() -> None:
    camera = FakeCamera()
    queue = FrameQueue(max_size=1)
    worker = CaptureWorker(camera=camera, queue=queue)

    worker.start()
    first_thread = worker._thread
    worker.start()
    second_thread = worker._thread
    worker.stop()

    assert first_thread is second_thread
