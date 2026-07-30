from __future__ import annotations


class AcquisitionError(Exception):
    """Base error raised by the live acquisition subsystem."""

    code = "ACQUISITION_ERROR"


class CameraOpenError(AcquisitionError):
    code = "CAMERA_OPEN_FAILED"


class CameraReadError(AcquisitionError):
    code = "CAMERA_READ_FAILED"


class CameraStateError(AcquisitionError):
    code = "CAMERA_STATE_INVALID"


class CaptureWorkerError(AcquisitionError):
    code = "CAPTURE_WORKER_FAILED"
