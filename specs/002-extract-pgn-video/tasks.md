---

description: "Task list template for feature implementation"
---

# Tasks: Extract PGN from a Recorded Video File

**Input**: Design documents from `/specs/002-extract-pgn-video/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md

**Tests**: Included — this project's constitution (Principle III) requires camera-free unit tests for all non-hardware logic, and this feature (uniquely) needs no hardware anywhere, not even to test the "live-like" recognition path.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project (existing `chess_transmission` package): `src/chess_transmission/`, `tests/unit/` at repository root.

---

## Phase 1: Setup

**Purpose**: Shared test infrastructure this feature's whole suite depends on

- [X] T001 Create `tests/unit/video_fixtures.py`: a `write_synthetic_video(path, frames, fps)` helper (using `cv2.VideoWriter` with the lossless FFV1 codec into an `.avi` container, per research.md #7 — MJPG was tried first but its lossy compression drifted pixel values enough to break exact-value assertions) that `test_video_capture.py`, `test_video_file_source.py`, and `test_cli_extract.py` all reuse to build tiny in-test video files — no checked-in video asset, no real camera

---

## Phase 2: User Story 1 - Get a PGN from a recorded game video (Priority: P1) 🎯 MVP

**Goal**: `chess-transmission extract <video_file>` recognizes a full game from a
recorded video (given a matching calibration) and prints its PGN, with no
operator interaction while it runs.

**Independent Test**: Point the command at a synthetic video encoding a short
known sequence of moves and confirm the printed PGN matches exactly.

### Implementation for User Story 1

- [X] T002 [P] [US1] Create `src/chess_transmission/vision/video_capture.py`: `VideoFileCapture` wrapping `cv2.VideoCapture(path)` — raises a clear typed error if the file can't be opened (mirrors `CameraCapture`'s open-failure pattern); `read()` returns `None` at end-of-file rather than raising (EOF is normal termination, not an error, per research.md #2); `frames(target_fps=8.0)` samples by skipping frames based on the video's own reported FPS instead of sleeping (research.md #3); exposes `frames_read`/`total_frames` for progress (research.md #4)
- [X] T003 [US1] Create `tests/unit/test_video_capture.py`: reads frames in order from a synthetic video, stops cleanly at EOF with no exception, samples at roughly the target rate given the source video's reported FPS, reports correct `frames_read`/`total_frames`, and raises a clear typed error for a nonexistent/corrupt path (depends on T001, T002)
- [X] T004 [P] [US1] Create `src/chess_transmission/board_source/video_file_source.py`: `VideoFileBoardStateSource(BoardStateSource)` composing `VideoFileCapture` with the existing `StabilityDetector`, `classify_occupancy`, and `warp_board` — identical downstream pipeline to `CameraBoardStateSource`; `stream()` yields `BoardSnapshot`s until the video ends (terminates, unlike the live camera source's infinite loop); `calibrate()` raises `NotImplementedError`; exposes `frames_processed`/`total_frames` (depends on T002)
- [X] T005 [US1] Create `tests/unit/test_video_file_source.py`: encode a synthetic video for the starting position followed by 1. e4 (same frame-painting approach as `test_occupancy_diff.py`/`test_replay_pgn_save_failure.py`) and assert `.stream()` yields snapshots a `GameSession` correctly recognizes as `e4` (depends on T001, T004)
- [X] T006 [US1] Create `src/chess_transmission/cli/extract.py`: argparse with `video_path` and `--calibration` (default `DEFAULT_CALIBRATION_PATH`); construct `VideoFileBoardStateSource`, catching its open-failure error and printing one clear line plus a non-zero return instead of a traceback (FR-007); loop `.stream()` through `GameSession.observe()`, printing per-frame `MATCHED`/`AMBIGUOUS_PROMOTION`/`UNMATCHED` exactly like `cli/replay.py`; print the full PGN once the video ends (FR-004) (depends on T004) — while implementing, found FR-008 (periodic progress reporting) had no task actually wired to it (T002/T004 only exposed the properties); added `_print_progress()` here, called every `PROGRESS_INTERVAL` snapshots and once more at the end, closing that gap
- [X] T007 [US1] Wire an `extract` subcommand into `src/chess_transmission/cli/main.py`, matching the existing `calibrate`/`run`/`replay` dispatch pattern (depends on T006)
- [X] T008 [US1] Create `tests/unit/test_cli_extract.py`: run `extract.main()` end-to-end against a synthetic video + calibration fixture and assert the printed PGN matches the encoded moves; a second test asserts a nonexistent/corrupt video path produces a clean error message and non-zero return, never a traceback or partial PGN (FR-007) (depends on T001, T006)

**Checkpoint**: User Story 1 is fully functional and independently testable — `chess-transmission extract` produces a correct PGN end-to-end, with zero real hardware anywhere in its test coverage.

---

## Phase 3: User Story 2 - See what needs manual review (Priority: P2)

**Goal**: Anything the extraction couldn't confidently recognize (unmatched
frames, assumed promotions) is collected into one scannable end-of-run summary,
distinct from the per-frame processing output.

**Independent Test**: Run extraction against a synthetic video containing one
unrecognizable stretch and one promotion, and confirm both show up in the final
summary rather than only in scattered per-frame log lines.

### Implementation for User Story 2

- [X] T009 [P] [US2] Create `src/chess_transmission/engine/review.py`: `ReviewItem` (`kind`, `move_number`, `frame_index`, `detail`) and `ReviewLog` with `record_unmatched(...)`, `record_assumed_promotion(...)`, and `summary() -> str` (a short "nothing to review" line when empty) — no dependency on anything from User Story 1, can be built in parallel with it
- [X] T010 [P] [US2] Create `tests/unit/test_review_log.py`: covers recording both item kinds and the summary text for both a populated and an empty log (depends on T009)
- [X] T011 [US2] Wire `ReviewLog` into `src/chess_transmission/cli/extract.py`: record an item wherever the loop already inspects `InferenceStatus.UNMATCHED` / `InferenceStatus.AMBIGUOUS_PROMOTION`, and print `review_log.summary()` after the final PGN (depends on T006, T009)
- [X] T012 [US2] Extend `tests/unit/test_cli_extract.py`: a synthetic video containing an unmatched frame and a promotion asserts both appear in the printed review summary (depends on T011) — the promotion move sequence had to be constructed and verified programmatically with python-chess: a first attempt promoting via a central-file diagonal capture (`b7a8q`) turned out to have a *second*, unwanted ambiguity (`bxa8=Q` and `bxc8=Q` produced identical occupancy, since capturing onto an already-occupied square doesn't change its occupancy bit either way) on top of the intended Q/R/B/N ambiguity; switched to a straight-push promotion onto a vacated square, which is only ambiguous in piece choice

**Checkpoint**: User Story 2 is independently functional — the operator gets a scannable list of exactly what to double-check, without reading the full per-frame log.

---

## Phase 4: User Story 3 - Save the extracted PGN to a file (Priority: P3)

**Goal**: The extracted PGN can also be saved to a configured folder, reusing
the local-save behavior already built for live/replayed sessions.

**Independent Test**: Run extraction with a save folder configured and confirm
a PGN file appears there matching the console output; confirm a save failure
prints a warning without stopping extraction.

### Implementation for User Story 3

- [X] T013 [US3] Extend `src/chess_transmission/cli/extract.py`: add `--pgn-save-folder`; construct `PgnFileWriter` when provided, wrapping construction in `try/except PgnSaveError` (same fix already established in `cli/replay.py`); call `pgn_writer.save(...)` after each recognized move, wrapped in `try/except PgnSaveError` (depends on T006)
- [X] T014 [US3] Extend `tests/unit/test_cli_extract.py`: asserts a PGN file appears in a configured save folder matching the console output, and that a save failure (construction or `save()`) prints a warning without crashing extraction — mirroring `tests/unit/test_replay_pgn_save_failure.py`'s pattern (depends on T013)

**Checkpoint**: All three user stories are independently functional — extraction works end-to-end, review items are never silently dropped, and the result can be saved to a file exactly like any other session.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T015 [P] Update `CLAUDE.md`'s Architecture section to mention `VideoFileBoardStateSource` alongside `CameraBoardStateSource` and the new `extract` command
- [X] T016 [P] Update `README.md`'s Usage section to document `chess-transmission extract`
- [X] T017 Run `uv run pytest tests/unit -q` and `uv run black --check src tests scripts` to confirm the full suite passes and formatting is clean
- [X] T018 Execute `specs/002-extract-pgn-video/quickstart.md` end-to-end (synthetic video required, real video optional) to confirm the feature works as designed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **User Story 1 (Phase 2)**: Depends on Setup (needs the fixture helper for its tests)
- **User Story 2 (Phase 3)**: `engine/review.py` itself (T009, T010) has no dependency on User Story 1 and can be built in parallel with it; wiring it in (T011, T012) depends on `cli/extract.py` existing (T006)
- **User Story 3 (Phase 4)**: Depends on `cli/extract.py` existing (T006); otherwise independent of User Story 2
- **Polish (Phase 5)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start right after Setup — no dependency on other stories
- **User Story 2 (P2)**: `ReviewLog` itself is independent; its wiring into `extract.py` requires User Story 1's `cli/extract.py`
- **User Story 3 (P3)**: Requires User Story 1's `cli/extract.py`; independent of User Story 2 (both extend the same file but touch different parts of the loop)

### Within Each User Story

- Implementation and its test can be developed together; run the test suite before considering the story done
- Story complete before moving to the next priority

### Parallel Opportunities

- T002 (Phase 2) can proceed alongside T001 (Phase 1) — the implementation itself doesn't need the test fixture helper, only its test does
- T004 and T003 (Phase 2) touch different files and can run in parallel once T002 is done
- T009 and T010 (Phase 3, `engine/review.py`) have zero dependency on anything in User Story 1 and can be built in parallel with the entire Phase 2
- T013 (Phase 4) and T011 (Phase 3) both extend `cli/extract.py` — sequence them, don't edit concurrently
- T015 and T016 (Phase 5) touch different files and can run in parallel

---

## Parallel Example: User Story 1 vs. User Story 2

```bash
# T002 (Phase 2) and T009 (Phase 3) have no dependency on each other at all:
Task: "Create src/chess_transmission/vision/video_capture.py (VideoFileCapture)"
Task: "Create src/chess_transmission/engine/review.py (ReviewItem, ReviewLog)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: User Story 1
3. **STOP and VALIDATE**: run `chess-transmission extract` against a synthetic (or real) video with a matching calibration; confirm the printed PGN matches the game played
4. This is already a usable increment — extraction works end-to-end

### Incremental Delivery

1. Complete Setup → fixture helper ready
2. Add User Story 1 → validate independently → usable MVP (extraction works)
3. Add User Story 2 → validate independently → uncertain moments are never silently buried in a long log
4. Add User Story 3 → validate independently → extracted PGNs can be saved to a file
5. Each story adds value without breaking the previous one

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- This feature has no `contracts/` artifacts (no external API/service interface) and no database entities — see data-model.md for the conceptual entities involved
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
