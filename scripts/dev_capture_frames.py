"""Record frames from the camera to disk, for building vision test fixtures or
replaying a session offline via `chess-transmission replay`.

Usage: uv run python scripts/dev_capture_frames.py <out_dir> [--camera-index 0] [--interval 1.0]
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2

from chess_transmission.vision.capture import CameraCapture


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_dir", type=str)
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument(
        "--interval", type=float, default=1.0, help="seconds between frames"
    )
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("press Ctrl+C to stop")
    with CameraCapture(args.camera_index) as cam:
        index = 0
        while True:
            frame = cam.read()
            path = out_dir / f"frame_{index:05d}.png"
            cv2.imwrite(str(path), frame)
            print(f"saved {path}")
            index += 1
            time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
