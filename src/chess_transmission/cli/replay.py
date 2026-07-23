from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from chess_transmission.board_source.calibration import Calibration
from chess_transmission.config import DEFAULT_CALIBRATION_PATH
from chess_transmission.engine.game_session import GameSession
from chess_transmission.engine.types import InferenceStatus
from chess_transmission.vision.occupancy import classify_occupancy
from chess_transmission.vision.perspective import warp_board


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay a directory of recorded frames (PNGs, in filename order) "
        "through the inference pipeline without a live camera -- for building/"
        "debugging fixtures against recorded footage from scripts/dev_capture_frames.py."
    )
    parser.add_argument("frames_dir", type=str)
    parser.add_argument(
        "--calibration", type=str, default=str(DEFAULT_CALIBRATION_PATH)
    )
    args = parser.parse_args(argv)

    calibration = Calibration.from_json(Path(args.calibration))
    session = GameSession()

    for frame_path in sorted(Path(args.frames_dir).glob("*.png")):
        frame = cv2.imread(str(frame_path))
        if frame is None:
            print(f"skipping unreadable frame: {frame_path}")
            continue
        warped = warp_board(frame, calibration.homography())
        occupancy = classify_occupancy(warped, calibration.baseline_by_square())
        result = session.observe(occupancy)
        if result.status == InferenceStatus.MATCHED:
            print(f"{frame_path.name}: {result.san}")
        elif result.status == InferenceStatus.AMBIGUOUS_PROMOTION:
            print(f"{frame_path.name}: {result.san} (promotion assumed queen)")
        elif result.status == InferenceStatus.UNMATCHED:
            print(f"{frame_path.name}: unmatched -- no legal move fits this occupancy")

    print()
    print(session.pgn_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
