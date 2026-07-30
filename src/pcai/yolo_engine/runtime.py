from __future__ import annotations

from time import perf_counter
from typing import Any

import cv2
import numpy as np

from pcai.acquisition import CameraFrame

from .contracts import (
    YoloBackend,
    YoloInferenceResult,
    YoloInstance,
    YoloModelConfig,
)


class YoloRuntimeError(RuntimeError):
    """Raised when the YOLO runtime cannot load or execute a model."""


class YoloRuntime:
    """Run tablet instance detection through a backend-neutral interface."""

    def __init__(self, config: YoloModelConfig) -> None:
        self._config = config
        self._model: Any | None = None
        self._model_name = config.model_path.name

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        if self.loaded:
            return
        if not self._config.model_path.exists():
            raise YoloRuntimeError(
                f"YOLO model does not exist: {self._config.model_path}"
            )

        if self._config.backend in {
            YoloBackend.ULTRALYTICS,
            YoloBackend.TENSORRT,
        }:
            self._model = self._load_ultralytics_model()
            return

        if self._config.backend is YoloBackend.ONNX_RUNTIME:
            raise YoloRuntimeError(
                "Direct ONNX Runtime execution is not implemented in V1. "
                "Use the Ultralytics backend with an ONNX model or add the "
                "dedicated ONNX adapter."
            )

        raise YoloRuntimeError(f"Unsupported YOLO backend: {self._config.backend}")

    def infer(self, frame: CameraFrame) -> YoloInferenceResult:
        if not self.loaded:
            self.load()
        assert self._model is not None

        image = self._validate_image(frame.image_bgr)
        preprocessing_started = perf_counter()
        input_image = np.ascontiguousarray(image)
        preprocessing_ms = (perf_counter() - preprocessing_started) * 1000.0

        inference_started = perf_counter()
        try:
            results = self._model.predict(
                source=input_image,
                imgsz=(
                    self._config.input_height_px,
                    self._config.input_width_px,
                ),
                conf=self._config.confidence_threshold,
                iou=self._config.iou_threshold,
                max_det=self._config.maximum_detections,
                device=self._config.device,
                half=self._config.use_half_precision,
                classes=list(self._config.tablet_class_ids),
                verbose=False,
            )
        except Exception as error:  # backend exceptions vary by model format
            raise YoloRuntimeError(f"YOLO inference failed: {error}") from error
        inference_ms = (perf_counter() - inference_started) * 1000.0

        postprocessing_started = perf_counter()
        instances, reasons = self._parse_results(results, image.shape[:2])
        postprocessing_ms = (perf_counter() - postprocessing_started) * 1000.0

        return YoloInferenceResult(
            frame_sequence=frame.metadata.sequence,
            camera_id=frame.metadata.camera_id,
            instances=instances,
            count=len(instances),
            inference_time_ms=round(inference_ms, 3),
            preprocessing_time_ms=round(preprocessing_ms, 3),
            postprocessing_time_ms=round(postprocessing_ms, 3),
            model_name=self._model_name,
            backend=self._config.backend,
            input_shape_hw=(
                self._config.input_height_px,
                self._config.input_width_px,
            ),
            reason_codes=reasons,
        )

    def warmup(self, width_px: int = 1024, height_px: int = 768) -> None:
        """Initialize backend kernels using a synthetic frame."""
        if width_px <= 0 or height_px <= 0:
            raise ValueError("Warmup dimensions must be positive.")
        if not self.loaded:
            self.load()
        assert self._model is not None

        image = np.zeros((height_px, width_px, 3), dtype=np.uint8)
        try:
            self._model.predict(
                source=image,
                imgsz=(
                    self._config.input_height_px,
                    self._config.input_width_px,
                ),
                conf=self._config.confidence_threshold,
                iou=self._config.iou_threshold,
                max_det=self._config.maximum_detections,
                device=self._config.device,
                half=self._config.use_half_precision,
                classes=list(self._config.tablet_class_ids),
                verbose=False,
            )
        except Exception as error:
            raise YoloRuntimeError(f"YOLO warmup failed: {error}") from error

    def close(self) -> None:
        self._model = None

    def _load_ultralytics_model(self) -> Any:
        try:
            from ultralytics import YOLO
        except ImportError as error:
            raise YoloRuntimeError(
                "Ultralytics is not installed. Install it in the P.C.A.I. "
                "environment before loading this backend."
            ) from error

        try:
            model = YOLO(str(self._config.model_path))
        except Exception as error:
            raise YoloRuntimeError(f"Could not load YOLO model: {error}") from error

        model_names = getattr(model, "names", None)
        if isinstance(model_names, dict) and model_names:
            self._model_name = self._config.model_path.name
        return model

    def _parse_results(
        self,
        results: Any,
        image_shape_hw: tuple[int, int],
    ) -> tuple[tuple[YoloInstance, ...], tuple[str, ...]]:
        if results is None or len(results) == 0:
            return (), ("YOLO_RESULT_EMPTY",)

        result = results[0]
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return (), ()

        names = getattr(result, "names", {}) or {}
        masks = getattr(result, "masks", None)
        mask_data = getattr(masks, "data", None) if masks is not None else None

        xyxy = self._to_numpy(boxes.xyxy)
        confidences = self._to_numpy(boxes.conf).reshape(-1)
        class_ids = self._to_numpy(boxes.cls).reshape(-1).astype(np.int64)

        instances: list[YoloInstance] = []
        reasons: list[str] = []
        image_height, image_width = image_shape_hw

        for index, (box, confidence, class_id) in enumerate(
            zip(xyxy, confidences, class_ids, strict=True)
        ):
            class_id_int = int(class_id)
            if class_id_int not in self._config.tablet_class_ids:
                continue

            x1, y1, x2, y2 = [float(value) for value in box]
            x1 = max(0.0, min(float(image_width - 1), x1))
            y1 = max(0.0, min(float(image_height - 1), y1))
            x2 = max(x1, min(float(image_width), x2))
            y2 = max(y1, min(float(image_height), y2))

            mask: np.ndarray | None = None
            area: float | None = None
            if mask_data is not None and index < len(mask_data):
                raw_mask = self._to_numpy(mask_data[index])
                if raw_mask.ndim == 3:
                    raw_mask = raw_mask.squeeze()
                resized = cv2.resize(
                    raw_mask.astype(np.float32),
                    (image_width, image_height),
                    interpolation=cv2.INTER_LINEAR,
                )
                mask = np.where(resized >= 0.5, 255, 0).astype(np.uint8)
                area = float(np.count_nonzero(mask))
            else:
                reasons.append("YOLO_MASKS_UNAVAILABLE")

            class_name = str(names.get(class_id_int, class_id_int))
            instances.append(
                YoloInstance(
                    identifier=len(instances),
                    class_id=class_id_int,
                    class_name=class_name,
                    confidence=float(confidence),
                    bounding_box_xyxy=(x1, y1, x2, y2),
                    centroid_xy=((x1 + x2) / 2.0, (y1 + y2) / 2.0),
                    mask=mask,
                    area_px2=area,
                )
            )

        return tuple(instances), tuple(dict.fromkeys(reasons))

    @staticmethod
    def _to_numpy(value: Any) -> np.ndarray:
        if hasattr(value, "detach"):
            value = value.detach()
        if hasattr(value, "cpu"):
            value = value.cpu()
        if hasattr(value, "numpy"):
            value = value.numpy()
        return np.asarray(value)

    @staticmethod
    def _validate_image(image_bgr: np.ndarray) -> np.ndarray:
        if not isinstance(image_bgr, np.ndarray):
            raise TypeError("image_bgr must be a numpy array.")
        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise ValueError("image_bgr must have shape (height, width, 3).")
        if image_bgr.size == 0:
            raise ValueError("image_bgr cannot be empty.")
        if image_bgr.dtype != np.uint8:
            image_bgr = cv2.normalize(
                image_bgr,
                None,
                0,
                255,
                cv2.NORM_MINMAX,
            ).astype(np.uint8)
        return image_bgr
