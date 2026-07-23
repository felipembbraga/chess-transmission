import json

import chess
import cv2
import numpy as np
import pytest

from chess_transmission.cli import replay
from chess_transmission.publish.pgn_file_writer import PgnSaveError
from chess_transmission.vision.perspective import BOARD_SIZE

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


@pytest.fixture
def replay_fixtures(tmp_path):
    """A tiny synthetic frames dir + calibration reproducing the starting
    position, then 1. e4 -- enough to trigger exactly one save() call, with
    no real camera or photograph involved (Principle III)."""
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()

    starting_rows = {0, 1, 6, 7}
    cv2.imwrite(str(frames_dir / "frame_000.png"), _make_frame(starting_rows))
    cv2.imwrite(
        str(frames_dir / "frame_001.png"),
        _make_frame(starting_rows, extra_occupied={(4, 4)}, extra_empty={(6, 4)}),
    )

    calibration_path = tmp_path / "calibration.json"
    calibration_path.write_text(
        json.dumps(
            {
                "corners": [
                    [0, 0],
                    [BOARD_SIZE, 0],
                    [BOARD_SIZE, BOARD_SIZE],
                    [0, BOARD_SIZE],
                ],
                "baseline": {
                    chess.square_name(sq): float(EMPTY) for sq in chess.SQUARES
                },
            }
        )
    )

    return frames_dir, calibration_path


def test_replay_continues_when_pgn_writer_construction_fails(
    replay_fixtures, tmp_path, monkeypatch, capsys
):
    frames_dir, calibration_path = replay_fixtures

    class ExplodingWriter:
        def __init__(self, *args, **kwargs):
            raise PgnSaveError("boom: cannot create folder")

    monkeypatch.setattr(replay, "PgnFileWriter", ExplodingWriter)

    exit_code = replay.main(
        [
            str(frames_dir),
            "--calibration",
            str(calibration_path),
            "--pgn-save-folder",
            str(tmp_path / "unwritable"),
        ]
    )

    assert exit_code == 0
    assert "warning" in capsys.readouterr().out.lower()


def test_replay_continues_when_pgn_writer_save_fails(
    replay_fixtures, tmp_path, monkeypatch, capsys
):
    frames_dir, calibration_path = replay_fixtures

    class ExplodingWriter:
        def __init__(self, *args, **kwargs):
            pass

        def save(self, pgn):
            raise PgnSaveError("boom: disk full")

    monkeypatch.setattr(replay, "PgnFileWriter", ExplodingWriter)

    exit_code = replay.main(
        [
            str(frames_dir),
            "--calibration",
            str(calibration_path),
            "--pgn-save-folder",
            str(tmp_path / "games"),
        ]
    )

    assert exit_code == 0
    assert "warning" in capsys.readouterr().out.lower()
