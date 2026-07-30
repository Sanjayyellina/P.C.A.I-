"""Experimental batch evaluation for light-coloured Aleve tablet images.

This script is intentionally separate from production Cells. It measures whether
the current segmentation hypothesis is strong enough to justify integration.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import median

import cv2
import numpy as np


SOURCE_DIR = Path("/media/saika/USB/pcai-working/converted/10")
REPORT_DIR = Path("/media/saika/USB/pcai-working/reports/ten-tablet-v0")
FAILURE_DIR = REPORT_DIR / "failures"
CSV_PATH = REPORT_DIR / "results.csv"

EXPECTED_COUNT = 10
MAXIMUM_DIMENSION = 1600


@dataclass(frozen=True)
class ImageResult:
    filename: str
    predicted_count: int
    usable_regions: int
    typical_area: float
    threshold: int
    exact: bool
    error: int
    status: str


def resize_for_analysis(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    scale = min(1.0, MAXIMUM_DIMENSION / max(height, width))

    return cv2.resize(
        image,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_AREA,
    )


def segment_light_tablets(image: np.ndarray) -> tuple[np.ndarray, int]:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lightness = lab[:, :, 0]

    threshold_value = int(np.percentile(lightness, 88))

    _, mask = cv2.threshold(
        lightness,
        threshold_value,
        255,
        cv2.THRESH_BINARY,
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
    )
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)),
    )

    return mask, threshold_value


def extract_usable_contours(mask: np.ndarray) -> list[np.ndarray]:
    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    usable: list[np.ndarray] = []

    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < 1_000:
            continue

        perimeter = float(cv2.arcLength(contour, True))
        if perimeter <= 0:
            continue

        circularity = 4.0 * np.pi * area / (perimeter * perimeter)
        x, y, width, height = cv2.boundingRect(contour)
        aspect_ratio = width / height if height else 0.0

        if circularity < 0.30:
            continue
        if not 0.40 <= aspect_ratio <= 2.50:
            continue

        usable.append(contour)

    return usable


def estimate_typical_area(areas: list[float]) -> float:
    """Estimate one-tablet area without using the known tablet count."""

    if not areas:
        raise ValueError("No usable candidate areas.")

    ordered = sorted(areas)

    # Large upper-tail regions are likely touching-tablet regions.
    keep_count = max(1, int(np.ceil(len(ordered) * 0.80)))
    reference = ordered[:keep_count]

    return float(median(reference))


def analyse_image(path: Path) -> tuple[ImageResult, np.ndarray | None]:
    image = cv2.imread(str(path))

    if image is None:
        result = ImageResult(
            filename=path.name,
            predicted_count=0,
            usable_regions=0,
            typical_area=0.0,
            threshold=0,
            exact=False,
            error=-EXPECTED_COUNT,
            status="IMAGE_READ_FAILED",
        )
        return result, None

    resized = resize_for_analysis(image)
    mask, threshold_value = segment_light_tablets(resized)
    contours = extract_usable_contours(mask)

    areas = [float(cv2.contourArea(contour)) for contour in contours]

    if not areas:
        result = ImageResult(
            filename=path.name,
            predicted_count=0,
            usable_regions=0,
            typical_area=0.0,
            threshold=threshold_value,
            exact=False,
            error=-EXPECTED_COUNT,
            status="NO_USABLE_REGIONS",
        )
        return result, resized

    typical_area = estimate_typical_area(areas)

    predicted_count = sum(
        max(1, int(round(area / typical_area)))
        for area in areas
    )

    overlay = resized.copy()

    for contour, area in zip(contours, areas, strict=True):
        region_count = max(1, int(round(area / typical_area)))
        x, y, width, height = cv2.boundingRect(contour)

        colour = (0, 255, 0) if region_count == 1 else (0, 165, 255)

        cv2.rectangle(
            overlay,
            (x, y),
            (x + width, y + height),
            colour,
            3,
        )

        cv2.putText(
            overlay,
            str(region_count),
            (x, max(30, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            colour,
            2,
            cv2.LINE_AA,
        )

    exact = predicted_count == EXPECTED_COUNT

    cv2.putText(
        overlay,
        f"Predicted: {predicted_count}  Expected: {EXPECTED_COUNT}",
        (30, 55),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        (0, 255, 0) if exact else (0, 0, 255),
        3,
        cv2.LINE_AA,
    )

    result = ImageResult(
        filename=path.name,
        predicted_count=predicted_count,
        usable_regions=len(contours),
        typical_area=typical_area,
        threshold=threshold_value,
        exact=exact,
        error=predicted_count - EXPECTED_COUNT,
        status="OK",
    )

    return result, overlay


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    FAILURE_DIR.mkdir(parents=True, exist_ok=True)

    images = sorted(SOURCE_DIR.glob("*.jpg"))

    if not images:
        raise SystemExit(f"No JPEG images found in {SOURCE_DIR}")

    results: list[ImageResult] = []

    for index, path in enumerate(images, start=1):
        result, overlay = analyse_image(path)
        results.append(result)

        marker = "PASS" if result.exact else "FAIL"
        print(
            f"[{index:02d}/{len(images):02d}] {marker} "
            f"{path.name}: predicted={result.predicted_count}, "
            f"regions={result.usable_regions}, "
            f"typical_area={result.typical_area:.1f}"
        )

        if not result.exact and overlay is not None:
            cv2.imwrite(
                str(FAILURE_DIR / path.name),
                overlay,
            )

    with CSV_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "filename",
                "predicted_count",
                "usable_regions",
                "typical_area",
                "threshold",
                "exact",
                "error",
                "status",
            ],
        )
        writer.writeheader()

        for result in results:
            writer.writerow(
                {
                    "filename": result.filename,
                    "predicted_count": result.predicted_count,
                    "usable_regions": result.usable_regions,
                    "typical_area": round(result.typical_area, 2),
                    "threshold": result.threshold,
                    "exact": result.exact,
                    "error": result.error,
                    "status": result.status,
                }
            )

    exact_count = sum(result.exact for result in results)
    total = len(results)
    accuracy = 100.0 * exact_count / total

    absolute_errors = [abs(result.error) for result in results]
    mean_absolute_error = sum(absolute_errors) / total

    predictions: dict[int, int] = {}
    for result in results:
        predictions[result.predicted_count] = (
            predictions.get(result.predicted_count, 0) + 1
        )

    print("\n=== TEN-TABLET DATASET V0 SUMMARY ===")
    print(f"images: {total}")
    print(f"exact counts: {exact_count}")
    print(f"exact-count accuracy: {accuracy:.2f}%")
    print(f"mean absolute count error: {mean_absolute_error:.3f}")
    print(f"prediction distribution: {dict(sorted(predictions.items()))}")
    print(f"CSV report: {CSV_PATH}")
    print(f"failure overlays: {FAILURE_DIR}")


if __name__ == "__main__":
    main()
