from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

import numpy as np


class CameraState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    RUNNING = "running"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CameraConfig:
    source: int | str = 0
    width_px: int = 1280
    height_px: int = 720
    fps: float = 30.0
    backend: int | None = None
    buffer_size: int = 2
    fourcc: str | None = "MJPG"
    camera_id: str = "camera-0"

    def __post_init__(self) -> None:
        if self.width_px <= 0 or self.height_px <= 0:
            raise ValueError("Camera dimensions must be positive.")
        if self.fps <= 0:
            raise ValueError("Camera FPS must be positive.")
        if self.buffer_size <= 0:
            raise ValueError("Buffer size must be positive.")
        if self.fourcc is not None and len(self.fourcc) != 4:
            raise ValueError("fourcc must contain exactly four characters.")


@dataclass(frozen=True, slots=True)
class FrameMetadata:
    sequence: int
    captured_at_utc: datetime
    monotonic_ns: int
    camera_id: str
    width_px: int
    height_px: int


@dataclass(frozen=True, slots=True)
class CameraFrame:
    image_bgr: np.ndarray
    metadata: FrameMetadata

    def __post_init__(self) -> None:
        if not isinstance(self.image_bgr, np.ndarray):
            raise TypeError("image_bgr must be a numpy array.")
        if self.image_bgr.ndim != 3 or self.image_bgr.shape[2] != 3:
            raise ValueError("image_bgr must have shape (height, width, 3).")
        if self.image_bgr.shape[1] != self.metadata.width_px:
            raise ValueError("Frame width does not match metadata.")
        if self.image_bgr.shape[0] != self.metadata.height_px:
            raise ValueError("Frame height does not match metadata.")


@dataclass(frozen=True, slots=True)
class AcquisitionSnapshot:
    state: CameraState
    frames_captured: int
    frames_dropped: int
    measured_fps: float
    queue_depth: int
    last_frame_age_ms: float | None
    last_error: str | None


class CameraSource(ABC):
    @property
    @abstractmethod
    def state(self) -> CameraState:
        raise NotImplementedError

    @abstractmethod
    def open(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def read(self) -> CameraFrame:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    def __enter__(self) -> "CameraSource":
        self.open()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


class FrameConsumer(Protocol):
    def __call__(self, frame: CameraFrame) -> None: ...
