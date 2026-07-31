from __future__ import annotations

import argparse
import time
from collections import Counter, deque
from pathlib import Path

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a headless classical pill-counting trial from /dev/video0."
    )
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--frames", type=int, default=300)
    parser.add_argument("--min-area", type=float, default=250.0)
    parser.add_argument("--max-area", type=float, default=20000.0)
    parser.add_argument("--margin", type=float, default=0.04)
    parser.add_argument("--stability-window", type=int, default=30)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/pcai-classical-trial"),
    )
    return parser.parse_args()


def open_camera(args: argparse.Namespace) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(args.device, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, args.fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open /dev/video{args.device}")
    return cap


def crop_workspace(frame: np.ndarray, margin_ratio: float) -> tuple[np.ndarray, tuple[int, int]]:
    height, width = frame.shape[:2]
    margin_x = int(width * margin_ratio)
    margin_y = int(height * margin_ratio)
    crop = frame[margin_y : height - margin_y, margin_x : width - margin_x]
    return crop, (margin_x, margin_y)


def segment_pills(workspace: np.ndarray) -> tuple[np.ndarray, str]:
    gray = cv2.cvtColor(workspace, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (7, 7), 0)

    _, bright = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, dark = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    border = np.zeros(gray.shape, dtype=np.uint8)
    border[:10, :] = 255
    border[-10:, :] = 255
    border[:, :10] = 255
    border[:, -10:] = 255

    bright_border = int(np.count_nonzero(cv2.bitwise_and(bright, border)))
    dark_border = int(np.count_nonzero(cv2.bitwise_and(dark, border)))
    mask = bright if bright_border < dark_border else dark
    polarity = "bright-on-dark" if mask is bright else "dark-on-bright"

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    return mask, polarity


def count_candidates(
    mask: np.ndarray,
    min_area: float,
    max_area: float,
) -> tuple[int, list[np.ndarray], list[float]]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    accepted: list[np.ndarray] = []
    areas: list[float] = []

    height, width = mask.shape[:2]
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < min_area or area > max_area:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if x <= 1 or y <= 1 or x + w >= width - 1 or y + h >= height - 1:
            continue
        perimeter = float(cv2.arcLength(contour, True))
        if perimeter <= 0:
            continue
        circularity = 4.0 * np.pi * area / (perimeter * perimeter)
        if circularity < 0.18:
            continue
        accepted.append(contour)
        areas.append(area)

    return len(accepted), accepted, areas


def annotate(
    workspace: np.ndarray,
    contours: list[np.ndarray],
    count: int,
    stable_count: int | None,
    polarity: str,
    measured_fps: float,
) -> np.ndarray:
    output = workspace.copy()
    cv2.drawContours(output, contours, -1, (0, 255, 0), 2)
    for index, contour in enumerate(contours, start=1):
        x, y, w, h = cv2.boundingRect(contour)
        cv2.putText(
            output,
            str(index),
            (x, max(18, y - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    label = f"raw={count} stable={stable_count} fps={measured_fps:.1f} {polarity}"
    cv2.putText(
        output,
        label,
        (25, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 0, 255),
        3,
        cv2.LINE_AA,
    )
    return output


def main() -> int:
    args = parse_args()
    if args.frames <= 0:
        raise ValueError("--frames must be positive")
    if not 0.0 <= args.margin < 0.45:
        raise ValueError("--margin must be between 0 and 0.45")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    cap = open_camera(args)

    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"Camera: /dev/video{args.device}")
    print(f"Mode: {actual_width}x{actual_height} @ {actual_fps:.2f} FPS")
    print("Place pills on the tray and keep the scene still.")
    print()

    history: deque[int] = deque(maxlen=args.stability_window)
    started = time.perf_counter()
    last_saved_count: int | None = None

    try:
        for frame_index in range(1, args.frames + 1):
            ok, frame = cap.read()
            if not ok or frame is None:
                raise RuntimeError(f"Frame read failed at frame {frame_index}")

            workspace, _ = crop_workspace(frame, args.margin)
            mask, polarity = segment_pills(workspace)
            count, contours, areas = count_candidates(mask, args.min_area, args.max_area)
            history.append(count)

            stable_count = None
            stability = 0.0
            if history:
                frequencies = Counter(history)
                stable_count, occurrences = frequencies.most_common(1)[0]
                stability = occurrences / len(history)

            elapsed = time.perf_counter() - started
            measured_fps = frame_index / elapsed if elapsed > 0 else 0.0

            if frame_index % 15 == 0:
                median_area = float(np.median(areas)) if areas else 0.0
                print(
                    f"frame={frame_index:04d} raw={count:3d} "
                    f"stable={stable_count!s:>3} stability={stability:.2f} "
                    f"median_area={median_area:.1f} fps={measured_fps:.1f}"
                )

            should_save = (
                frame_index in {1, args.frames}
                or frame_index % 60 == 0
                or (stable_count is not None and stable_count != last_saved_count and stability >= 0.80)
            )
            if should_save:
                annotated = annotate(
                    workspace,
                    contours,
                    count,
                    stable_count,
                    polarity,
                    measured_fps,
                )
                cv2.imwrite(str(args.output_dir / f"frame_{frame_index:04d}.jpg"), annotated)
                cv2.imwrite(str(args.output_dir / f"mask_{frame_index:04d}.png"), mask)
                if stability >= 0.80:
                    last_saved_count = stable_count

    finally:
        cap.release()

    final_stable = Counter(history).most_common(1)[0][0] if history else None
    final_stability = (
        Counter(history).most_common(1)[0][1] / len(history) if history else 0.0
    )
    print()
    print(f"FINAL STABLE COUNT: {final_stable}")
    print(f"FINAL STABILITY:    {final_stability:.3f}")
    print(f"ARTIFACTS:          {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
