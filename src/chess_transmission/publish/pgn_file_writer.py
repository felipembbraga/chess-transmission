from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from chess_transmission.engine.game_session import GameMetadata


class PgnSaveError(Exception):
    """Raised when the local PGN file can't be written."""


def _slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-")
    return slug or "unknown"


def _filename_for(metadata: GameMetadata, started_at: datetime, folder: Path) -> str:
    stamp = started_at.strftime("%Y%m%d-%H%M%S")
    base = f"{stamp}_{_slugify(metadata.white)}-vs-{_slugify(metadata.black)}"
    candidate = f"{base}.pgn"
    suffix = 2
    while (folder / candidate).exists():
        candidate = f"{base}-{suffix}.pgn"
        suffix += 1
    return candidate


class PgnFileWriter:
    """Writes/updates one game session's PGN to a file in a configured folder.

    Mirrors LichessBroadcastPublisher's shape: constructed once per session,
    `save()` is called after every recognized move to overwrite the file in
    place with the session's current full PGN.
    """

    def __init__(
        self,
        folder: str | Path,
        metadata: GameMetadata,
        started_at: datetime | None = None,
    ):
        self._folder = Path(folder)
        try:
            self._folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise PgnSaveError(
                f"could not create folder {self._folder}: {exc}"
            ) from exc
        self._path = self._folder / _filename_for(
            metadata, started_at or datetime.now(), self._folder
        )

    def save(self, pgn: str) -> None:
        try:
            self._path.write_text(pgn)
        except OSError as exc:
            raise PgnSaveError(f"could not write {self._path}: {exc}") from exc
