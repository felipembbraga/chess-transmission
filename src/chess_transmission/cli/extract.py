from __future__ import annotations

import argparse
from pathlib import Path

from chess_transmission.board_source.calibration import Calibration
from chess_transmission.board_source.video_file_source import VideoFileBoardStateSource
from chess_transmission.config import DEFAULT_CALIBRATION_PATH
from chess_transmission.engine.game_session import GameSession
from chess_transmission.engine.review import ReviewLog
from chess_transmission.engine.types import InferenceStatus
from chess_transmission.publish.pgn_file_writer import PgnFileWriter, PgnSaveError

PROGRESS_INTERVAL = 20


def _print_progress(source: VideoFileBoardStateSource) -> None:
    total = source.total_frames
    processed = source.frames_processed
    if total > 0:
        print(f"...progress: {processed}/{total} frames ({processed / total:.0%})")
    else:
        print(f"...progress: {processed} frames processed")


def _save_locally(pgn_writer: PgnFileWriter | None, pgn: str) -> None:
    if pgn_writer is None:
        return
    try:
        pgn_writer.save(pgn)
    except PgnSaveError as exc:
        print(f"warning: failed to save PGN locally: {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract a full game's PGN from a recorded video file, given "
        "an existing calibration -- runs to completion with no camera or "
        "operator interaction needed."
    )
    parser.add_argument("video_path", type=str)
    parser.add_argument(
        "--calibration", type=str, default=str(DEFAULT_CALIBRATION_PATH)
    )
    parser.add_argument(
        "--pgn-save-folder",
        type=str,
        default=None,
        help="also save the extracted PGN to a file in this folder",
    )
    args = parser.parse_args(argv)

    calibration = Calibration.from_json(Path(args.calibration))
    source = VideoFileBoardStateSource(args.video_path, calibration)
    session = GameSession()
    review_log = ReviewLog()

    pgn_writer = None
    if args.pgn_save_folder:
        try:
            pgn_writer = PgnFileWriter(args.pgn_save_folder, session.metadata)
        except PgnSaveError as exc:
            print(f"warning: local PGN saving disabled: {exc}")

    try:
        snapshots_seen = 0
        for snapshot in source.stream():
            snapshots_seen += 1
            frame_index = int(snapshot.timestamp)
            result = session.observe(snapshot.occupancy)
            if result.status == InferenceStatus.MATCHED:
                print(f"frame {frame_index}: {result.san}")
            elif result.status == InferenceStatus.AMBIGUOUS_PROMOTION:
                print(f"frame {frame_index}: {result.san} (promotion assumed queen)")
                review_log.record_assumed_promotion(
                    move_number=session.board.fullmove_number,
                    frame_index=frame_index,
                    assumed_san=result.san,
                )
            elif result.status == InferenceStatus.UNMATCHED:
                print(
                    f"frame {frame_index}: unmatched -- no legal move fits this occupancy"
                )
                review_log.record_unmatched(
                    move_number=session.board.fullmove_number,
                    frame_index=frame_index,
                )

            if result.status in (
                InferenceStatus.MATCHED,
                InferenceStatus.AMBIGUOUS_PROMOTION,
            ):
                _save_locally(pgn_writer, session.pgn_string())

            if snapshots_seen % PROGRESS_INTERVAL == 0:
                _print_progress(source)
    except RuntimeError as exc:
        print(f"error: {exc}")
        return 1

    _print_progress(source)
    print()
    print(session.pgn_string())
    print()
    print(review_log.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
