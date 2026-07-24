from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import numpy as np

from chess_transmission.board_source.base import BoardSnapshot, BoardStateSource
from chess_transmission.board_source.calibration import Calibration
from chess_transmission.vision.occupancy import (
    DEFAULT_OCCUPANCY_THRESHOLD,
    classify_occupancy,
)
from chess_transmission.vision.perspective import warp_board
from chess_transmission.vision.stability import StabilityDetector
from chess_transmission.vision.video_capture import DEFAULT_TARGET_FPS, VideoFileCapture


class VideoFileBoardStateSource(BoardStateSource):
    """Reads board occupancy from a recorded video file, using a pre-computed
    Calibration. Unlike CameraBoardStateSource, `stream()` terminates once the
    video ends rather than running forever.

    `frames_processed`/`total_frames` are cached on the instance (rather than
    delegated live to the underlying capture) so they stay valid to read even
    after the video has finished and the capture has been released -- e.g. to
    print a final "100% processed" line.
    """

    def __init__(
        self,
        video_path: str | Path,
        calibration: Calibration,
        occupancy_threshold: float = DEFAULT_OCCUPANCY_THRESHOLD,
        target_fps: float = DEFAULT_TARGET_FPS,
    ):
        self._video_path = video_path
        self._calibration = calibration
        self._occupancy_threshold = occupancy_threshold
        self._target_fps = target_fps
        self._frames_processed = 0
        self._total_frames = 0

    def calibrate(self) -> None:
        raise NotImplementedError(
            "video extraction reuses an existing Calibration; construct "
            "VideoFileBoardStateSource with one instead"
        )

    def capture_once(self) -> BoardSnapshot:
        with VideoFileCapture(self._video_path) as cap:
            self._total_frames = cap.total_frames
            frame = cap.read()
            self._frames_processed = cap.frames_read
            if frame is None:
                raise RuntimeError(f"video file has no frames: {self._video_path}")
            return self._snapshot_from_frame(frame)

    def stream(self) -> Iterator[BoardSnapshot]:
        detector = StabilityDetector()
        with VideoFileCapture(self._video_path) as cap:
            self._total_frames = cap.total_frames
            for frame in cap.frames(target_fps=self._target_fps):
                self._frames_processed = cap.frames_read
                if detector.push(frame):
                    yield self._snapshot_from_frame(frame)
                    detector.reset()

    @property
    def frames_processed(self) -> int:
        return self._frames_processed

    @property
    def total_frames(self) -> int:
        return self._total_frames

    def _snapshot_from_frame(self, frame: np.ndarray) -> BoardSnapshot:
        warped = warp_board(frame, self._calibration.homography())
        occupancy = classify_occupancy(
            warped, self._calibration.baseline_by_square(), self._occupancy_threshold
        )
        return BoardSnapshot(
            occupancy=occupancy, timestamp=float(self._frames_processed)
        )
