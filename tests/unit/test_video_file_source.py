import chess
import numpy as np

from chess_transmission.board_source.calibration import Calibration
from chess_transmission.board_source.video_file_source import VideoFileBoardStateSource
from chess_transmission.engine.game_session import GameSession
from chess_transmission.engine.types import InferenceStatus
from chess_transmission.vision.perspective import BOARD_SIZE
from tests.unit.video_fixtures import write_synthetic_video

CELL_SIZE = BOARD_SIZE // 8
EMPTY = 200
PIECE = 40


def _make_frame(occupied_rows, extra_occupied=(), extra_empty=()) -> np.ndarray:
    frame = np.full((BOARD_SIZE, BOARD_SIZE, 3), EMPTY, dtype=np.uint8)
    for row in range(8):
        for col in range(8):
            occupied = row in occupied_rows
            if (row, col) in extra_occupied:
                occupied = True
            if (row, col) in extra_empty:
                occupied = False
            value = PIECE if occupied else EMPTY
            y0, y1 = row * CELL_SIZE, (row + 1) * CELL_SIZE
            x0, x1 = col * CELL_SIZE, (col + 1) * CELL_SIZE
            frame[y0:y1, x0:x1] = value
    return frame


def _make_calibration() -> Calibration:
    return Calibration(
        corners=[(0, 0), (BOARD_SIZE, 0), (BOARD_SIZE, BOARD_SIZE), (0, BOARD_SIZE)],
        baseline={chess.square_name(sq): float(EMPTY) for sq in chess.SQUARES},
    )


def test_stream_recognizes_e4_from_a_recorded_video(tmp_path):
    starting_rows = {0, 1, 6, 7}
    # A few repeated frames per position, so the stability detector's window
    # (8 frames) settles on each one -- same requirement a live camera has.
    frames = [_make_frame(starting_rows)] * 10
    frames += [
        _make_frame(starting_rows, extra_occupied={(4, 4)}, extra_empty={(6, 4)})
    ] * 10

    video_path = tmp_path / "game.avi"
    write_synthetic_video(video_path, frames, fps=10.0)

    source = VideoFileBoardStateSource(video_path, _make_calibration())
    session = GameSession()

    results = [session.observe(snapshot.occupancy) for snapshot in source.stream()]
    matched = [r for r in results if r.status == InferenceStatus.MATCHED]

    assert len(matched) == 1
    assert matched[0].san == "e4"


def test_progress_properties_report_frames_processed(tmp_path):
    frames = [_make_frame({0, 1, 6, 7})] * 5
    video_path = tmp_path / "game.avi"
    write_synthetic_video(video_path, frames, fps=10.0)

    source = VideoFileBoardStateSource(video_path, _make_calibration())

    list(source.stream())

    assert source.total_frames == 5
    assert source.frames_processed == 5
