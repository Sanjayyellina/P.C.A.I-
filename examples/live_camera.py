from __future__ import annotations

import argparse
from time import monotonic

import cv2

from pcai.acquisition import AcquisitionSession, AcquisitionSessionConfig, CameraConfig


def parse_source(value: str) -> int | str:
    return int(value) if value.isdigit() else value


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the P.C.A.I. live camera acquisition demo.")
    parser.add_argument("--source", default="0", help="Camera index, device path, RTSP URL, video file, or GStreamer pipeline.")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--camera-id", default="camera-0")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    config = AcquisitionSessionConfig(
        camera=CameraConfig(
            source=parse_source(args.source),
            width_px=args.width,
            height_px=args.height,
            fps=args.fps,
            camera_id=args.camera_id,
        )
    )

    last_report_s = monotonic()
    with AcquisitionSession(config) as session:
        while True:
            frame = session.read_latest(timeout_s=2.0)
            if frame is None:
                report = session.diagnostics()
                print(f"No frame: health={report.health.value} reasons={report.reason_codes}")
                continue

            if not args.headless:
                cv2.imshow("P.C.A.I. Live Acquisition", frame.image_bgr)
                key = cv2.waitKey(1) & 0xFF
                if key in {ord("q"), 27}:
                    break

            now = monotonic()
            if now - last_report_s >= 1.0:
                snapshot = session.snapshot()
                print(
                    f"camera={frame.metadata.camera_id} "
                    f"frame={frame.metadata.sequence} "
                    f"resolution={frame.metadata.width_px}x{frame.metadata.height_px} "
                    f"fps={snapshot.measured_fps:.2f} "
                    f"dropped={snapshot.frames_dropped} "
                    f"queue={snapshot.queue_depth} "
                    f"age_ms={snapshot.last_frame_age_ms or 0:.1f}"
                )
                last_report_s = now

    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
