from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import chess
import numpy as np

from chess_transmission.vision.occupancy import compute_baseline
from chess_transmission.vision.perspective import compute_homography, warp_board


@dataclass
class Calibration:
    """A camera's fixed-rig calibration: the board's corner points (for the
    perspective warp) plus each square's baseline appearance when empty."""

    corners: list[tuple[float, float]]
    baseline: dict[str, float]  # keyed by square name (e.g. "e4") for JSON-friendliness

    def homography(self) -> np.ndarray:
        return compute_homography(self.corners)

    def baseline_by_square(self) -> dict[chess.Square, float]:
        return {chess.parse_square(name): value for name, value in self.baseline.items()}

    def to_json(self, path: Path) -> None:
        path.write_text(json.dumps({"corners": self.corners, "baseline": self.baseline}, indent=2))

    @classmethod
    def from_json(cls, path: Path) -> Calibration:
        data = json.loads(path.read_text())
        return cls(corners=[tuple(c) for c in data["corners"]], baseline=data["baseline"])

    @classmethod
    def capture(
        cls, corners: list[tuple[float, float]], empty_board_frame: np.ndarray
    ) -> Calibration:
        """`empty_board_frame` must show the board with no pieces on it."""
        homography = compute_homography(corners)
        warped = warp_board(empty_board_frame, homography)
        baseline = compute_baseline(warped)
        return cls(
            corners=corners,
            baseline={chess.square_name(square): value for square, value in baseline.items()},
        )
