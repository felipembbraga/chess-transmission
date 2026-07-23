from pathlib import Path

import pytest

from chess_transmission.config import Settings

BASE_TOML = """
camera_index = 1
occupancy_threshold = 12.5
event = "Test Event"
white = "Alice"
black = "Bob"
"""


def _write(tmp_path, extra_toml: str) -> Path:
    path = tmp_path / "settings.toml"
    path.write_text(BASE_TOML + extra_toml)
    return path


def test_load_with_only_pgn_save_folder_configured(tmp_path, monkeypatch):
    monkeypatch.delenv("LICHESS_API_TOKEN", raising=False)
    path = _write(tmp_path, 'pgn_save_folder = "games"\n')

    settings = Settings.load(path)

    assert settings.pgn_save_folder == "games"
    assert settings.lichess_token is None
    assert settings.round_id is None


def test_load_with_only_lichess_config_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("LICHESS_API_TOKEN", "secret-token")
    path = _write(tmp_path, 'round_id = "abcd1234"\n')

    settings = Settings.load(path)

    assert settings.lichess_token == "secret-token"
    assert settings.round_id == "abcd1234"
    assert settings.pgn_save_folder is None


def test_load_with_both_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("LICHESS_API_TOKEN", "secret-token")
    path = _write(tmp_path, 'round_id = "abcd1234"\npgn_save_folder = "games"\n')

    settings = Settings.load(path)

    assert settings.lichess_token == "secret-token"
    assert settings.round_id == "abcd1234"
    assert settings.pgn_save_folder == "games"


def test_load_raises_when_neither_configured(tmp_path, monkeypatch):
    monkeypatch.delenv("LICHESS_API_TOKEN", raising=False)
    path = _write(tmp_path, "")

    with pytest.raises(RuntimeError):
        Settings.load(path)
