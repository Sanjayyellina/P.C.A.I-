from __future__ import annotations

from datetime import timezone

import numpy as np
import pytest

from pcai.acquisition import (
    CameraConfig,
    CameraOpenError,
    CameraReadError,
    CameraState,
    CameraStateError,
    OpenCvCamera,
)


class FakeVideoCapture:
    def __init__(self, source: int | str, backend: int) -> None:
        self.source = source
        self.backend = backend
        self.opened = True
        self.released = False
        self.properties: dict[int, float] = {}
        self.frames: list[tuple[bool, np.ndarray | None]] = [
            (True, np.zeros((24, 32, 3), dtype=np.uint8))
        ]

    def isOpened(self) -> bool:
        return self.opened

    def set(self, prop: int, value: float) -> bool:
        self.properties[prop] = value
        return True

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self.frames:
            return self.frames.pop(0)
        return False, None

    def release(self) -> None:
        self.released = True
        self.opened = False


def test_open_read_close_lifecycle(monkeypatch) -> None:
    created: list[FakeVideoCapture] = []

    def factory(source: int | str, backend: int) -> FakeVideoCapture:
        capture = FakeVideoCapture(source, backend)
        created.append(capture)
        return capture

    monkeypatch.setattr("pcai.acquisition.opencv_camera.cv2.VideoCapture", factory)

    camera = OpenCvCamera(
        CameraConfig(
            source=0,
            width_px=32,
            height_px=24,
            fps=30.0,
            camera_id="test-camera",
        )
    )

    camera.open()
    frame = camera.read()
    camera.close()

    assert len(created) == 1
    assert frame.image_bgr.shape == (24, 32, 3)
    assert frame.metadata.sequence == 0
    assert frame.metadata.camera_id == "test-camera"
    assert frame.metadata.captured_at_utc.tzinfo is timezone.utc
    assert camera.state is CameraState.CLOSED
    assert created[0].released is True


def test_read_requires_open_camera() -> None:
    camera = OpenCvCamera(CameraConfig())

    with pytest.raises(CameraStateError, match="must be open"):
        camera.read()


def test_open_failure_sets_failed_state(monkeypatch) -> None:
    def factory(source: int | str, backend: int) -> FakeVideoCapture:
        capture = FakeVideoCapture(source, backend)
        capture.opened = False
        return capture

    monkeypatch.setattr("pcai.acquisition.opencv_camera.cv2.VideoCapture", factory)
    camera = OpenCvCamera(CameraConfig(source=9))

    with pytest.raises(CameraOpenError, match="Could not open"):
        camera.open()

    assert camera.state is CameraState.FAILED


def test_read_failure_sets_failed_state(monkeypatch) -> None:
    capture = FakeVideoCapture(0, 0)
    capture.frames = [(False, None)]
    monkeypatch.setattr(
        "pcai.acquisition.opencv_camera.cv2.VideoCapture",
        lambda source, backend: capture,
    )
    camera = OpenCvCamera(CameraConfig())
    camera.open()

    with pytest.raises(CameraReadError, match="failed to return a frame"):
        camera.read()

    assert camera.state is CameraState.FAILED


def test_read_returns_copy_of_backend_buffer(monkeypatch) -> None:
    backend_frame = np.zeros((10, 10, 3), dtype=np.uint8)
    capture = FakeVideoCapture(0, 0)
    capture.frames = [(True, backend_frame)]
    monkeypatch.setattr(
        "pcai.acquisition.opencv_camera.cv2.VideoCapture",
        lambda source, backend: capture,
    )
    camera = OpenCvCamera(CameraConfig(width_px=10, height_px=10))
    camera.open()

    frame = camera.read()
    backend_frame[:, :, :] = 255

    assert int(frame.image_bgr.max()) == 0
