from datetime import datetime

import pytest

from chess_transmission.engine.game_session import GameMetadata
from chess_transmission.publish.pgn_file_writer import PgnFileWriter, PgnSaveError


def test_save_creates_missing_folder_and_writes_content(tmp_path):
    folder = tmp_path / "games"
    writer = PgnFileWriter(folder, GameMetadata(white="Alice", black="Bob"))

    writer.save("1. e4 e5 *")

    files = list(folder.glob("*.pgn"))
    assert len(files) == 1
    assert files[0].read_text() == "1. e4 e5 *"


def test_save_overwrites_same_file_in_place(tmp_path):
    writer = PgnFileWriter(tmp_path, GameMetadata(white="Alice", black="Bob"))

    writer.save("1. e4 *")
    writer.save("1. e4 e5 2. Nf3 *")

    files = list(tmp_path.glob("*.pgn"))
    assert len(files) == 1
    assert files[0].read_text() == "1. e4 e5 2. Nf3 *"


def test_filename_includes_timestamp_and_slugified_players(tmp_path):
    writer = PgnFileWriter(
        tmp_path,
        GameMetadata(white="White Player", black="Black Player"),
        started_at=datetime(2026, 7, 23, 15, 30, 0),
    )

    writer.save("*")

    files = list(tmp_path.glob("*.pgn"))
    assert files[0].name == "20260723-153000_White-Player-vs-Black-Player.pgn"


def test_two_sessions_started_at_same_moment_get_distinct_files(tmp_path):
    metadata = GameMetadata(white="Alice", black="Bob")
    same_moment = datetime(2026, 7, 23, 15, 30, 0)

    first = PgnFileWriter(tmp_path, metadata, started_at=same_moment)
    first.save("1. e4 *")
    second = PgnFileWriter(tmp_path, metadata, started_at=same_moment)
    second.save("1. d4 *")

    files = sorted(tmp_path.glob("*.pgn"))
    assert len(files) == 2
    contents = {f.read_text() for f in files}
    assert contents == {"1. e4 *", "1. d4 *"}


def test_folder_created_automatically_when_missing(tmp_path):
    folder = tmp_path / "does" / "not" / "exist" / "yet"
    assert not folder.exists()

    PgnFileWriter(folder, GameMetadata(white="Alice", black="Bob"))

    assert folder.is_dir()


def test_save_raises_pgn_save_error_on_write_failure(tmp_path, monkeypatch):
    writer = PgnFileWriter(tmp_path, GameMetadata(white="Alice", black="Bob"))

    def _raise(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("pathlib.Path.write_text", _raise)

    with pytest.raises(PgnSaveError):
        writer.save("1. e4 *")


def test_construction_raises_pgn_save_error_when_folder_cannot_be_created(
    tmp_path, monkeypatch
):
    def _raise(*args, **kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr("pathlib.Path.mkdir", _raise)

    with pytest.raises(PgnSaveError):
        PgnFileWriter(tmp_path / "unwritable", GameMetadata(white="Alice", black="Bob"))
