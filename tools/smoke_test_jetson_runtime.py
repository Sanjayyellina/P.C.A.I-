from __future__ import annotations

from datetime import UTC, datetime

import numpy as np

from pcai.acquisition.contracts import CameraFrame, FrameMetadata
from pcai.frame_quality import TemporalFrameStability
from pcai.tracking.contracts import TrackObservation
from pcai.tracking.object_tracker import ObjectTrackerConfig, TemporalObjectTracker
from pcai.tracking.stable_counter import StableCounter