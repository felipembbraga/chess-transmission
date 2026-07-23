from __future__ import annotations

import time
from collections.abc import Iterator

import numpy as np

from chess_transmission.board_source.base import BoardSnapshot, BoardStateSource
from chess_transmission.board_source.calibration import Calibration
from chess_transmission.vision.capture import CameraCapture
from chess_transmission.vision.occupancy import DEFAULT_OCCUPANCY_THRESHOLD, classify_occupancy
from chess_transmission.vision.perspective import warp_board
from chess_transmission.vision.stability import StabilityDetector


class CameraBoardStateSource(BoardStateSource):
    """Reads board occupancy from an overhead camera, using a pre-computed
    Calibration. Run `chess-transmission calibrate` first to produce one --
    interactive calibration itself lives in cli/calibrate.py, not here."""

    def __init__(
        self,
        camera_index: int,
        calibration: Calibration,
        occupancy_threshold: float = DEFAULT_OCCUPANCY_THRESHOLD,
    ):
        self._camera_index = camera_index
        self._calibration = calibration
        self._occupancy_threshold = occupancy_threshold

    def calibrate(self) -> None:
        raise NotImplementedError(
            "interactive calibration is driven by cli.calibrate; construct "
            "CameraBoardStateSource with an existing Calibration instead"
        )

    def capture_once(self) -> BoardSnapshot:
        with CameraCapture(self._camera_index) as cam:
            frame = cam.read()
        return self._snapshot_from_frame(frame)

    def stream(self) -> Iterator[BoardSnapshot]:
        detector = StabilityDetector()
        with CameraCapture(self._camera_index) as cam:
            for frame in cam.frames():
                if detector.push(frame):
                    yield self._snapshot_from_frame(frame)
                    detector.reset()

    def _snapshot_from_frame(self, frame: np.ndarray) -> BoardSnapshot:
        warped = warp_board(frame, self._calibration.homography())
        occupancy = classify_occupancy(
            warped, self._calibration.baseline_by_square(), self._occupancy_threshold
        )
        return BoardSnapshot(occupancy=occupancy, timestamp=time.time())
