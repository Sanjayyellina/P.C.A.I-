from __future__ import annotations

from dataclasses import dataclass, replace
from time import perf_counter

from pcai.acquisition import AcquisitionSession, CameraFrame
from pcai.classical_estimator.contracts import ClassicalCountEstimate
from pcai.classical_estimator.estimator import ClassicalTabletEstimator
from pcai.frame_quality.gate import FrameGateResult, LiveFrameQualityGate
from pcai.fusion.contracts import FusedCountEstimate, FusionDecision
from pcai.fusion.fusion_engine import EvidenceFusionEngine
from pcai.segmentation.adaptive_threshold import AdaptiveTabletSegmenter
from pcai.segmentation.candidate_extraction import CandidateExtractor
from pcai.segmentation.contracts import CandidateObservation
from pcai.segmentation.feature_extraction import CandidateFeatureExtractor
from pcai.segmentation.illumination import IlluminationNormalizer
from pcai.segmentation.touching_tablets import TouchingTabletAnalyzer
from pcai.segmentation.watershed_split import WatershedTabletSplitter
from pcai.tracking.contracts import StableCountResult, TrackObservation
from pcai.tracking.object_tracker import TemporalObjectTracker
from pcai.tracking.stable_counter import StableCounter
from pcai.tracking.temporal_tracker import TemporalSceneMetrics, TemporalSceneTracker
from pcai.tray_geometry.workspace import TrayWorkspaceBuilder, TrayWorkspaceResult
from pcai.yolo_engine.contracts import YoloInferenceResult
from pcai.yolo_engine.runtime import YoloRuntime


@dataclass(frozen=True, slots=True)
class LivePipelineResult:
    frame_sequence: int
    ready: bool
    stable_count: StableCountResult | None
    frame_gate: FrameGateResult
    tray_workspace: TrayWorkspaceResult | None
    classical_estimate: ClassicalCountEstimate | None
    yolo_result: YoloInferenceResult | None
    fused_estimate: FusedCountEstimate | None
    temporal_metrics: TemporalSceneMetrics | None
    processing_time_ms: float
    reason_codes: tuple[str, ...]


