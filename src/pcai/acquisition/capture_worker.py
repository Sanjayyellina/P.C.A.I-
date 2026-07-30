from __future__ import annotations

from dataclasses import dataclass
from threading import Event, Lock, Thread
from time import monotonic, sleep

from .contracts import AcquisitionSnapshot, CameraSource, CameraState
from .exceptions import AcquisitionError, CaptureWorkerError
from .frame_queue import FrameQueue


@dataclass(frozen=True, slots=True)
class CaptureWorkerConfig:
    reconnect_attempts: int = 3
    reconnect_delay_s: float = 0.5
    fps_window_s: float = 2.0

    def __post_init__(self) -> None:
        if self.reconnect_attempts < 0:
            raise ValueError("reconnect_attempts cannot be negative.")
        if self.reconnect_delay_s < 0:
            raise ValueError("reconnect_delay_s cannot be negative.")
        if self.fps_window_s <= 0:
            raise ValueError("fps_window_s must be positive.")


class CaptureWorker:
    """Continuously reads frames from a camera on a background thread."""

    def __init__(
        self,
        camera: CameraSource,
        queue: FrameQueue,
        config: CaptureWorkerConfig | None = None,
    ) -> None:
        self._camera = camera
        self._queue = queue
        self._config = config or CaptureWorkerConfig()
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._lock = Lock()
        self._frames_captured = 0
        self._measured_fps = 0.0
        self._last_frame_monotonic_s: float | None = None
        self._last_error: str | None = None
        self._window_started_s = monotonic()
        self._window_frames = 0

    @property
    def running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def start(self) -> None:
        with self._lock:
            if self.running:
                return
            self._stop_event.clear()
            self._thread = Thread(
                target=self._run,
                name="pcai-capture-worker",
                daemon=True,
            )
            self._thread.start()

    def stop(self, timeout_s: float = 5.0) -> None:
        if timeout_s < 0:
            raise ValueError("timeout_s cannot be negative.")
        self._stop_event.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout_s)
            if thread.is_alive():
                raise CaptureWorkerError("Capture worker did not stop within timeout.")
        self._camera.close()
        self._queue.close()

    def snapshot(self) -> AcquisitionSnapshot:
        now = monotonic()
        with self._lock:
            age_ms = None
            if self._last_frame_monotonic_s is not None:
                age_ms = max(0.0, (now - self._last_frame_monotonic_s) * 1000.0)
            return AcquisitionSnapshot(
                state=self._camera.state,
                frames_captured=self._frames_captured,
                frames_dropped=self._queue.dropped_frames,
                measured_fps=self._measured_fps,
                queue_depth=self._queue.depth,
                last_frame_age_ms=age_ms,
                last_error=self._last_error,
            )

    def _run(self) -> None:
        reconnects_remaining = self._config.reconnect_attempts

        while not self._stop_event.is_set():
            try:
                if self._camera.state not in {CameraState.OPEN, CameraState.RUNNING}:
                    self._camera.open()
                frame = self._camera.read()
                self._queue.put(frame)
                self._record_frame()
                reconnects_remaining = self._config.reconnect_attempts
            except AcquisitionError as error:
                with self._lock:
                    self._last_error = f"{error.__class__.__name__}: {error}"

                self._camera.close()
                if reconnects_remaining <= 0:
                    return
                reconnects_remaining -= 1
                if self._stop_event.wait(self._config.reconnect_delay_s):
                    return
            except Exception as error:  # defensive boundary around device backends
                with self._lock:
                    self._last_error = f"{error.__class__.__name__}: {error}"
                self._camera.close()
                return

    def _record_frame(self) -> None:
        now = monotonic()
        with self._lock:
            self._frames_captured += 1
            self._window_frames += 1
            self._last_frame_monotonic_s = now
            elapsed = now - self._window_started_s
            if elapsed >= self._config.fps_window_s:
                self._measured_fps = self._window_frames / elapsed
                self._window_frames = 0
                self._window_started_s = now
                self._last_error = None
