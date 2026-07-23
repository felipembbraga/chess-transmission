from __future__ import annotations

import chess
import cv2
import numpy as np

from chess_transmission.vision.perspective import BOARD_SIZE

CELL_SIZE = BOARD_SIZE // 8
DEFAULT_OCCUPANCY_THRESHOLD = 18.0


def square_for_cell(row: int, col: int) -> chess.Square:
    """`row`/`col` are 0-indexed from the top-left of a warped board image, which
    corresponds to a8 given the [a8, h8, h1, a1] corner order used in perspective.py."""
    file_index = col
    rank_index = 7 - row
    return chess.square(file_index, rank_index)


def _cell_feature(warped: np.ndarray, row: int, col: int) -> float:
    y0, y1 = row * CELL_SIZE, (row + 1) * CELL_SIZE
    x0, x1 = col * CELL_SIZE, (col + 1) * CELL_SIZE
    cell = warped[y0:y1, x0:x1]
    gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY) if cell.ndim == 3 else cell
    return float(np.mean(gray))


def compute_baseline(empty_board_frame: np.ndarray) -> dict[chess.Square, float]:
    """Must be computed against a frame of the genuinely empty board -- a game's
    starting position already has 32 occupied squares and can't stand in for this."""
    return {
        square_for_cell(row, col): _cell_feature(empty_board_frame, row, col)
        for row in range(8)
        for col in range(8)
    }


def classify_occupancy(
    warped: np.ndarray,
    baseline: dict[chess.Square, float],
    threshold: float = DEFAULT_OCCUPANCY_THRESHOLD,
) -> dict[chess.Square, bool]:
    occupancy: dict[chess.Square, bool] = {}
    for row in range(8):
        for col in range(8):
            square = square_for_cell(row, col)
            current = _cell_feature(warped, row, col)
            occupancy[square] = abs(current - baseline[square]) > threshold
    return occupancy
