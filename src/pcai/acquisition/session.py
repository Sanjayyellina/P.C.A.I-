from __future__ import annotations

from dataclasses import dataclass

from .capture_worker import CaptureWorker, CaptureWorkerConfig
from .contracts import AcquisitionSnapshot, CameraConfig, CameraFrame
from .diagnostics import AcquisitionDiagnostics, DiagnosticsConfig, DiagnosticsReport
from .frame_queue import FrameQueue
from .opencv_camera import OpenCvCamera


@dataclass(frozen=True, slots=True)
class AcquisitionSessionConfig:
    camera: CameraConfig = CameraConfig()
    worker: CaptureWorkerConfig = CaptureWorkerConfig()
    diagnostics: DiagnosticsConfig = DiagnosticsConfig()
    queue_size: int = 2

    def __post_init__(self) -> None:
        if self.queue_size <= 0:
            raise ValueError("queue_size must be positive.")


class AcquisitionSession:
    """High-level API for one live camera acquisition session."""

    def __init__(self, config: AcquisitionSessionConfig | None = None) -> None:
        self._config = config or AcquisitionSessionConfig()
        self._queue = FrameQueue(max_size=self._config.queue_size)
        self._camera = OpenCvCamera(self._config.camera)
        self._worker = CaptureWorker(
            camera=self._camera,
            queue=self._queue,
            config=self._config.worker,
        )
        self._diagnostics = AcquisitionDiagnostics(self._config.diagnostics)

    @property
    def running(self) -> bool:
        return self._worker.running

    def start(self) -> None:
        self._worker.start()

    def read(self, timeout_s: float | None = 1.0) -> CameraFrame | None:
        return self._queue.get(timeout_s=timeout_s)

    def read_latest(self, timeout_s: float | None = 1.0) -> CameraFrame | None:
        return self._queue.get_latest(timeout_s=timeout_s)

    def snapshot(self) -> AcquisitionSnapshot:
        return self._worker.snapshot()

    def diagnostics(self) -> DiagnosticsReport:
        return self._diagnostics.evaluate(self.snapshot())

    def stop(self, timeout_s: float = 5.0) -> None:
        self._worker.stop(timeout_s=timeout_s)

    def __enter__(self) -> "AcquisitionSession":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.stop()
