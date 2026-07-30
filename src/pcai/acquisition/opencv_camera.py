from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from time import monotonic_ns
from typing import Final

import cv2

from .contracts import CameraConfig, CameraFrame, CameraSource, CameraState, FrameMetadata
from .exceptions import CameraOpenError, CameraReadError, CameraStateError


_DEFAULT_BACKEND: Final[int] = cv2.CAP_ANY


class OpenCvCamera(CameraSource):
    """Synchronous OpenCV-backed camera source.

    The class supports USB cameras, device paths, video files, RTSP URLs and
    Jetson GStreamer pipelines through the same ``CameraConfig.source`` field.
    """

    def __init__(self, config: CameraConfig) -> None:
        self._config = config
        self._capture: cv2.VideoCapture | None = None
        self._state = CameraState.CLOSED
        self._sequence = 0
        self._lock = RLock()

    @property
    def state(self) -> CameraState:
        with self._lock:
            return self._state

    @property
    def config(self) -> CameraConfig:
        return self._config

    def open(self) -> None:
        with self._lock:
            if self._state in {CameraState.OPEN, CameraState.RUNNING}:
                return

            backend = self._config.backend if self._config.backend is not None else _DEFAULT_BACKEND
            capture = cv2.VideoCapture(self._config.source, backend)

            if not capture.isOpened():
                capture.release()
                self._state = CameraState.FAILED
                raise CameraOpenError(
                    f"Could not open camera source {self._config.source!r} "
                    f"with backend {backend}."
                )

            self._apply_configuration(capture)
            self._capture = capture
            self._sequence = 0
            self._state = CameraState.OPEN

    def read(self) -> CameraFrame:
        with self._lock:
            if self._state not in {CameraState.OPEN, CameraState.RUNNING}:
                raise CameraStateError(
                    f"Camera must be open before reading; current state is {self._state.value}."
                )

            capture = self._capture
            if capture is None:
                self._state = CameraState.FAILED
                raise CameraStateError("Camera capture handle is unavailable.")

            ok, image_bgr = capture.read()
            captured_monotonic_ns = monotonic_ns()
            captured_at_utc = datetime.now(timezone.utc)

            if not ok or image_bgr is None:
                self._state = CameraState.FAILED
                raise CameraReadError(
                    f"Camera source {self._config.source!r} failed to return a frame."
                )

            if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
                self._state = CameraState.FAILED
                raise CameraReadError(
                    f"Camera returned unsupported frame shape {image_bgr.shape!r}."
                )

            height_px, width_px = image_bgr.shape[:2]
            metadata = FrameMetadata(
                sequence=self._sequence,
                captured_at_utc=captured_at_utc,
                monotonic_ns=captured_monotonic_ns,
                camera_id=self._config.camera_id,
                width_px=width_px,
                height_px=height_px,
            )
            self._sequence += 1
            self._state = CameraState.RUNNING

            # Copy isolates downstream processing from mutable backend buffers.
            return CameraFrame(image_bgr=image_bgr.copy(), metadata=metadata)

    def close(self) -> None:
        with self._lock:
            capture = self._capture
            self._capture = None
            if capture is not None:
                capture.release()
            self._state = CameraState.CLOSED

    def _apply_configuration(self, capture: cv2.VideoCapture) -> None:
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, float(self._config.width_px))
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self._config.height_px))
        capture.set(cv2.CAP_PROP_FPS, float(self._config.fps))
        capture.set(cv2.CAP_PROP_BUFFERSIZE, float(self._config.buffer_size))

        if self._config.fourcc is not None:
            capture.set(
                cv2.CAP_PROP_FOURCC,
                float(cv2.VideoWriter_fourcc(*self._config.fourcc)),
            )
