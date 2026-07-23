from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chess-transmission")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "calibrate", help="calibrate the camera against the physical board"
    )
    subparsers.add_parser("run", help="run the live camera-to-Lichess pipeline")
    replay_parser = subparsers.add_parser(
        "replay", help="replay recorded frames (dev/offline)"
    )
    replay_parser.add_argument("frames_dir")

    args, remaining = parser.parse_known_args(argv)

    if args.command == "calibrate":
        from chess_transmission.cli.calibrate import main as calibrate_main

        return calibrate_main(remaining)
    if args.command == "run":
        from chess_transmission.cli.run import main as run_main

        return run_main(remaining)
    if args.command == "replay":
        from chess_transmission.cli.replay import main as replay_main

        return replay_main([args.frames_dir, *remaining])
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