class LiveTabletCountingPipeline:
    """Execute the complete P.C.A.I. live counting path for each camera frame."""

    def __init__(
        self,
        *,
        yolo_runtime: YoloRuntime,
        touching_analyzer: TouchingTabletAnalyzer,
        frame_gate: LiveFrameQualityGate | None = None,
        tray_workspace: TrayWorkspaceBuilder | None = None,
        illumination: IlluminationNormalizer | None = None,
        segmenter: AdaptiveTabletSegmenter | None = None,
        candidate_extractor: CandidateExtractor | None = None,
        feature_extractor: CandidateFeatureExtractor | None = None,
        watershed_splitter: WatershedTabletSplitter | None = None,
        classical_estimator: ClassicalTabletEstimator | None = None,
        fusion_engine: EvidenceFusionEngine | None = None,
        object_tracker: TemporalObjectTracker | None = None,
        temporal_tracker: TemporalSceneTracker | None = None,
        stable_counter: StableCounter | None = None,
    ) -> None:
        self._frame_gate = frame_gate or LiveFrameQualityGate()
        self._tray_workspace = tray_workspace or TrayWorkspaceBuilder()
        self._illumination = illumination or IlluminationNormalizer()
        self._segmenter = segmenter or AdaptiveTabletSegmenter()
        self._candidate_extractor = candidate_extractor or CandidateExtractor()
        self._feature_extractor = feature_extractor or CandidateFeatureExtractor()
        self._touching_analyzer = touching_analyzer
        self._watershed_splitter = watershed_splitter or WatershedTabletSplitter()
        self._classical_estimator = classical_estimator or ClassicalTabletEstimator()
        self._yolo_runtime = yolo_runtime
        self._fusion_engine = fusion_engine or EvidenceFusionEngine()
        self._object_tracker = object_tracker or TemporalObjectTracker()
        self._temporal_tracker = temporal_tracker or TemporalSceneTracker()
        self._stable_counter = stable_counter or StableCounter()

    def process(self, frame: CameraFrame) -> LivePipelineResult:
        started = perf_counter()
        gate = self._frame_gate.evaluate(frame)
        if not gate.ready_for_counting:
            return self._early_result(frame, gate, None, started, gate.reason_codes)

        workspace = self._tray_workspace.build(frame.image_bgr)
        if not workspace.ready or workspace.normalized_frame is None:
            return self._early_result(
                frame,
                gate,
                workspace,
                started,
                (workspace.reason or "TRAY_NOT_READY",),
            )

        normalized_image = workspace.normalized_frame.image_bgr
        illumination = self._illumination.normalize(normalized_image)
        threshold = self._segmenter.segment(illumination.normalized)
        candidates = self._candidate_extractor.extract(
            threshold.binary_mask,
            illumination.grayscale,
        )

        hypotheses = []
        for candidate in candidates:
            features = self._feature_extractor.extract(
                candidate,
                illumination.grayscale,
            )
            touching = self._touching_analyzer.assess(features)
            watershed = (
                self._watershed_splitter.split(normalized_image, candidate.mask)
                if touching.requires_split
                else None
            )
            hypotheses.append(
                self._classical_estimator.estimate_candidate(
                    features,
                    touching,
                    watershed,
                )
            )

        classical = self._classical_estimator.estimate_total(tuple(hypotheses))
        normalized_frame = self._normalized_camera_frame(frame, normalized_image)
        yolo = self._yolo_runtime.infer(normalized_frame)
        fused = self._fusion_engine.fuse(candidates, classical, yolo)

        track_observations = self._to_track_observations(
            fused,
            candidates,
            yolo,
        )
        tracking = self._object_tracker.update(
            frame.metadata.sequence,
            track_observations,
        )
        temporal = self._temporal_tracker.update(tracking)
        stable = self._stable_counter.update(temporal)

        reasons = list(fused.reason_codes)
        reasons.extend(temporal.reason_codes)
        reasons.extend(stable.reason_codes)

        return LivePipelineResult(
            frame_sequence=frame.metadata.sequence,
            ready=fused.decision is FusionDecision.ACCEPT and temporal.scene_stable,
            stable_count=stable,
            frame_gate=gate,
            tray_workspace=workspace,
            classical_estimate=classical,
            yolo_result=yolo,
            fused_estimate=fused,
            temporal_metrics=temporal,
            processing_time_ms=round((perf_counter() - started) * 1000.0, 3),
            reason_codes=tuple(dict.fromkeys(reasons)),
        )

    def run_forever(
        self,
        session: AcquisitionSession,
        on_result: callable | None = None,
    ) -> None:
        """Continuously process the newest available frame until interrupted."""
        if not session.running:
            session.start()
        try:
            while True:
                frame = session.read_latest(timeout_s=1.0)
                if frame is None:
                    continue
                result = self.process(frame)
                if on_result is not None:
                    on_result(result)
        finally:
            session.stop()

    def reset(self) -> None:
        self._frame_gate.reset()
        self._object_tracker.reset()
        self._temporal_tracker.reset()

    @staticmethod
    def _normalized_camera_frame(
        source: CameraFrame,
        image_bgr,
    ) -> CameraFrame:
        height, width = image_bgr.shape[:2]
        metadata = replace(
            source.metadata,
            width_px=width,
            height_px=height,
        )
        return CameraFrame(image_bgr=image_bgr, metadata=metadata)

    @staticmethod
    def _to_track_observations(
        fused: FusedCountEstimate,
        classical_candidates: tuple[CandidateObservation, ...],
        yolo: YoloInferenceResult,
    ) -> tuple[TrackObservation, ...]:
        classical_by_id = {
            candidate.identifier: candidate for candidate in classical_candidates
        }
        yolo_by_id = {instance.identifier: instance for instance in yolo.instances}
        observations: list[TrackObservation] = []

        for candidate in fused.candidates:
            if candidate.decision is FusionDecision.REJECT:
                continue

            box: tuple[float, float, float, float] | None = None
            centroid: tuple[float, float] | None = None

            if candidate.yolo_instance_id is not None:
                instance = yolo_by_id.get(candidate.yolo_instance_id)
                if instance is not None:
                    box = instance.bounding_box_xyxy
                    centroid = instance.centroid_xy

            if box is None and candidate.classical_candidate_id is not None:
                classical = classical_by_id.get(candidate.classical_candidate_id)
                if classical is not None:
                    x, y, width, height = classical.bounding_box_xywh
                    box = (float(x), float(y), float(x + width), float(y + height))
                    centroid = classical.centroid_xy

            if box is None or centroid is None:
                continue

            observations.append(
                TrackObservation(
                    frame_sequence=fused.frame_sequence,
                    fused_candidate_id=candidate.identifier,
                    centroid_xy=centroid,
                    bounding_box_xyxy=box,
                    estimated_count=candidate.estimated_count,
                    confidence=candidate.confidence,
                )
            )

        return tuple(observations)

    @staticmethod
    def _early_result(
        frame: CameraFrame,
        gate: FrameGateResult,
        workspace: TrayWorkspaceResult | None,
        started: float,
        reasons: tuple[str, ...],
    ) -> LivePipelineResult:
        return LivePipelineResult(
            frame_sequence=frame.metadata.sequence,
            ready=False,
            stable_count=None,
            frame_gate=gate,
            tray_workspace=workspace,
            classical_estimate=None,
            yolo_result=None,
            fused_estimate=None,
            temporal_metrics=None,
            processing_time_ms=round((perf_counter() - started) * 1000.0, 3),
            reason_codes=tuple(dict.fromkeys(reasons)),
        )
