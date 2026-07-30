from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from pcai.acquisition import CameraFrame, FrameMetadata, FrameQueue


def make_frame(sequence: int) -> CameraFrame:
    image = np.zeros((8, 12, 3), dtype=np.uint8)
    return CameraFrame(
        image_bgr=image,
        metadata=FrameMetadata(
            sequence=sequence,
            captured_at_utc=datetime.now(timezone.utc),
            monotonic_ns=sequence,
            camera_id="test-camera",
            width_px=12,
            height_px=8,
        ),
    )


def test_queue_evicts_oldest_frame_when_full() -> None:
    queue = FrameQueue(max_size=2)

    queue.put(make_frame(1))
    queue.put(make_frame(2))
    queue.put(make_frame(3))

    assert queue.depth == 2
    assert queue.dropped_frames == 1
    assert queue.get(timeout_s=0).metadata.sequence == 2
    assert queue.get(timeout_s=0).metadata.sequence == 3


def test_get_latest_discards_older_buffered_frames() -> None:
    queue = FrameQueue(max_size=4)
    queue.put(make_frame(1))
    queue.put(make_frame(2))
    queue.put(make_frame(3))

    latest = queue.get_latest(timeout_s=0)

    assert latest is not None
    assert latest.metadata.sequence == 3
    assert queue.depth == 0


def test_get_times_out_when_no_frame_arrives() -> None:
    queue = FrameQueue(max_size=1)

    assert queue.get(timeout_s=0.001) is None


def test_close_unblocks_empty_queue_and_rejects_new_frames() -> None:
    queue = FrameQueue(max_size=1)
    queue.close()

    assert queue.closed is True
    assert queue.get(timeout_s=0) is None

    try:
        queue.put(make_frame(1))
    except RuntimeError as error:
        assert "closed queue" in str(error)
    else:
        raise AssertionError("Expected RuntimeError when putting into closed queue.")
