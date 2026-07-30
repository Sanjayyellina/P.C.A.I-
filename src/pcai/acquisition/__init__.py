"""Live camera acquisition for the P.C.A.I. vision engine."""

from .capture_worker import CaptureWorker, CaptureWorkerConfig
from .contracts import (
    AcquisitionSnapshot,
    CameraConfig,
    CameraFrame,
    CameraSource,
    CameraState,
    FrameMetadata,
)
from .diagnostics import (
    AcquisitionDiagnostics,
    AcquisitionHealth,
    DiagnosticsConfig,
    DiagnosticsReport,
)
from .exceptions import (
    AcquisitionError,
    CameraOpenError,
    CameraReadError,
    CameraStateError,
    CaptureWorkerError,
)
from .frame_queue import FrameQueue
from .opencv_camera import OpenCvCamera
from .session import AcquisitionSession, AcquisitionSessionConfig

__all__ = [
    "AcquisitionDiagnostics",
    "AcquisitionError",
    "AcquisitionHealth",
    "AcquisitionSession",
    "AcquisitionSessionConfig",
    "AcquisitionSnapshot",
    "CameraConfig",
    "CameraFrame",
    "CameraOpenError",
    "CameraReadError",
    "CameraSource",
    "CameraState",
    "CameraStateError",
    "CaptureWorker",
    "CaptureWorkerConfig",
    "CaptureWorkerError",
    "DiagnosticsConfig",
    "DiagnosticsReport",
    "FrameMetadata",
    "FrameQueue",
    "OpenCvCamera",
]
