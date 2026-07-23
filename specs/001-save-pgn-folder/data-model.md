# Phase 1 Data Model: Save PGN to a Configured Folder

This feature adds no persistent database/data-layer entities — it's file I/O
layered on state the project already tracks in memory (`GameSession`). The
"entities" below are the conceptual objects introduced or changed.

## Configured Save Folder

A directory path, supplied by the operator via `config/settings.toml`
(`pgn_save_folder`). Optional — if absent, local saving is disabled.

- **Validation**: none at load time beyond being a valid path string; existence is
  handled at write time (created automatically, see below).
- **Lifecycle**: read once at process start (`Settings.load()`), passed to the
  writer at construction.

## Saved PGN File

One file per game session, living inside the Configured Save Folder.

| Field           | Description                                                        |
|-----------------|---------------------------------------------------------------------|
| `path`          | `<folder>/<filename>`, computed once at session start (see below)   |
| `content`       | The session's current full PGN (`GameSession.pgn_string()`)         |
| `filename`      | `{start-timestamp:%Y%m%d-%H%M%S}_{white-slug}-vs-{black-slug}.pgn`   |

- **Relationships**: one-to-one with a single `GameSession` instance (one run of
  `chess-transmission run`, or one `chess-transmission replay` invocation).
- **State transitions**: created (empty/header-only PGN) at session start → updated
  in place after every recognized move → updated again when the result is set. The
  file is never renamed or deleted by the tool.
- **Validation rules**: content MUST always be a syntactically valid PGN (guaranteed
  transitively, since it's exactly `GameSession.pgn_string()`'s output — no new PGN
  generation logic is introduced by this feature).

## `Settings` (changed)

`src/chess_transmission/config.py`'s `Settings` dataclass gains one field and
relaxes two existing ones:

| Field           | Before      | After           | Notes                                  |
|-----------------|-------------|-----------------|-----------------------------------------|
| `lichess_token` | `str`       | `str \| None`   | `None` if `LICHESS_API_TOKEN` unset     |
| `round_id`      | `str`       | `str \| None`   | `None` if `round_id` absent from toml   |
| `pgn_save_folder` | n/a       | `str \| None`   | new; `None` disables local saving       |

`Settings.load()` raises only if **both** Lichess config (token + round_id) and
`pgn_save_folder` are absent — otherwise there's nothing for the tool to do.

## `PgnFileWriter` (new)

`src/chess_transmission/publish/pgn_file_writer.py` — the write-side counterpart to
`LichessBroadcastPublisher`, same shape/spirit:

- Constructed with a folder path and a `GameMetadata` (to derive the filename).
- `save(pgn: str) -> None`: ensures the folder exists, writes `pgn` to the session's
  file (overwrite, not append).
- Raises `PgnSaveError` (new exception) on any `OSError`, with the failing path in
  the message.
