from __future__ import annotations

import cv2
import numpy as np

BOARD_SIZE = 512  # warped square image side length, in pixels


def compute_homography(corners: list[tuple[float, float]]) -> np.ndarray:
    """`corners` must be [a8, h8, h1, a1] in image coordinates, in that order --
    the same order the calibration CLI asks the user to click them in, which is
    also what encodes the board's orientation relative to the camera."""
    src = np.array(corners, dtype=np.float32)
    dst = np.array(
        [[0, 0], [BOARD_SIZE, 0], [BOARD_SIZE, BOARD_SIZE], [0, BOARD_SIZE]],
        dtype=np.float32,
    )
    return cv2.getPerspectiveTransform(src, dst)


def warp_board(frame: np.ndarray, homography: np.ndarray) -> np.ndarray:
    return cv2.warpPerspective(frame, homography, (BOARD_SIZE, BOARD_SIZE))
