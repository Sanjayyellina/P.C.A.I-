from __future__ import annotations

import argparse
import importlib
import platform
import sys
from dataclasses import dataclass

from pcai.tracking.contracts import (
    CountPublicationDecision,
    TrackObservation,
)
from pcai.tracking.object_tracker import (
    ObjectTrackerConfig,
    TemporalObjectTracker,
)