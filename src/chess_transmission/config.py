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
    round_id: str
    event: str
    site: str
    white: str
    black: str
    round: str
    occupancy_threshold: float
    lichess_token: str

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_PATH) -> Settings:
        data = tomllib.loads(path.read_text())
        token = os.environ.get("LICHESS_API_TOKEN")
        if not token:
            raise RuntimeError("LICHESS_API_TOKEN environment variable is not set")
        return cls(
            camera_index=data.get("camera_index", 0),
            round_id=data["round_id"],
            event=data.get("event", "Live Broadcast"),
            site=data.get("site", "?"),
            white=data.get("white", "White"),
            black=data.get("black", "Black"),
            round=data.get("round", "-"),
            occupancy_threshold=data.get("occupancy_threshold", 18.0),
            lichess_token=token,
        )
