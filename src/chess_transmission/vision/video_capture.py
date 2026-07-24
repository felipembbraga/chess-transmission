from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np

DEFAULT_TARGET_FPS = 8.0


class VideoFileCapture:
    """Reads frames from a recorded video file.

    Unlike CameraCapture, reaching the end of the file is normal termination
    (not an error), and frames are read as fast as they decode -- no real-time
    polling delay.
    """

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._cap: cv2.VideoCapture | None = None
        self.frames_read = 0

    def __enter__(self) -> VideoFileCapture:
        self._cap = cv2.VideoCapture(str(self._path))
        if not self._cap.isOpened():
            raise RuntimeError(f"could not open video file {self._path}")
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._cap is not None:
            self._cap.release()

    @property
    def total_frames(self) -> int:
        assert (
            self._cap is not None
        ), "VideoFileCapture must be used as a context manager"
        return int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

    @property
    def source_fps(self) -> float:
        assert (
            self._cap is not None
        ), "VideoFileCapture must be used as a context manager"
        return float(self._cap.get(cv2.CAP_PROP_FPS)) or DEFAULT_TARGET_FPS

    def read(self) -> np.ndarray | None:
        """Returns the next decoded frame, or None at end-of-file."""
        assert (
            self._cap is not None
        ), "VideoFileCapture must be used as a context manager"
        ok, frame = self._cap.read()
        if not ok:
            return None
        self.frames_read += 1
        return frame

    def frames(self, target_fps: float = DEFAULT_TARGET_FPS) -> Iterator[np.ndarray]:
        """Yields frames sampled at roughly `target_fps`, derived from the
        video's own reported FPS -- so recognition sees roughly the same
        effective rate a live camera would poll at (see research.md #3)."""
        stride = max(1, round(self.source_fps / target_fps))
        index = 0
        while True:
            frame = self.read()
            if frame is None:
                return
            if index % stride == 0:
                yield frame
            index += 1
