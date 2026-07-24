from pathlib import Path

import cv2
import numpy as np


def write_synthetic_video(path: Path, frames: list[np.ndarray], fps: float) -> None:
    """Write a small synthetic video (lossless FFV1/.avi -- verified working in
    this environment, and round-trips pixel values exactly, unlike MJPG) for
    use as a test fixture, so nothing in the suite needs a real camera or a
    checked-in video asset."""
    height, width = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"FFV1")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    try:
        for frame in frames:
            writer.write(frame)
    finally:
        writer.release()


def write_empty_video(
    path: Path, fps: float = 10.0, size: tuple[int, int] = (32, 32)
) -> None:
    """Write a video container with zero frames -- OpenCV reports such a file
    as `isOpened() == True` (verified in this environment) but `read()` fails
    immediately, simulating a corrupt/unreadable video that opens but can't
    actually be decoded."""
    fourcc = cv2.VideoWriter_fourcc(*"FFV1")
    writer = cv2.VideoWriter(str(path), fourcc, fps, size)
    writer.release()
