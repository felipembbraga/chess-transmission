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
