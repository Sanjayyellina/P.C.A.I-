from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np


class YoloBackend(StrEnum):
    ULTRALYTICS = "ultralytics"
    ONNX_RUNTIME = "onnx_runtime"
    TENSORRT = "tensorrt"


@dataclass(frozen=True, slots=True)
class YoloModelConfig:
    model_path: Path
    backend: YoloBackend = YoloBackend.ULTRALYTICS
    input_width_px: int = 640
    input_height_px: int = 640
    confidence_threshold: float = 0.35
    iou_threshold: float = 0.50
    maximum_detections: int = 500
    device: str = "0"
    use_half_precision: bool = True
    tablet_class_ids: tuple[int, ...] = (0,)

    def __post_init__(self) -> None:
        if self.input_width_px <= 0 or self.input_height_px <= 0:
            raise ValueError("YOLO input dimensions must be positive.")
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0 and 1.")
        if not 0.0 <= self.iou_threshold <= 1.0:
            raise ValueError("iou_threshold must be between 0 and 1.")
        if self.maximum_detections <= 0:
            raise ValueError("maximum_detections must be positive.")
        if not self.tablet_class_ids:
            raise ValueError("tablet_class_ids cannot be empty.")
        if any(class_id < 0 for class_id in self.tablet_class_ids):
            raise ValueError("tablet_class_ids cannot contain negative values.")


@dataclass(frozen=True, slots=True)
class YoloInstance:
    identifier: int
    class_id: int
    class_name: str
    confidence: float
    bounding_box_xyxy: tuple[float, float, float, float]
    centroid_xy: tuple[float, float]
    mask: np.ndarray | None
    area_px2: float | None

    def __post_init__(self) -> None:
        if self.identifier < 0:
            raise ValueError("identifier cannot be negative.")
        if self.class_id < 0:
            raise ValueError("class_id cannot be negative.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1.")
        x1, y1, x2, y2 = self.bounding_box_xyxy
        if x2 < x1 or y2 < y1:
            raise ValueError("bounding_box_xyxy must satisfy x2 >= x1 and y2 >= y1.")
        if self.area_px2 is not None and self.area_px2 < 0:
            raise ValueError("area_px2 cannot be negative.")


@dataclass(frozen=True, slots=True)
class YoloInferenceResult:
    frame_sequence: int
    camera_id: str
    instances: tuple[YoloInstance, ...]
    count: int
    inference_time_ms: float
    preprocessing_time_ms: float
    postprocessing_time_ms: float
    model_name: str
    backend: YoloBackend
    input_shape_hw: tuple[int, int]
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.frame_sequence < 0:
            raise ValueError("frame_sequence cannot be negative.")
        if self.count < 0:
            raise ValueError("count cannot be negative.")
        for field_name in (
            "inference_time_ms",
            "preprocessing_time_ms",
            "postprocessing_time_ms",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} cannot be negative.")
        if self.count != len(self.instances):
            raise ValueError("count must equal the number of returned instances.")
