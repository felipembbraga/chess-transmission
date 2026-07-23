from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("config/settings.toml")
DEFAULT_CALIBRATION_PATH = Path("config/calibration.json")


@dataclass
class Settings:
    camera_index: int
    round_id: str | None
    event: str
    site: str
    white: str
    black: str
    round: str
    occupancy_threshold: float
    lichess_token: str | None
    pgn_save_folder: str | None

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_PATH) -> Settings:
        data = tomllib.loads(path.read_text())
        token = os.environ.get("LICHESS_API_TOKEN")
        round_id = data.get("round_id")
        pgn_save_folder = data.get("pgn_save_folder")

        if not (token and round_id) and not pgn_save_folder:
            raise RuntimeError(
                "nothing configured to do: set round_id + LICHESS_API_TOKEN for "
                "Lichess push, and/or pgn_save_folder for local saving"
            )

        return cls(
            camera_index=data.get("camera_index", 0),
            round_id=round_id,
            event=data.get("event", "Live Broadcast"),
            site=data.get("site", "?"),
            white=data.get("white", "White"),
            black=data.get("black", "Black"),
            round=data.get("round", "-"),
            occupancy_threshold=data.get("occupancy_threshold", 18.0),
            lichess_token=token,
            pgn_save_folder=pgn_save_folder,
        )
