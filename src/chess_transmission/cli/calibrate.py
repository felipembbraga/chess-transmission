from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

from chess_transmission.board_source.calibration import Calibration
from chess_transmission.config import DEFAULT_CALIBRATION_PATH
from chess_transmission.vision.capture import CameraCapture
from chess_transmission.vision.video_capture import VideoFileCapture

CORNER_ORDER = ["a8", "h8", "h1", "a1"]
WINDOW_NAME = "chess-transmission calibrate"


def _collect_corners(camera_index: int) -> tuple[list[tuple[float, float]], np.ndarray]:
    corners: list[tuple[float, float]] = []

    def on_click(event: int, x: int, y: int, flags: int, param: object) -> None:
        if event == cv2.EVENT_LBUTTONDOWN and len(corners) < 4:
            corners.append((float(x), float(y)))

    with CameraCapture(camera_index) as cam:
        cv2.namedWindow(WINDOW_NAME)
        cv2.setMouseCallback(WINDOW_NAME, on_click)
        while len(corners) < 4:
            frame = cam.read()
            preview = frame.copy()
            for point in corners:
                cv2.circle(preview, (int(point[0]), int(point[1])), 6, (0, 255, 0), -1)
            label = (
                f"click {CORNER_ORDER[len(corners)]} ({len(corners)}/4) -- q to abort"
            )
            cv2.putText(
                preview, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
            )
            cv2.imshow(WINDOW_NAME, preview)
            if cv2.waitKey(20) & 0xFF == ord("q"):
                raise SystemExit("calibration aborted")
        print("board must now be empty -- press any key once cleared")
        cv2.waitKey(0)
        empty_frame = cam.read()
    cv2.destroyWindow(WINDOW_NAME)
    return corners, empty_frame


def _collect_corners_from_frame(frame: np.ndarray) -> list[tuple[float, float]]:
    corners: list[tuple[float, float]] = []

    def on_click(event: int, x: int, y: int, flags: int, param: object) -> None:
        if event == cv2.EVENT_LBUTTONDOWN and len(corners) < 4:
            corners.append((float(x), float(y)))

    cv2.namedWindow(WINDOW_NAME)
    cv2.setMouseCallback(WINDOW_NAME, on_click)
    while len(corners) < 4:
        preview = frame.copy()
        for point in corners:
            cv2.circle(preview, (int(point[0]), int(point[1])), 6, (0, 255, 0), -1)
        label = f"click {CORNER_ORDER[len(corners)]} ({len(corners)}/4) -- q to abort"
        cv2.putText(
            preview, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
        )
        cv2.imshow(WINDOW_NAME, preview)
        if cv2.waitKey(20) & 0xFF == ord("q"):
            raise SystemExit("calibration aborted")
    cv2.destroyWindow(WINDOW_NAME)
    return corners


def _collect_from_video(
    video_path: str,
) -> tuple[list[tuple[float, float]], np.ndarray]:
    """Uses the video's first frame for both corner-clicking and the empty-board
    baseline -- the recording must therefore start on the genuinely empty board."""
    with VideoFileCapture(video_path) as cap:
        frame = cap.read()
    if frame is None:
        raise RuntimeError(f"video file has no frames: {video_path}")
    print(f"click the board's 4 corners in order: {', '.join(CORNER_ORDER)}")
    corners = _collect_corners_from_frame(frame)
    return corners, frame


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Calibrate the camera against the physical board."
    )
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument(
        "--from-video",
        type=str,
        default=None,
        help="use a recorded video's first frame (must show the empty board) "
        "instead of a live camera",
    )
    parser.add_argument("--out", type=str, default=str(DEFAULT_CALIBRATION_PATH))
    args = parser.parse_args(argv)

    if args.from_video:
        corners, empty_frame = _collect_from_video(args.from_video)
    else:
        print(f"click the board's 4 corners in order: {', '.join(CORNER_ORDER)}")
        corners, empty_frame = _collect_corners(args.camera_index)

    calibration = Calibration.capture(corners, empty_frame)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    calibration.to_json(out_path)
    print(f"calibration saved to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
