# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- SPECKIT START -->
Active Spec Kit feature: [specs/001-save-pgn-folder/plan.md](specs/001-save-pgn-folder/plan.md) — read it for technologies, structure, and commands specific to the in-progress feature.
<!-- SPECKIT END -->

## What this is

Recognizes chess moves played on a physical board via an overhead camera and transmits them live to a **Lichess Broadcast** round. Chess.com is out of scope — it has no public live-broadcast/push API. A DGT electronic board is owned and planned as a second, alternative capture backend, but is not implemented yet (`board_source/dgt_source.py` is a stub).

The full architecture, rationale, and phased milestone plan live in `/home/felipe/.claude/plans/vamos-criar-um-projeto-resilient-cosmos.md` — read it before making structural changes; this file only covers what's needed day-to-day.

## Commands

```bash
uv sync                      # install/update dependencies
uv run pytest tests/unit -q  # run the unit suite (camera-free, runs in CI)
uv run pytest tests/unit -q -k test_infer_move_matches_expected_san  # single test
uv run black .                # format all Python files (required before committing, see constitution)

uv run chess-transmission calibrate   # interactive: click board corners + capture baseline
uv run chess-transmission run         # live loop: camera -> Lichess broadcast round
uv run chess-transmission replay <dir># replay recorded frames, no camera needed

uv run python scripts/dev_capture_frames.py <out_dir>  # record frames for fixtures/replay
```

`calibrate` and `run` require a real camera and are not exercised by the automated test suite — see `tests/integration/` and the plan's Verification section for the manual checks to run against actual hardware.

Config: copy `config/settings.example.toml` → `config/settings.toml` (camera index, Lichess round ID, PGN player/event headers, optional `pgn_save_folder`) and `.env.example` → `.env` (`LICHESS_API_TOKEN`, needs the `study:write` scope). Both copies are gitignored. Lichess config and `pgn_save_folder` are each optional, but at least one must be set — `Settings.load()` raises otherwise.

## Architecture

**Core insight the whole design follows from:** move inference does not need per-square piece identity. A `chess.Board` already knows what's on every square between confirmed moves, so the sensor layer only needs binary occupancy per square. `engine/move_inference.py::infer_move` tries every legal move from the current position, computes each candidate's resulting occupancy, and returns whichever move(s) reproduce the observed grid — this one algorithm handles disambiguation, castling, and en passant with no special-casing. The only unresolvable case is promotion piece choice (Q/R/B/N give identical occupancy), handled by defaulting to queen and flagging `needs_confirmation`.

**`BoardStateSource` is the seam between capture and everything else** (`board_source/base.py`). `engine/` and `publish/` depend only on this ABC (`BoardSnapshot.occupancy`), never on OpenCV or serial specifics — this is what will let a future `DGTBoardStateSource` slot in next to `CameraBoardStateSource` without touching move inference or the Lichess publisher.

**Data flow:** `vision/capture.py` (camera frames) → `vision/stability.py` (debounce: only emit once frame-to-frame diff is quiet for a full window, filtering out mid-move hand motion) → `vision/occupancy.py` (per-cell diff against `board_source/calibration.py`'s empty-board baseline, using the homography from `vision/perspective.py`) → `board_source/camera_source.py` wraps these into `BoardSnapshot`s → `engine/game_session.py::GameSession.observe()` runs `infer_move` and applies the result to its `chess.Board`/`chess.pgn.Game`. From there the updated PGN fans out to up to two independent, individually-optional sinks, each called from `cli/run.py`/`cli/replay.py` and each wrapped so a failure in one never blocks the other: `publish/lichess_broadcast.py::LichessBroadcastPublisher.push()` sends it via `berserk`, and `publish/pgn_file_writer.py::PgnFileWriter.save()` overwrites a local file (one per game session, named from the start timestamp + player names) in the operator-configured `pgn_save_folder`.

**Calibration is per-camera-rig and required before anything else works.** It's a one-time interactive step (`cli/calibrate.py`): click the 4 board corners in a fixed order (a8, h8, h1, a1 — this also encodes orientation), then capture one frame of the *empty* board to seed each square's baseline appearance. A game's starting position can't substitute for this (32 squares are already occupied). Output is `config/calibration.json` (gitignored, per-machine).

**Result-setting and resync can't come from the board.** Game result (resignation/draw agreement) and manual re-push after a failed publish are handled as commands typed at the `run` loop's stdin prompt (`result 1-0`, `resync`), not as separate CLI invocations — `GameSession` only exists in-memory for the duration of one `run`.

**Testing split:** `engine/` is fully deterministic and tested with fixtures derived by applying a move to a `chess.Board(fen)` and diffing occupancy — no images involved (`tests/unit/test_move_inference.py`, `test_game_session.py`). `vision/occupancy.py` is tested against synthetic numpy images, not real photos (`test_occupancy_diff.py`), since real-photo accuracy is lighting/hardware-dependent and would make the suite flaky. `publish/` is tested with the `berserk.Client` mocked out (`test_lichess_publisher.py`). Anything needing a live camera or a real Lichess round is manual/integration-only.
