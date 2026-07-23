# Quickstart: Save PGN to a Configured Folder

Validates the feature end-to-end once implemented. See [data-model.md](./data-model.md)
for field details and [research.md](./research.md) for the design decisions behind
each step.

## Prerequisites

```bash
uv sync
```

No camera or Lichess account is required to validate the local-save path in
isolation (that's the point of FR-001/FR-008).

## 1. Enable local saving

In `config/settings.toml`, add:

```toml
pgn_save_folder = "games"
```

You may leave Lichess settings (`round_id`) and `.env`'s `LICHESS_API_TOKEN` unset
entirely for this check — per the plan, local saving must work on its own.

## 2. Run the unit suite for this feature

```bash
uv run pytest tests/unit/test_pgn_file_writer.py tests/unit/test_config.py -q
```

Expected: all pass, camera-free (Principle III).

## 3. Exercise it against a real session (no camera needed)

Using `chess-transmission replay` against any existing recorded-frames directory
(see `scripts/dev_capture_frames.py` if you don't have one yet):

```bash
uv run chess-transmission replay <frames_dir>
```

Expected:
- A new file appears under `games/`, named like
  `20260723-153000_White-Player-vs-Black-Player.pgn`.
- Its content updates after each recognized move and matches what's printed to the
  console.
- Opening the file with any PGN reader (or `python -c "import chess.pgn, sys; print(chess.pgn.read_game(open(sys.argv[1])))" <file>`)
  parses without error.

## 4. Confirm the failure path doesn't crash the session

Temporarily set `pgn_save_folder` to a location the process can't write to (e.g. a
directory you `chmod 000`, or a path under `/root` without permission), then repeat
step 3.

Expected: a warning identifying the save failure prints to the console; move
recognition (and the Lichess push, if configured) continue uninterrupted. Revert
the permission/setting afterward.

## 5. Confirm two sessions don't collide

Run step 3 twice in a row against the same `pgn_save_folder`.

Expected: two distinct files exist afterward (different start timestamps), each
containing only its own game's moves.
