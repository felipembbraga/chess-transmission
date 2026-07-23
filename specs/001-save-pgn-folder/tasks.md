---

description: "Task list template for feature implementation"
---

# Tasks: Save PGN to a Configured Folder

**Input**: Design documents from `/specs/001-save-pgn-folder/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md

**Tests**: Included — this project's constitution (Principle III) requires camera-free unit tests for all non-hardware logic, and this feature is pure file I/O.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project (existing `chess_transmission` package): `src/chess_transmission/`, `tests/unit/` at repository root.

---

## Phase 1: Setup

**Purpose**: Document the new setting for operators

- [X] T001 Add a `pgn_save_folder` example entry (with a comment explaining it's optional and independent of Lichess config) to `config/settings.example.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config support that every user story depends on — none of the stories are testable until the tool can run with only a save folder configured (no Lichess credentials at all)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Add `pgn_save_folder: str | None` field to the `Settings` dataclass, and relax `lichess_token`/`round_id` from `str` to `str | None`, in `src/chess_transmission/config.py`
- [X] T003 Update `Settings.load()` in `src/chess_transmission/config.py`: read `LICHESS_API_TOKEN` and `round_id` optionally (no longer raise if absent), read `pgn_save_folder` from the TOML, and raise `RuntimeError` only when neither Lichess config (token + round_id) nor `pgn_save_folder` is present (depends on T002)
- [X] T004 [P] Create `tests/unit/test_config.py` covering: loads successfully with only `pgn_save_folder` set, loads successfully with only Lichess config set, loads with both set, and raises `RuntimeError` when neither is set (depends on T003)
- [X] T005 [P] In `src/chess_transmission/cli/run.py`, construct `LichessBroadcastPublisher` only when `settings.lichess_token` and `settings.round_id` are both present, otherwise leave the publisher as `None` (depends on T003)

**Checkpoint**: `Settings` supports folder-only operation; `run.py` no longer requires Lichess credentials to start.

---

## Phase 3: User Story 1 - Local PGN record of the live game (Priority: P1) 🎯 MVP

**Goal**: Every recognized move updates a PGN file in the operator-configured folder, independent of whether the Lichess push succeeds or is even configured.

**Independent Test**: Configure `pgn_save_folder` with no Lichess credentials set, run `chess-transmission replay <frames_dir>`, and confirm a PGN file appears and is updated after each recognized move.

### Implementation for User Story 1

- [X] T006 [P] [US1] Create `src/chess_transmission/publish/pgn_file_writer.py`: a `PgnSaveError` exception, a filename-generation helper implementing the `{start-timestamp}_{white-slug}-vs-{black-slug}.pgn` scheme from research.md, and a `PgnFileWriter` class whose `save(pgn: str) -> None` creates the folder if missing and writes/overwrites the session's file, wrapping any `OSError` as `PgnSaveError`

### Tests for User Story 1

- [X] T007 [US1] Create `tests/unit/test_pgn_file_writer.py`: `save()` creates the configured folder if missing, writes the given PGN content to the session's file, and repeated `save()` calls overwrite that same file in place (latest content wins, no duplication) (depends on T006)

### Wiring for User Story 1

- [X] T008 [US1] In `src/chess_transmission/cli/run.py`: construct a `PgnFileWriter` when `settings.pgn_save_folder` is set (else `None`), and after each applied move call `pgn_writer.save(session.pgn_string())` guarded by `if pgn_writer is not None`, alongside the existing (now-conditional) Lichess push (depends on T005, T006)
- [X] T009 [US1] Wire the same local saving into `src/chess_transmission/cli/replay.py`: add an optional `--pgn-save-folder` argument, construct a `PgnFileWriter` when provided, and call `pgn_writer.save(session.pgn_string())` after each recognized move (depends on T006)
- [X] T010 [US1] In `src/chess_transmission/cli/run.py`, wrap the existing `publisher.push(...)` call sites (the main loop and the `result`/`resync` stdin commands) in `try/except RuntimeError`, printing a warning instead of propagating — so a Lichess push failure never stops move recognition or local saving (depends on T005)

**Checkpoint**: User Story 1 is fully functional and independently testable — a live or replayed session saves its PGN locally whether or not Lichess is configured or reachable.

---

## Phase 4: User Story 2 - Distinct file per game session (Priority: P2)

**Goal**: Separate game sessions against the same configured folder never overwrite each other's saved files, and the folder is created automatically if missing.

**Independent Test**: Run two replayed sessions back-to-back against the same `pgn_save_folder` and confirm two distinct files exist afterward, each with only its own moves.

### Tests for User Story 2

- [X] T011 [US2] Extend `tests/unit/test_pgn_file_writer.py`: two `PgnFileWriter` instances constructed against the same folder with metadata that would otherwise produce identical filenames (e.g. same start timestamp) resolve to two distinct files, and neither's content is clobbered (pairs with T013 below — expected to fail until the collision-suffix hardening is implemented)
- [X] T012 [US2] Extend `tests/unit/test_pgn_file_writer.py`: constructing/saving against a folder that doesn't exist yet creates it automatically (formalizes spec User Story 2's Acceptance Scenario 2; behavior already present from T006) (depends on T006)

### Implementation for User Story 2

