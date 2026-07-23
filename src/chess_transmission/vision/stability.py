from __future__ import annotations

from collections import deque

import numpy as np

DEFAULT_WINDOW_SIZE = 8
DEFAULT_DIFF_THRESHOLD = 2.0


class StabilityDetector:
    """Declares a frame stream 'at rest' once frame-to-frame difference stays below
    a threshold across a full rolling window -- this is what filters out frames
    where a hand is still moving a piece, without needing to understand the hand."""

    def __init__(
        self,
        window_size: int = DEFAULT_WINDOW_SIZE,
        threshold: float = DEFAULT_DIFF_THRESHOLD,
    ):
        self._window_size = window_size
        self._threshold = threshold
        self._frames: deque[np.ndarray] = deque(maxlen=window_size)

    def push(self, frame: np.ndarray) -> bool:
        self._frames.append(frame)
        if len(self._frames) < self._window_size:
            return False
        frames = list(self._frames)
        return all(
            _mean_abs_diff(a, b) < self._threshold for a, b in zip(frames, frames[1:])
        )

    def reset(self) -> None:
        self._frames.clear()


def _mean_abs_diff(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a.astype(np.int16) - b.astype(np.int16))))
