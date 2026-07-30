"""Evaluate the experimental classical counting baseline.

This remains outside the production Cells. It exists to compare changing
physical setups and segmentation profiles against known-count datasets.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

import cv2
import numpy as np


DEFAULT_PROFILE = Path("configs/vision_setups/phone_wood_v0.json")


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


def load_profile(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        profile = json.load(file)

    required_sections = {
        "profile_id",
        "analysis",
        "segmentation",
        "candidate_filter",
    }

    missing = required_sections.difference(profile)

    if missing:
        raise ValueError(
            f"Profile {path} is missing sections: {sorted(missing)}"
        )

    return profile


def resize_for_analysis(
    image: np.ndarray,
    maximum_dimension: int,
) -> np.ndarray:
    height, width = image.shape[:2]
    scale = min(1.0, maximum_dimension / max(height, width))

    return cv2.resize(
        image,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_AREA,
    )


def segment_light_tablets(
    image: np.ndarray,
    profile: dict[str, Any],
) -> tuple[np.ndarray, int]:
    analysis = profile["analysis"]
    segmentation = profile["segmentation"]

    if analysis["colour_space"] != "LAB":
        raise ValueError("V0 currently supports only LAB colour space.")

    if analysis["object_polarity"] != "LIGHT":
        raise ValueError("V0 currently supports only light objects.")

    if segmentation["strategy"] != "LIGHTNESS_PERCENTILE":
        raise ValueError(
            "V0 currently supports only LIGHTNESS_PERCENTILE segmentation."
        )

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lightness = lab[:, :, 0]

    threshold_value = int(
        np.percentile(
            lightness,
            float(segmentation["lightness_percentile"]),
        )
    )

    _, mask = cv2.threshold(
        lightness,
        threshold_value,
        255,
        cv2.THRESH_BINARY,
    )

    opening_size = int(segmentation["opening_kernel_px"])
    closing_size = int(segmentation["closing_kernel_px"])

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (opening_size, opening_size),
        ),
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (closing_size, closing_size),
        ),
    )

    return mask, threshold_value


def extract_usable_contours(
    mask: np.ndarray,
    profile: dict[str, Any],
) -> list[np.ndarray]:
    candidate_filter = profile["candidate_filter"]

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    usable: list[np.ndarray] = []

    for contour in contours:
        area = float(cv2.contourArea(contour))

        if area < float(candidate_filter["minimum_area_px2"]):
            continue

        perimeter = float(cv2.arcLength(contour, True))

        if perimeter <= 0:
            continue

        circularity = (
            4.0 * np.pi * area / (perimeter * perimeter)
        )

        _, _, width, height = cv2.boundingRect(contour)
        aspect_ratio = width / height if height else 0.0

        if circularity < float(
            candidate_filter["minimum_circularity"]
        ):
            continue

        if not (
            float(candidate_filter["minimum_aspect_ratio"])
            <= aspect_ratio
            <= float(candidate_filter["maximum_aspect_ratio"])
        ):
            continue

        usable.append(contour)

    return usable


def estimate_typical_area(areas: list[float]) -> float:
    if not areas:
        raise ValueError("No usable candidate areas.")

    ordered = sorted(areas)
    keep_count = max(1, int(np.ceil(len(ordered) * 0.80)))

    return float(median(ordered[:keep_count]))


def analyse_image(
    path: Path,
    profile: dict[str, Any],
    expected_count: int,
) -> tuple[ImageResult, np.ndarray | None]:
    image = cv2.imread(str(path))

    if image is None:
        return (
            ImageResult(
                filename=path.name,
                predicted_count=0,
                usable_regions=0,
                typical_area=0.0,
                threshold=0,
                exact=False,
                error=-expected_count,
                status="IMAGE_READ_FAILED",
            ),
            None,
        )

    resized = resize_for_analysis(
        image,
        int(profile["analysis"]["maximum_dimension_px"]),
    )

    mask, threshold_value = segment_light_tablets(
        resized,
        profile,
    )

    contours = extract_usable_contours(
        mask,
        profile,
    )

    areas = [
        float(cv2.contourArea(contour))
        for contour in contours
    ]

    if not areas:
        return (
            ImageResult(
                filename=path.name,
                predicted_count=0,
                usable_regions=0,
                typical_area=0.0,
                threshold=threshold_value,
                exact=False,
                error=-expected_count,
                status="NO_USABLE_REGIONS",
            ),
            resized,
        )

    typical_area = estimate_typical_area(areas)

    contributions = [
        max(1, int(round(area / typical_area)))
        for area in areas
    ]

    predicted_count = sum(contributions)
    exact = predicted_count == expected_count

    overlay = resized.copy()

    for contour, contribution in zip(
        contours,
        contributions,
        strict=True,
    ):
        x, y, width, height = cv2.boundingRect(contour)

        colour = (
            (0, 255, 0)
            if contribution == 1
            else (0, 165, 255)
        )

        cv2.rectangle(
            overlay,
            (x, y),
            (x + width, y + height),
            colour,
            3,
        )

        cv2.putText(
            overlay,
            str(contribution),
            (x, max(30, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            colour,
            2,
            cv2.LINE_AA,
        )

    cv2.putText(
        overlay,
        f"Predicted: {predicted_count}  Expected: {expected_count}",
        (30, 55),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        (0, 255, 0) if exact else (0, 0, 255),
        3,
        cv2.LINE_AA,
    )

    return (
        ImageResult(
            filename=path.name,
            predicted_count=predicted_count,
            usable_regions=len(contours),
            typical_area=typical_area,
            threshold=threshold_value,
            exact=exact,
            error=predicted_count - expected_count,
            status="OK",
        ),
        overlay,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--profile",
        type=Path,
        default=DEFAULT_PROFILE,
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--report-root",
        type=Path,
        required=True,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = load_profile(args.profile)

    report_dir = (
        args.report_root
        / profile["profile_id"]
        / f"count-{args.expected_count}"
    )
    failure_dir = report_dir / "failures"
    csv_path = report_dir / "results.csv"

    report_dir.mkdir(parents=True, exist_ok=True)
    failure_dir.mkdir(parents=True, exist_ok=True)

    images = sorted(args.source.glob("*.jpg"))

    if not images:
        raise SystemExit(f"No JPEG images found in {args.source}")

    results: list[ImageResult] = []

    for index, path in enumerate(images, start=1):
        result, overlay = analyse_image(
            path,
            profile,
            args.expected_count,
        )

        results.append(result)

        marker = "PASS" if result.exact else "FAIL"

        print(
            f"[{index:02d}/{len(images):02d}] {marker} "
            f"{path.name}: predicted={result.predicted_count}, "
            f"regions={result.usable_regions}"
        )

        if not result.exact and overlay is not None:
            cv2.imwrite(
                str(failure_dir / path.name),
                overlay,
            )

    with csv_path.open("w", newline="", encoding="utf-8") as file:
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

    mean_absolute_error = (
        sum(abs(result.error) for result in results) / total
    )

    predictions: dict[int, int] = {}

    for result in results:
        predictions[result.predicted_count] = (
            predictions.get(result.predicted_count, 0) + 1
        )

    print("\n=== DATASET SUMMARY ===")
    print(f"profile: {profile['profile_id']}")
    print(f"expected count: {args.expected_count}")
    print(f"images: {total}")
    print(f"exact counts: {exact_count}")
    print(f"exact-count accuracy: {accuracy:.2f}%")
    print(f"mean absolute count error: {mean_absolute_error:.3f}")
    print(
        "prediction distribution:",
        dict(sorted(predictions.items())),
    )
    print(f"CSV report: {csv_path}")
    print(f"failure overlays: {failure_dir}")


if __name__ == "__main__":
    main()