- [X] T013 [US2] In `src/chess_transmission/publish/pgn_file_writer.py`, harden the filename-generation helper: if a file with the computed name already exists at construction time, append a short disambiguating suffix (`-2`, `-3`, ...) so a new session never overwrites an existing one (depends on T006; makes T011 pass)

**Checkpoint**: Running multiple sessions against the same configured folder never overwrites a previous session's file.

---

## Phase 5: User Story 3 - Clear failure signal when saving fails (Priority: P3)

**Goal**: A local save failure is surfaced to the operator as a clear warning and never crashes the session or blocks the Lichess push.

**Independent Test**: Point `pgn_save_folder` at a location the process can't write to, run a replayed session, and confirm a clear warning prints while move recognition (and Lichess push, if configured) continue uninterrupted.

### Tests for User Story 3

- [X] T014 [P] [US3] Add a test in `tests/unit/test_pgn_file_writer.py` asserting `save()` raises `PgnSaveError` (not a bare `OSError`) when the underlying write fails — monkeypatch the write call to raise `OSError` rather than relying on real filesystem permission bits, for portability (depends on T006)

### Implementation for User Story 3

- [X] T015 [US3] In `src/chess_transmission/cli/run.py`, wrap the `pgn_writer.save(...)` call site in `try/except PgnSaveError`, printing a warning that names the failing path instead of propagating (depends on T008)
- [X] T016 [P] [US3] Apply the same `try/except PgnSaveError` wrapping around the `pgn_writer.save(...)` call in `src/chess_transmission/cli/replay.py` (depends on T009)

**Checkpoint**: All three user stories are independently functional — local saving works without Lichess, sessions never collide, and failures never crash the loop.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T017 [P] Update `CLAUDE.md`'s Architecture data-flow paragraph to mention the new local PGN save sink alongside the Lichess publisher
- [X] T018 [P] Update `README.md`'s Setup/Usage sections to document `pgn_save_folder` and running with no Lichess token configured
- [X] T019 Run `uv run pytest tests/unit -q` and `uv run black --check src tests scripts` to confirm the full suite passes and formatting is clean
- [X] T020 Execute `specs/001-save-pgn-folder/quickstart.md` end-to-end (a real or replayed session) to confirm the feature works as designed — this surfaced a real gap not covered by T015/T016: `PgnFileWriter`'s *construction* (folder creation) could still raise `PgnSaveError` uncaught in `run.py`/`replay.py`, crashing the process. Fixed by wrapping construction in `try/except PgnSaveError` too (falls back to `pgn_writer = None` with a warning), and added `test_construction_raises_pgn_save_error_when_folder_cannot_be_created` to `tests/unit/test_pgn_file_writer.py` to cover it.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - Story implementation proceeds in priority order (P1 → P2 → P3); US2 and US3 both extend the module US1 creates
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — no dependency on other stories
- **User Story 2 (P2)**: Builds on the `PgnFileWriter` module US1 creates (T006) — implement after US1 for a working base, though its acceptance criteria are independently verifiable
- **User Story 3 (P3)**: Builds on the call sites US1 wires in `run.py`/`replay.py` (T008, T009) — implement after US1

### Within Each User Story

- Tests and implementation for the same unit (e.g., `pgn_file_writer.py`) can be developed together; run the test suite before considering the story done
- Story complete before moving to the next priority

### Parallel Opportunities

- T004 and T005 (Phase 2) touch different files and can run in parallel once T003 is done
- T006 [P] stands alone; T007 depends on T006 existing so isn't truly concurrent, but is listed early since it's the story's test
- T011 and T012 (Phase 4) both extend the same test file — sequence them, don't edit concurrently
- T014 (Phase 5) touches the shared test file but has no dependency on T015/T016, so it can proceed in parallel with those two
- T015 and T016 (Phase 5) touch different files (`run.py` vs `replay.py`) and can run in parallel
- T017 and T018 (Phase 6) touch different files and can run in parallel

---

## Parallel Example: Phase 2 (Foundational)

```bash
# T004 and T005 touch different files and both only depend on T003 being done:
Task: "Create tests/unit/test_config.py covering folder-only, lichess-only, both, and neither-configured cases"
Task: "In src/chess_transmission/cli/run.py, construct LichessBroadcastPublisher only when configured"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run `chess-transmission replay <frames_dir>` with `pgn_save_folder` set and no Lichess credentials; confirm the PGN file appears and updates
5. This is already a usable increment — local saving works end-to-end

### Incremental Delivery

1. Complete Setup + Foundational → foundation ready (tool runs without Lichess configured)
2. Add User Story 1 → validate independently → usable MVP (local save works)
3. Add User Story 2 → validate independently → sessions never collide
4. Add User Story 3 → validate independently → failures never crash the loop
5. Each story adds value without breaking the previous one

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- This feature has no `contracts/` artifacts (no external API/service interface) and no database entities — see data-model.md for the conceptual entities involved
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence

---

## Phase 7: Convergence

- [X] T021 Add an automated test exercising `chess_transmission.cli.replay.main()` end-to-end (synthetic frames + calibration fixture, no real camera) with a `PgnFileWriter` that fails both at construction and at `save()`, asserting `main()` returns `0` without raising and prints a warning, per US3/AC1 (partial) — `tests/unit/test_replay_pgn_save_failure.py`, 2 tests (construction failure, save failure)
