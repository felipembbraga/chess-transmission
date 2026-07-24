import json

import chess
import chess.pgn
import numpy as np

from chess_transmission.cli import extract
from chess_transmission.engine.types import occupancy_from_board
from chess_transmission.vision.occupancy import square_for_cell
from chess_transmission.vision.perspective import BOARD_SIZE
from tests.unit.video_fixtures import write_empty_video, write_synthetic_video

CELL_SIZE = BOARD_SIZE // 8
EMPTY = 200
PIECE = 40


def _make_frame(occupied_rows, extra_occupied=(), extra_empty=()):
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


def _frame_for_occupancy(occupancy) -> np.ndarray:
    frame = np.full((BOARD_SIZE, BOARD_SIZE, 3), EMPTY, dtype=np.uint8)
    for row in range(8):
        for col in range(8):
            square = square_for_cell(row, col)
            value = PIECE if occupancy.get(square, False) else EMPTY
            y0, y1 = row * CELL_SIZE, (row + 1) * CELL_SIZE
            x0, x1 = col * CELL_SIZE, (col + 1) * CELL_SIZE
            frame[y0:y1, x0:x1] = value
    return frame


def _write_calibration(tmp_path):
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
    return calibration_path


def _write_game_video(tmp_path):
    starting_rows = {0, 1, 6, 7}
    frames = [_make_frame(starting_rows)] * 10
    frames += [
        _make_frame(starting_rows, extra_occupied={(4, 4)}, extra_empty={(6, 4)})
    ] * 10
    video_path = tmp_path / "game.avi"
    write_synthetic_video(video_path, frames, fps=10.0)
    return video_path


def test_extract_prints_correct_pgn_for_a_recorded_game(tmp_path, capsys):
    video_path = _write_game_video(tmp_path)
    calibration_path = _write_calibration(tmp_path)

    exit_code = extract.main([str(video_path), "--calibration", str(calibration_path)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "e4" in out
    assert "1. e4" in out


def test_extract_reports_clear_error_for_unreadable_video(tmp_path, capsys):
    calibration_path = _write_calibration(tmp_path)
    missing_video = tmp_path / "does-not-exist.avi"

    exit_code = extract.main(
        [str(missing_video), "--calibration", str(calibration_path)]
    )

    out = capsys.readouterr().out
    assert exit_code != 0
    assert "error" in out.lower()
    assert "e4" not in out


def test_extract_reports_clear_error_for_video_that_decodes_no_frames(tmp_path, capsys):
    calibration_path = _write_calibration(tmp_path)
    empty_video = tmp_path / "empty.avi"
    write_empty_video(empty_video)

    exit_code = extract.main([str(empty_video), "--calibration", str(calibration_path)])

    out = capsys.readouterr().out
    assert exit_code != 0
    assert "error" in out.lower()
    assert "1. e4" not in out
    assert "Result" not in out


# A real legal sequence reaching a pawn promotion, verified move-by-move with
# python-chess before being encoded as frames -- including confirming the final
# promotion is only ambiguous in piece choice (Q/R/B/N), not destination square
# (an earlier attempt promoting via a central-file diagonal capture produced a
# second, unwanted destination-square ambiguity: bxa8=Q and bxc8=Q had identical
# resulting occupancy, since neither a8 nor c8 change occupancy state on capture).
_PROMOTION_SEQUENCE_UCI = [
    "g2g4",
    "g8f6",
    "g4g5",
    "h7h6",
    "g5h6",
    "h8g8",
    "h6h7",
    "b8c6",
    "h7h8q",
]
_REPEAT = 10


def _write_video_with_unmatched_and_promotion(tmp_path):
    board = chess.Board()
    states = [occupancy_from_board(board)]
    for uci in _PROMOTION_SEQUENCE_UCI:
        board.push(chess.Move.from_uci(uci))
        states.append(occupancy_from_board(board))

    start_occupancy = states[0]
    garbage_occupancy = dict(start_occupancy)
    for square_name in ("d4", "d5", "e5"):
        garbage_occupancy[chess.parse_square(square_name)] = True

    frames = [_frame_for_occupancy(start_occupancy)] * _REPEAT
    frames += [_frame_for_occupancy(garbage_occupancy)] * _REPEAT  # -> UNMATCHED
    frames += [_frame_for_occupancy(start_occupancy)] * _REPEAT  # revert -> IDLE
    for occupancy in states[1:]:
        frames += [_frame_for_occupancy(occupancy)] * _REPEAT

    video_path = tmp_path / "game-with-review-items.avi"
    write_synthetic_video(video_path, frames, fps=10.0)
    return video_path


def test_extract_summarizes_unmatched_frames_and_assumed_promotions(tmp_path, capsys):
    video_path = _write_video_with_unmatched_and_promotion(tmp_path)
    calibration_path = _write_calibration(tmp_path)

    exit_code = extract.main([str(video_path), "--calibration", str(calibration_path)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "unmatched" in out.lower()
    assert "h8=Q" in out
    assert "assumed_promotion" in out
    assert "nothing to review" not in out.lower()


def test_extract_saves_pgn_to_configured_folder(tmp_path, capsys):
    video_path = _write_game_video(tmp_path)
    calibration_path = _write_calibration(tmp_path)
    save_folder = tmp_path / "games"

    exit_code = extract.main(
        [
            str(video_path),
            "--calibration",
            str(calibration_path),
            "--pgn-save-folder",
            str(save_folder),
        ]
    )

    assert exit_code == 0
    files = list(save_folder.glob("*.pgn"))
    assert len(files) == 1
    out = capsys.readouterr().out
    assert "1. e4" in out

    parsed = chess.pgn.read_game(files[0].open())
    assert parsed is not None
    assert [m.uci() for m in parsed.mainline_moves()] == ["e2e4"]


def test_extract_continues_when_pgn_writer_construction_fails(
    tmp_path, monkeypatch, capsys
):
    video_path = _write_game_video(tmp_path)
    calibration_path = _write_calibration(tmp_path)

    class ExplodingWriter:
        def __init__(self, *args, **kwargs):
            from chess_transmission.publish.pgn_file_writer import PgnSaveError

            raise PgnSaveError("boom: cannot create folder")

    monkeypatch.setattr(extract, "PgnFileWriter", ExplodingWriter)

    exit_code = extract.main(
        [
            str(video_path),
            "--calibration",
            str(calibration_path),
            "--pgn-save-folder",
            str(tmp_path / "unwritable"),
        ]
    )

    assert exit_code == 0
    assert "warning" in capsys.readouterr().out.lower()


def test_extract_continues_when_pgn_writer_save_fails(tmp_path, monkeypatch, capsys):
    video_path = _write_game_video(tmp_path)
    calibration_path = _write_calibration(tmp_path)

    class ExplodingWriter:
        def __init__(self, *args, **kwargs):
            pass

        def save(self, pgn):
            from chess_transmission.publish.pgn_file_writer import PgnSaveError

            raise PgnSaveError("boom: disk full")

    monkeypatch.setattr(extract, "PgnFileWriter", ExplodingWriter)

    exit_code = extract.main(
        [
            str(video_path),
            "--calibration",
            str(calibration_path),
            "--pgn-save-folder",
            str(tmp_path / "games"),
        ]
    )

    assert exit_code == 0
    assert "warning" in capsys.readouterr().out.lower()
