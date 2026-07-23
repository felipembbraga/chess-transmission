from __future__ import annotations

import argparse
import select
import sys
from pathlib import Path

import chess

from chess_transmission.board_source.calibration import Calibration
from chess_transmission.board_source.camera_source import CameraBoardStateSource
from chess_transmission.config import (
    DEFAULT_CALIBRATION_PATH,
    DEFAULT_CONFIG_PATH,
    Settings,
)
from chess_transmission.engine.game_session import GameMetadata, GameSession
from chess_transmission.engine.types import InferenceStatus
from chess_transmission.publish.lichess_broadcast import LichessBroadcastPublisher
from chess_transmission.publish.pgn_file_writer import PgnFileWriter, PgnSaveError

PROMOTION_PIECES = {
    "q": chess.QUEEN,
    "r": chess.ROOK,
    "b": chess.BISHOP,
    "n": chess.KNIGHT,
}


def _read_line_with_timeout(timeout_seconds: float) -> str | None:
    ready, _, _ = select.select([sys.stdin], [], [], timeout_seconds)
    if ready:
        return sys.stdin.readline().strip()
    return None


def _push_to_lichess(publisher: LichessBroadcastPublisher | None, pgn: str) -> None:
    if publisher is None:
        return
    try:
        publisher.push(pgn)
    except RuntimeError as exc:
        print(f"warning: failed to push to Lichess: {exc}")


def _save_locally(pgn_writer: PgnFileWriter | None, pgn: str) -> None:
    if pgn_writer is None:
        return
    try:
        pgn_writer.save(pgn)
    except PgnSaveError as exc:
        print(f"warning: failed to save PGN locally: {exc}")


def _maybe_handle_stdin_command(
    session: GameSession,
    publisher: LichessBroadcastPublisher | None,
    pgn_writer: PgnFileWriter | None,
) -> None:
    """While waiting for the next stable board snapshot, also let the operator type
    `result 1-0` / `result 1/2-1/2` / `resync` at any time -- these can't be inferred
    from the board and would otherwise require restarting the process."""
    line = _read_line_with_timeout(0)
    if not line:
        return
    parts = line.split()
    if parts[0] == "result" and len(parts) == 2:
        try:
            session.set_result(parts[1])
        except ValueError as exc:
            print(exc)
            return
        _push_to_lichess(publisher, session.pgn_string())
        _save_locally(pgn_writer, session.pgn_string())
        print(f"result set to {parts[1]}")
    elif parts[0] == "resync":
        _push_to_lichess(publisher, session.pgn_string())
        _save_locally(pgn_writer, session.pgn_string())
        print("resynced current PGN")
    else:
        print(f"unrecognized command: {line!r} (try: result 1-0 | resync)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the live camera-to-Lichess pipeline."
    )
    parser.add_argument("--config", type=str, default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument(
        "--calibration", type=str, default=str(DEFAULT_CALIBRATION_PATH)
    )
    args = parser.parse_args(argv)

    settings = Settings.load(Path(args.config))
    calibration = Calibration.from_json(Path(args.calibration))

    source = CameraBoardStateSource(
        settings.camera_index, calibration, settings.occupancy_threshold
    )
    session = GameSession(
        GameMetadata(
            event=settings.event,
            site=settings.site,
            white=settings.white,
            black=settings.black,
            round=settings.round,
        )
    )

    publisher = None
    if settings.lichess_token and settings.round_id:
        publisher = LichessBroadcastPublisher(settings.lichess_token, settings.round_id)

    pgn_writer = None
    if settings.pgn_save_folder:
        try:
            pgn_writer = PgnFileWriter(settings.pgn_save_folder, session.metadata)
        except PgnSaveError as exc:
            print(f"warning: local PGN saving disabled: {exc}")

    print("watching board... play a move (type 'result 1-0'/'resync' anytime)")
    for snapshot in source.stream():
        _maybe_handle_stdin_command(session, publisher, pgn_writer)
        result = session.observe(snapshot.occupancy)

        if result.status == InferenceStatus.UNMATCHED:
            print("move not recognized from a stable position")
            san = _read_line_with_timeout(5.0)
            if san:
                session.force_san(san)
                print(f"applied manual move: {san}")
            else:
                continue
        elif result.status == InferenceStatus.AMBIGUOUS_PROMOTION:
            print(
                f"{result.san} assumed -- type q/r/b/n within 10s to correct the promotion"
            )
            answer = _read_line_with_timeout(10.0)
            if answer and answer.strip().lower() in PROMOTION_PIECES:
                piece = PROMOTION_PIECES[answer.strip().lower()]
                session.correct_promotion(piece)
                print(f"corrected promotion to {answer.strip().lower()}")
        elif result.status != InferenceStatus.MATCHED:
            continue

        print(f"move: {result.san}")
        _push_to_lichess(publisher, session.pgn_string())
        _save_locally(pgn_writer, session.pgn_string())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
