from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .contracts import AcquisitionSnapshot, CameraState


class AcquisitionHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class DiagnosticsConfig:
    minimum_fps: float = 15.0
    maximum_frame_age_ms: float = 500.0
    maximum_drop_ratio: float = 0.25

    def __post_init__(self) -> None:
        if self.minimum_fps < 0:
            raise ValueError("minimum_fps cannot be negative.")
        if self.maximum_frame_age_ms <= 0:
            raise ValueError("maximum_frame_age_ms must be positive.")
        if not 0.0 <= self.maximum_drop_ratio <= 1.0:
            raise ValueError("maximum_drop_ratio must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class DiagnosticsReport:
    health: AcquisitionHealth
    reason_codes: tuple[str, ...]
    snapshot: AcquisitionSnapshot


class AcquisitionDiagnostics:
    def __init__(self, config: DiagnosticsConfig | None = None) -> None:
        self._config = config or DiagnosticsConfig()

    def evaluate(self, snapshot: AcquisitionSnapshot) -> DiagnosticsReport:
        reasons: list[str] = []

        if snapshot.state is CameraState.CLOSED:
            return DiagnosticsReport(
                health=AcquisitionHealth.STOPPED,
                reason_codes=("CAMERA_CLOSED",),
                snapshot=snapshot,
            )

        if snapshot.state is CameraState.FAILED:
            reasons.append("CAMERA_FAILED")

        if snapshot.last_error:
            reasons.append("LAST_ERROR_PRESENT")

        if snapshot.last_frame_age_ms is not None:
            if snapshot.last_frame_age_ms > self._config.maximum_frame_age_ms:
                reasons.append("FRAME_STALE")

        if snapshot.frames_captured > 0:
            total = snapshot.frames_captured + snapshot.frames_dropped
            drop_ratio = snapshot.frames_dropped / total if total else 0.0
            if drop_ratio > self._config.maximum_drop_ratio:
                reasons.append("DROP_RATIO_HIGH")

        if snapshot.measured_fps > 0 and snapshot.measured_fps < self._config.minimum_fps:
            reasons.append("FPS_LOW")

        if "CAMERA_FAILED" in reasons or "FRAME_STALE" in reasons:
            health = AcquisitionHealth.UNHEALTHY
        elif reasons:
            health = AcquisitionHealth.DEGRADED
        else:
            health = AcquisitionHealth.HEALTHY

        return DiagnosticsReport(
            health=health,
            reason_codes=tuple(reasons),
            snapshot=snapshot,
        )
