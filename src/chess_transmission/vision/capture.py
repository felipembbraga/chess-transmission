from __future__ import annotations

import time
from collections.abc import Iterator

import cv2
import numpy as np


class CameraCapture:
    """Thin wrapper over cv2.VideoCapture. Requires a real camera to exercise --
    not covered by the automated unit-test suite (see tests/fixtures/vision for the
    synthetic-image tests that cover the occupancy-classification algorithm instead)."""

    def __init__(self, camera_index: int = 0):
        self._camera_index = camera_index
        self._cap: cv2.VideoCapture | None = None

    def __enter__(self) -> CameraCapture:
        self._cap = cv2.VideoCapture(self._camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"could not open camera index {self._camera_index}")
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._cap is not None:
            self._cap.release()

    def read(self) -> np.ndarray:
        assert self._cap is not None, "CameraCapture must be used as a context manager"
        ok, frame = self._cap.read()
        if not ok:
            raise RuntimeError("failed to read frame from camera")
        return frame

    def frames(self, poll_fps: float = 8.0) -> Iterator[np.ndarray]:
        delay = 1.0 / poll_fps
        while True:
            yield self.read()
            time.sleep(delay)
