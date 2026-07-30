from __future__ import annotations

from collections import deque
from threading import Condition
from time import monotonic

from .contracts import CameraFrame


class FrameQueue:
    """Thread-safe bounded queue optimized for live vision.

    When full, the oldest frame is evicted so consumers receive the freshest
    available frame instead of accumulating latency.
    """

    def __init__(self, max_size: int = 2) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be positive.")
        self._frames: deque[CameraFrame] = deque(maxlen=max_size)
        self._condition = Condition()
        self._closed = False
        self._dropped = 0

    @property
    def max_size(self) -> int:
        return self._frames.maxlen or 0

    @property
    def depth(self) -> int:
        with self._condition:
            return len(self._frames)

    @property
    def dropped_frames(self) -> int:
        with self._condition:
            return self._dropped

    @property
    def closed(self) -> bool:
        with self._condition:
            return self._closed

    def put(self, frame: CameraFrame) -> None:
        with self._condition:
            if self._closed:
                raise RuntimeError("Cannot put frames into a closed queue.")
            if len(self._frames) == self.max_size:
                self._frames.popleft()
                self._dropped += 1
            self._frames.append(frame)
            self._condition.notify()

    def get(self, timeout_s: float | None = None) -> CameraFrame | None:
        with self._condition:
            if timeout_s is not None and timeout_s < 0:
                raise ValueError("timeout_s cannot be negative.")

            deadline = None if timeout_s is None else monotonic() + timeout_s
            while not self._frames and not self._closed:
                remaining = None if deadline is None else deadline - monotonic()
                if remaining is not None and remaining <= 0:
                    return None
                self._condition.wait(remaining)

            if self._frames:
                return self._frames.popleft()
            return None

    def get_latest(self, timeout_s: float | None = None) -> CameraFrame | None:
        with self._condition:
            if timeout_s is not None and timeout_s < 0:
                raise ValueError("timeout_s cannot be negative.")

            deadline = None if timeout_s is None else monotonic() + timeout_s
            while not self._frames and not self._closed:
                remaining = None if deadline is None else deadline - monotonic()
                if remaining is not None and remaining <= 0:
                    return None
                self._condition.wait(remaining)

            if not self._frames:
                return None

            newest = self._frames[-1]
            self._frames.clear()
            return newest

    def clear(self) -> None:
        with self._condition:
            self._frames.clear()

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()
