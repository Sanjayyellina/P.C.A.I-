"""Run the local P.C.A.I. live-count demonstration dashboard.

This is deliberately a local, dependency-free UI for the Jetson.  It keeps
camera capture, calibration, candidate evidence, count decision, and capture
records visible to an operator.  It is an experimental counting UI, not a
medical device or dispensing authorization interface.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4

import cv2
import numpy as np

from pcai.cells.candidate_observation import (
    CandidateConfiguration,
    CandidateObservationInput,
    CandidateStatus,
    DeterministicCandidateObservationCell,
    ForegroundPolarity,
)
from pcai.cells.classical_counting import (
    ClassicalCountingConfiguration,
    ClassicalCountingInput,
    StrictClassicalCountingCell,
)
from pcai.cells.tray_geometry import (
    GeometryStatus,
    ProjectiveTrayGeometryCell,
    TrayGeometryConfiguration,
    TrayGeometryInput,
)
from pcai.shared.identifiers import FrameId


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE = ROOT / "runtime_data" / "live_dashboard_state.json"
DEFAULT_CAPTURE_ROOT = ROOT / "runtime_data" / "captures"
HTML_PATH = Path(__file__).resolve().parent / "dashboard" / "index.html"


@dataclass(frozen=True, slots=True)
class Calibration:
    source_points_xy: tuple[tuple[float, float], ...]
    canonical_width_px: int = 1200
    canonical_height_px: int = 800
    tray_width_mm: float = 300.0
    tray_height_mm: float = 200.0

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "Calibration":
        points = payload.get("source_points_xy")
        if not isinstance(points, list) or len(points) != 4:
            raise ValueError("Exactly four tray corners are required.")
        parsed = tuple((float(point[0]), float(point[1])) for point in points)
        width = int(payload.get("canonical_width_px", 1200))
        height = int(payload.get("canonical_height_px", 800))
        tray_width = float(payload.get("tray_width_mm", 300.0))
        tray_height = float(payload.get("tray_height_mm", 200.0))
        if width < 400 or height < 300:
            raise ValueError("Canonical tray dimensions are too small.")
        if tray_width <= 0.0 or tray_height <= 0.0:
            raise ValueError("Tray dimensions must be positive.")
        return cls(parsed, width, height, tray_width, tray_height)


class LiveCountService:
    """Owns the camera and produces evidence-backed live count observations."""

    def __init__(
        self,
        *,
        device: int,
        width: int,
        height: int,
        fps: float,
        state_path: Path,
        capture_root: Path,
    ) -> None:
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.state_path = state_path
        self.capture_root = capture_root
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.capture_thread: threading.Thread | None = None
        self.camera: cv2.VideoCapture | None = None
        self.raw_bgr: np.ndarray | None = None
        self.analysis_bgr: np.ndarray | None = None
        self.mask: np.ndarray | None = None
        self.last_capture_dir: Path | None = None
        self.latest_observation: dict[str, Any] = {
            "state": "STARTING",
            "message": "Opening camera.",
            "candidate_count": None,
            "published_count": None,
            "reason_codes": [],
            "updated_at": None,
        }
        self.calibration = self._load_calibration()
        self.last_analysis_at = 0.0
        self.frame_count = 0
        self.measured_fps = 0.0
        self.started_at = time.monotonic()

    def _load_calibration(self) -> Calibration | None:
        if not self.state_path.exists():
            return None
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            return Calibration.from_payload(payload["calibration"])
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def _save_calibration(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "saved_at": self._now(),
            "calibration": asdict(self.calibration) if self.calibration else None,
        }
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.state_path)

    def start(self) -> None:
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.capture_thread:
            self.capture_thread.join(timeout=3)
        if self.camera:
            self.camera.release()

    def _capture_loop(self) -> None:
        camera = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        camera.set(cv2.CAP_PROP_FPS, self.fps)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.camera = camera
        if not camera.isOpened():
            with self.lock:
                self.latest_observation = self._observation(
                    state="CAMERA_ERROR",
                    message=f"Could not open /dev/video{self.device}.",
                )
            return

        while not self.stop_event.is_set():
            ok, frame = camera.read()
            if not ok or frame is None:
                with self.lock:
                    self.latest_observation = self._observation(
                        state="CAMERA_ERROR",
                        message="The camera did not return a frame.",
                    )
                time.sleep(0.1)
                continue

            self.frame_count += 1
            elapsed = max(time.monotonic() - self.started_at, 0.001)
            self.measured_fps = self.frame_count / elapsed
            with self.lock:
                self.raw_bgr = frame.copy()

            if time.monotonic() - self.last_analysis_at >= 0.12:
                self._analyse(frame)
                self.last_analysis_at = time.monotonic()

        camera.release()

    def _analyse(self, frame: np.ndarray) -> None:
        with self.lock:
            calibration = self.calibration
        if calibration is None:
            preview = frame.copy()
            cv2.putText(
                preview,
                "CALIBRATION REQUIRED — click four tray corners",
                (28, 48),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 0, 255),
                2,
                cv2.LINE_AA,
            )
            with self.lock:
                self.analysis_bgr = preview
                self.mask = None
                self.latest_observation = self._observation(
                    state="CALIBRATION_REQUIRED",
                    message="Click the tray corners in the live feed, starting at top-left.",
                )
            return

        destination = np.array(
            [
                (0.0, 0.0),
                (float(calibration.canonical_width_px - 1), 0.0),
                (
                    float(calibration.canonical_width_px - 1),
                    float(calibration.canonical_height_px - 1),
                ),
                (0.0, float(calibration.canonical_height_px - 1)),
            ],
            dtype=np.float32,
        )
        geometry = ProjectiveTrayGeometryCell().measure(
            TrayGeometryInput(
                frame_id=FrameId(str(uuid4())),
                image_bgr=frame,
                source_points_xy=np.array(calibration.source_points_xy, dtype=np.float32),
                destination_points_xy=destination,
                configuration=TrayGeometryConfiguration(
                    canonical_width_px=calibration.canonical_width_px,
                    canonical_height_px=calibration.canonical_height_px,
                    tray_width_mm=calibration.tray_width_mm,
                    tray_height_mm=calibration.tray_height_mm,
                    maximum_reprojection_error_px=2.0,
                ),
            )
        )
        if geometry.status is not GeometryStatus.PASS:
            with self.lock:
                self.latest_observation = self._observation(
                    state="REVIEW_REQUIRED",
                    message="Tray calibration is invalid. Recalibrate before counting.",
                    reason_codes=list(geometry.reason_codes),
                )
            return

        candidates = DeterministicCandidateObservationCell().observe(
            CandidateObservationInput(
                frame_id=geometry.frame_id,
                canonical_tray_bgr=geometry.canonical_tray_bgr,
                tray_mask=geometry.tray_mask,
                pixels_per_mm_x=geometry.pixels_per_mm_x,
                pixels_per_mm_y=geometry.pixels_per_mm_y,
                configuration=CandidateConfiguration(
                    foreground_threshold=180,
                    morphology_kernel_px=5,
                    minimum_area_mm2=35.0,
                    maximum_single_area_mm2=650.0,
                    maximum_supported_area_mm2=1_600.0,
                    minimum_solidity_single=0.82,
                    touching_area_multiplier=1.25,
                    foreground_polarity=ForegroundPolarity.LIGHT_ON_DARK,
                ),
            )
        )
        decision = StrictClassicalCountingCell().count(
            ClassicalCountingInput(
                frame_id=geometry.frame_id,
                candidate_set=candidates,
                configuration=ClassicalCountingConfiguration(
                    allow_touching_regions=False,
                    reject_unknown_regions=True,
                    reject_partial_objects=True,
                    reject_possible_stacks=True,
                ),
            )
        )
        annotated = geometry.canonical_tray_bgr.copy()
        colors = {
            CandidateStatus.SINGLE_CANDIDATE: (0, 210, 105),
            CandidateStatus.TOUCHING_REGION: (0, 170, 255),
            CandidateStatus.PARTIAL_OBJECT: (0, 100, 255),
            CandidateStatus.UNKNOWN: (0, 0, 255),
            CandidateStatus.ARTIFACT: (130, 130, 130),
            CandidateStatus.POSSIBLE_STACK: (0, 0, 255),
            CandidateStatus.FOREIGN_OBJECT: (0, 0, 255),
        }
        for candidate in candidates.candidates:
            color = colors[candidate.status]
            cv2.drawContours(annotated, [candidate.contour], -1, color, 2)
            x, y, _width, _height = candidate.bounding_box_xywh
            cv2.putText(
                annotated,
                candidate.status.replace("_", " "),
                (x, max(y - 8, 22)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                2,
                cv2.LINE_AA,
            )

        counted = decision.candidate_count
        state = "COUNTED" if counted is not None else "REVIEW_REQUIRED"
        headline = f"{state}: {counted if counted is not None else '—'}"
        headline_color = (0, 210, 105) if counted is not None else (0, 100, 255)
        cv2.rectangle(annotated, (0, 0), (530, 70), (25, 25, 25), -1)
        cv2.putText(
            annotated,
            headline,
            (20, 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            headline_color,
            2,
            cv2.LINE_AA,
        )
        with self.lock:
            self.analysis_bgr = annotated
            self.mask = candidates.foreground_mask.copy()
            self.latest_observation = self._observation(
                state=state,
                message=(
                    "Experimental count — capture the result for the test record."
                    if counted is not None
                    else "Ambiguous regions detected. Reposition tablets or review the image."
                ),
                candidate_count=len(candidates.candidates),
                published_count=counted,
                reason_codes=list(decision.reason_codes),
                candidate_statuses=[candidate.status for candidate in candidates.candidates],
            )

    def _observation(self, *, state: str, message: str, **fields: Any) -> dict[str, Any]:
        return {
            "state": state,
            "message": message,
            "candidate_count": None,
            "published_count": None,
            "reason_codes": [],
            "candidate_statuses": [],
            "updated_at": self._now(),
            **fields,
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def status(self) -> dict[str, Any]:
        with self.lock:
            source_shape = self.raw_bgr.shape if self.raw_bgr is not None else None
            return {
                **self.latest_observation,
                "camera": {
                    "device": self.device,
                    "requested_width": self.width,
                    "requested_height": self.height,
                    "measured_fps": round(self.measured_fps, 1),
                    "source_width": int(source_shape[1]) if source_shape is not None else None,
                    "source_height": int(source_shape[0]) if source_shape is not None else None,
                },
                "calibration": asdict(self.calibration) if self.calibration else None,
                "disclaimer": "Experimental counting screen. It does not identify tablets or authorize dispensing.",
            }

    def set_calibration(self, payload: dict[str, Any]) -> Calibration:
        calibration = Calibration.from_payload(payload)
        with self.lock:
            self.calibration = calibration
            self._save_calibration()
        return calibration

    def clear_calibration(self) -> None:
        with self.lock:
            self.calibration = None
            self._save_calibration()

    def jpeg(self, *, analysis: bool) -> bytes | None:
        with self.lock:
            frame = self.analysis_bgr if analysis else self.raw_bgr
            if frame is None:
                return None
            ok, encoded = cv2.imencode(".jpg", frame, (cv2.IMWRITE_JPEG_QUALITY, 85))
        return encoded.tobytes() if ok else None

    def capture_result(self) -> dict[str, Any]:
        with self.lock:
            if self.analysis_bgr is None:
                raise RuntimeError("No camera result is available yet.")
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            capture_id = f"live-{timestamp}-{uuid4().hex[:8]}"
            capture_dir = self.capture_root / capture_id
            capture_dir.mkdir(parents=True, exist_ok=False)
            cv2.imwrite(str(capture_dir / "result.jpg"), self.analysis_bgr)
            if self.raw_bgr is not None:
                cv2.imwrite(str(capture_dir / "camera.jpg"), self.raw_bgr)
            if self.mask is not None:
                cv2.imwrite(str(capture_dir / "foreground-mask.png"), self.mask)
            record = {
                "capture_id": capture_id,
                "captured_at": self._now(),
                "observation": self.latest_observation,
                "camera": self.status()["camera"],
                "calibration": asdict(self.calibration) if self.calibration else None,
                "artifacts": {
                    "result": "result.jpg",
                    "camera": "camera.jpg" if self.raw_bgr is not None else None,
                    "foreground_mask": "foreground-mask.png" if self.mask is not None else None,
                },
            }
            (capture_dir / "record.json").write_text(
                json.dumps(record, indent=2), encoding="utf-8"
            )
            self.last_capture_dir = capture_dir
            return {
                "capture_id": capture_id,
                "record": record,
                "result_url": "/last-result.jpg",
            }

    def last_result_jpeg(self) -> bytes | None:
        with self.lock:
            if self.last_capture_dir is None:
                return None
            path = self.last_capture_dir / "result.jpg"
            return path.read_bytes() if path.exists() else None


class DashboardHandler(BaseHTTPRequestHandler):
    service: LiveCountService

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in {"/", "/index.html"}:
            self._send_bytes(HTTPStatus.OK, "text/html; charset=utf-8", HTML_PATH.read_bytes())
        elif path == "/api/status":
            self._send_json(HTTPStatus.OK, self.service.status())
        elif path == "/raw.mjpg":
            self._stream(analysis=False)
        elif path == "/analysis.mjpg":
            self._stream(analysis=True)
        elif path == "/last-result.jpg":
            image = self.service.last_result_jpeg()
            if image is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "No result captured yet"})
            else:
                self._send_bytes(HTTPStatus.OK, "image/jpeg", image)
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
            path = self.path.split("?", 1)[0]
            if path == "/api/calibration":
                calibration = self.service.set_calibration(payload)
                self._send_json(HTTPStatus.OK, {"calibration": asdict(calibration)})
            elif path == "/api/clear-calibration":
                self.service.clear_calibration()
                self._send_json(HTTPStatus.OK, {"cleared": True})
            elif path == "/api/capture":
                self._send_json(HTTPStatus.CREATED, self.service.capture_result())
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        except (RuntimeError, ValueError, json.JSONDecodeError) as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length))

    def _stream(self, *, analysis: bool) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            while True:
                image = self.service.jpeg(analysis=analysis)
                if image is not None:
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(image)}\r\n\r\n".encode())
                    self.wfile.write(image)
                    self.wfile.write(b"\r\n")
                time.sleep(0.12)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        self._send_bytes(status, "application/json; charset=utf-8", json.dumps(payload).encode())

    def _send_bytes(self, status: HTTPStatus, content_type: str, payload: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="P.C.A.I. local live-count dashboard")
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8088)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--capture-root", type=Path, default=DEFAULT_CAPTURE_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    service = LiveCountService(
        device=args.device,
        width=args.width,
        height=args.height,
        fps=args.fps,
        state_path=args.state_file,
        capture_root=args.capture_root,
    )
    DashboardHandler.service = service
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    service.start()
    print(f"P.C.A.I. dashboard: http://<jetson-ip>:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        service.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
