import numpy as np

from chess_transmission.vision.occupancy import (
    classify_occupancy,
    compute_baseline,
    square_for_cell,
)
from chess_transmission.vision.perspective import BOARD_SIZE

CELL_SIZE = BOARD_SIZE // 8


def make_uniform_frame(value: int) -> np.ndarray:
    return np.full((BOARD_SIZE, BOARD_SIZE, 3), value, dtype=np.uint8)


def paint_cell(frame: np.ndarray, row: int, col: int, value: int) -> None:
    y0, y1 = row * CELL_SIZE, (row + 1) * CELL_SIZE
    x0, x1 = col * CELL_SIZE, (col + 1) * CELL_SIZE
    frame[y0:y1, x0:x1] = value


def test_classify_occupancy_detects_changed_cells_only():
    empty_frame = make_uniform_frame(200)
    baseline = compute_baseline(empty_frame)

    current_frame = empty_frame.copy()
    occupied_cells = [(0, 0), (3, 4), (7, 7)]
    for row, col in occupied_cells:
        paint_cell(current_frame, row, col, 40)

    occupancy = classify_occupancy(current_frame, baseline)

    expected_occupied = {square_for_cell(row, col) for row, col in occupied_cells}
    actual_occupied = {square for square, occupied in occupancy.items() if occupied}
    assert actual_occupied == expected_occupied


def test_classify_occupancy_reports_untouched_board_as_all_empty():
    empty_frame = make_uniform_frame(180)
    baseline = compute_baseline(empty_frame)

    occupancy = classify_occupancy(empty_frame, baseline)

    assert all(not occupied for occupied in occupancy.values())


def test_square_for_cell_matches_clicked_corner_order():
    # corners are clicked [a8, h8, h1, a1], so the top-left warped cell (0, 0) is a8
    # and the bottom-right cell (7, 7) is h1.
    import chess

    assert chess.square_name(square_for_cell(0, 0)) == "a8"
    assert chess.square_name(square_for_cell(0, 7)) == "h8"
    assert chess.square_name(square_for_cell(7, 0)) == "a1"
    assert chess.square_name(square_for_cell(7, 7)) == "h1"
