from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True, slots=True)
class WatershedSplitConfig:
    distance_threshold_ratio: float = 0.42
    minimum_region_area_px2: int = 80
    maximum_regions: int = 12
    opening_kernel_size: int = 3

    def __post_init__(self) -> None:
        if not 0.0 < self.distance_threshold_ratio < 1.0:
            raise ValueError("distance_threshold_ratio must be between 0 and 1.")
        if self.minimum_region_area_px2 <= 0:
            raise ValueError("minimum_region_area_px2 must be positive.")
        if self.maximum_regions <= 0:
            raise ValueError("maximum_regions must be positive.")
        if self.opening_kernel_size <= 0 or self.opening_kernel_size % 2 == 0:
            raise ValueError("opening_kernel_size must be a positive odd integer.")


@dataclass(frozen=True, slots=True)
class WatershedRegion:
    identifier: int
    mask: np.ndarray
    area_px2: int
    centroid_xy: tuple[float, float]
    bounding_box_xywh: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class WatershedSplitResult:
    split_applied: bool
    regions: tuple[WatershedRegion, ...]
    marker_count: int
    reason: str | None


class WatershedTabletSplitter:
    """Split a connected candidate mask into tablet-sized regions."""

    def __init__(self, config: WatershedSplitConfig | None = None) -> None:
        self._config = config or WatershedSplitConfig()

    def split(
        self,
        image_bgr: np.ndarray,
        candidate_mask: np.ndarray,
    ) -> WatershedSplitResult:
        image = self._validate_image(image_bgr)
        mask = self._validate_mask(candidate_mask, image.shape[:2])

        if int(np.count_nonzero(mask)) < self._config.minimum_region_area_px2 * 2:
            return WatershedSplitResult(
                split_applied=False,
                regions=(),
                marker_count=0,
                reason="CANDIDATE_TOO_SMALL_FOR_SPLIT",
            )

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self._config.opening_kernel_size, self._config.opening_kernel_size),
        )
        opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        distance = cv2.distanceTransform(opened, cv2.DIST_L2, 5)
        peak = float(distance.max())
        if peak <= 0:
            return WatershedSplitResult(False, (), 0, "DISTANCE_TRANSFORM_EMPTY")

        _, sure_foreground = cv2.threshold(
            distance,
            self._config.distance_threshold_ratio * peak,
            255,
            cv2.THRESH_BINARY,
        )
        sure_foreground = sure_foreground.astype(np.uint8)
        sure_background = cv2.dilate(opened, kernel, iterations=2)
        unknown = cv2.subtract(sure_background, sure_foreground)

        marker_count, markers = cv2.connectedComponents(sure_foreground)
        object_markers = marker_count - 1
        if object_markers < 2:
            return WatershedSplitResult(
                split_applied=False,
                regions=(),
                marker_count=object_markers,
                reason="INSUFFICIENT_WATERSHED_MARKERS",
            )
        if object_markers > self._config.maximum_regions:
            return WatershedSplitResult(
                split_applied=False,
                regions=(),
                marker_count=object_markers,
                reason="TOO_MANY_WATERSHED_MARKERS",
            )

        markers = markers + 1
        markers[unknown > 0] = 0
        working = image.copy()
        markers = cv2.watershed(working, markers.astype(np.int32))

        regions: list[WatershedRegion] = []
        for marker_id in sorted(int(value) for value in np.unique(markers) if value > 1):
            region_mask = np.where(markers == marker_id, 255, 0).astype(np.uint8)
            region_mask = cv2.bitwise_and(region_mask, mask)
            area = int(np.count_nonzero(region_mask))
            if area < self._config.minimum_region_area_px2:
                continue

            points = cv2.findNonZero(region_mask)
            if points is None:
                continue
            x, y, width, height = cv2.boundingRect(points)
            moments = cv2.moments(region_mask, binaryImage=True)
            if moments["m00"] <= 0:
                continue
            centroid = (
                float(moments["m10"] / moments["m00"]),
                float(moments["m01"] / moments["m00"]),
            )
            regions.append(
                WatershedRegion(
                    identifier=len(regions),
                    mask=region_mask,
                    area_px2=area,
                    centroid_xy=centroid,
                    bounding_box_xywh=(x, y, width, height),
                )
            )

        if len(regions) < 2:
            return WatershedSplitResult(
                split_applied=False,
                regions=tuple(regions),
                marker_count=object_markers,
                reason="VALID_SPLIT_REGIONS_NOT_FOUND",
            )

        return WatershedSplitResult(
            split_applied=True,
            regions=tuple(regions),
            marker_count=object_markers,
            reason=None,
        )

    @staticmethod
    def _validate_image(image_bgr: np.ndarray) -> np.ndarray:
        if not isinstance(image_bgr, np.ndarray):
            raise TypeError("image_bgr must be a numpy array.")
        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3 or image_bgr.size == 0:
            raise ValueError("image_bgr must be a non-empty BGR image.")
        if image_bgr.dtype != np.uint8:
            image_bgr = cv2.normalize(
                image_bgr,
                None,
                0,
                255,
                cv2.NORM_MINMAX,
            ).astype(np.uint8)
        return image_bgr

    @staticmethod
    def _validate_mask(mask: np.ndarray, expected_shape: tuple[int, int]) -> np.ndarray:
        if not isinstance(mask, np.ndarray):
            raise TypeError("candidate_mask must be a numpy array.")
        if mask.ndim != 2 or mask.shape != expected_shape:
            raise ValueError("candidate_mask must be 2D and match image dimensions.")
        if mask.size == 0:
            raise ValueError("candidate_mask cannot be empty.")
        return np.where(mask > 0, 255, 0).astype(np.uint8)
