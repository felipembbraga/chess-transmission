# Implementation Plan: Save PGN to a Configured Folder

**Branch**: `001-save-pgn-folder` (no dedicated git branch created — implemented directly on `main`) | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-save-pgn-folder/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Write the live game's PGN to a file in an operator-configured local folder, updated
in place after every recognized move and after the result is set — a durable local
record that works independently of whether the Lichess push succeeds or is even
configured. Implemented as a new `PgnFileWriter` (mirroring the existing
`LichessBroadcastPublisher`), a new optional `pgn_save_folder` setting in
`config/settings.toml`, and relaxing `Settings` so Lichess credentials are no
longer hard-required when only local saving is wanted.

## Technical Context

**Language/Version**: Python >=3.12 (existing project stack, unchanged)

**Primary Dependencies**: none new — stdlib `pathlib`/`tomllib` and the existing
`chess.pgn`-backed `GameSession.pgn_string()`

**Storage**: local filesystem — one PGN text file per game session, in the
operator-configured folder

**Testing**: `pytest`, using the `tmp_path` fixture for filesystem isolation — no
camera or physical board involved (Principle III)

**Target Platform**: same host already running `chess-transmission` (Linux/macOS/Windows dev machine)

**Project Type**: single project — extends the existing `chess_transmission` package, no new project/service

**Performance Goals**: none beyond SC-001 (file reflects the current move within 1s), trivially met by a synchronous local write of a small text file

**Constraints**: a save failure MUST NOT crash the live loop or block the Lichess push (FR-007); local saving MUST work with no Lichess credentials configured at all (FR-001/FR-008)

**Scale/Scope**: one file per game session; one write per human move (not a high-frequency path)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Occupancy-Over-Identity | N/A | Feature doesn't touch occupancy detection or move inference. |
| II. Hardware-Decoupled Core | PASS | New `PgnFileWriter` lives in `publish/`, alongside `LichessBroadcastPublisher` — `engine/` (`GameSession`) is untouched and stays ignorant of where its PGN ends up. Same decoupling spirit as the `BoardStateSource` boundary, applied to the output side. |
| III. Camera-Free Determinism | PASS | Pure file I/O; fully unit-testable with `tmp_path`, no hardware. |
| IV. No Silent Guessing on Unknowable State | PASS | Not a guessing scenario, but FR-007's "surface a clear error, never fail silently" is the same principle applied to save failures — honored via a typed `PgnSaveError` the caller must handle. |
| V. Lichess-Only Transmission, Deferred Scope | PASS | No new platform or hardware backend introduced; stays within the current milestone. |

No violations — Complexity Tracking is not needed for this feature.

*Post-design re-check*: unchanged — the Phase 1 design (below) doesn't introduce
anything not already covered above.

## Project Structure

### Documentation (this feature)

```text
specs/001-save-pgn-folder/
├── plan.md              # this file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
└── tasks.md              # Phase 2 output (/speckit-tasks — not created by this command)
```

No `contracts/` directory: this feature exposes no external API/service interface
to document — it's an internal config option plus a local file writer consumed only
by this project's own CLI entry points.

### Source Code (repository root)

```text
src/chess_transmission/
├── config.py                       # + pgn_save_folder; lichess_token/round_id become optional
├── publish/
│   ├── lichess_broadcast.py        # unchanged
│   └── pgn_file_writer.py          # NEW: PgnFileWriter, PgnSaveError, filename generation
├── cli/
│   ├── run.py                      # construct/call PgnFileWriter alongside the publisher, both optional
│   └── replay.py                   # same wiring, for offline/replayed sessions
└── engine/                         # unchanged

tests/unit/
├── test_pgn_file_writer.py         # NEW
└── test_config.py                  # NEW — optional lichess fields, pgn_save_folder loading, error when neither sink configured
```

**Structure Decision**: Single existing project (no new service/package). This
feature extends `config.py`, adds one new module under `publish/` matching the
existing `LichessBroadcastPublisher` pattern, and wires both CLI entry points that
build a `GameSession`.

## Complexity Tracking

*No entries — Constitution Check has no unresolved violations.*
