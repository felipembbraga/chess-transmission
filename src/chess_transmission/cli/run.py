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


def _maybe_handle_stdin_command(
    session: GameSession, publisher: LichessBroadcastPublisher
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
        publisher.push(session.pgn_string())
        print(f"result set to {parts[1]} and pushed")
    elif parts[0] == "resync":
        publisher.push(session.pgn_string())
        print("resynced current PGN to Lichess")
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
    publisher = LichessBroadcastPublisher(settings.lichess_token, settings.round_id)

    print("watching board... play a move (type 'result 1-0'/'resync' anytime)")
    for snapshot in source.stream():
        _maybe_handle_stdin_command(session, publisher)
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
        publisher.push(session.pgn_string())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
