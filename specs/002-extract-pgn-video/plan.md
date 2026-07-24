# Implementation Plan: Extract PGN from a Recorded Video File

**Branch**: `002-extract-pgn-video` (no dedicated git branch created — implemented directly on `main`) | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-extract-pgn-video/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add a new `chess-transmission extract <video_file>` command that recognizes a full
game from a pre-recorded video file, given an existing calibration. Implemented as
a new `VideoFileBoardStateSource` (mirroring `CameraBoardStateSource`) built on a
new `VideoFileCapture`, sampling frames at roughly the live pipeline's effective
rate so recognition behaves the same as it would live. Runs to completion with no
operator interaction: unmatched frames and assumed promotions are recorded in a
new `ReviewLog` and summarized at the end, alongside the printed PGN and the
existing optional local-save behavior.

## Technical Context

**Language/Version**: Python >=3.12 (existing project stack, unchanged)

**Primary Dependencies**: none new — `opencv-python` (`cv2.VideoCapture` against a
file path instead of a device index) and `python-chess`, both already dependencies

**Storage**: reads one local video file per run; no new persistent storage beyond
the existing optional local PGN save

**Testing**: `pytest`, with synthetic video fixtures built on the fly via
`cv2.VideoWriter` (lossless FFV1/`.avi`, verified working in this environment) — no real
camera, no checked-in video asset (Principle III; see research.md #7)

**Target Platform**: same host already running `chess-transmission`

**Project Type**: single project — extends the existing `chess_transmission`
package, no new project/service

**Performance Goals**: none beyond FR-008 (periodic progress output); extraction is
explicitly allowed to take longer than the video's own runtime (spec Assumptions)

**Constraints**: must not require operator interaction while running (FR-003); must
preserve the live pipeline's recognition behavior (FR-002) rather than silently
changing it by reading frames at a different effective rate; must never produce a
partial/misleading PGN if the video can't be opened (FR-007)

**Scale/Scope**: one video file → one game's PGN per run; videos may be long
(an hour or more), single game per file (spec Edge Cases)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Occupancy-Over-Identity | N/A | Feature doesn't touch occupancy detection or move inference — it's a new frame source feeding the same `infer_move`. |
| II. Hardware-Decoupled Core | PASS | New `VideoFileBoardStateSource` implements the existing `BoardStateSource` ABC unchanged; `engine/` and `publish/` are untouched. Progress reporting is kept off `BoardSnapshot` specifically to avoid leaking a file-specific concept into that shared seam (research.md #4). |
| III. Camera-Free Determinism | PASS, and stronger than usual | Unlike the live camera path, this entire feature is testable with zero real hardware — a video file is just a file, so decode → sample → stability → occupancy → inference → PGN → review log is covered end-to-end by synthetic-video tests. |
| IV. No Silent Guessing on Unknowable State | PASS | FR-003/FR-005 apply the same "no silent guessing" spirit to *this* pipeline: promotion still defaults to queen, but every instance is logged to the new `ReviewLog` and surfaced, never silently absorbed into the final PGN. |
| V. Lichess-Only Transmission, Deferred Scope | PASS | No new transmission target or hardware backend; this is another capture *source* for the same camera-based recognition approach already in scope. |

No violations — Complexity Tracking is not needed for this feature.

*Post-design re-check*: unchanged — the Phase 1 design (below) doesn't introduce
anything not already covered above.

## Project Structure

### Documentation (this feature)

```text
specs/002-extract-pgn-video/
├── plan.md              # this file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
└── quickstart.md         # Phase 1 output
```

No `contracts/` directory: same reasoning as feature 001 — this is an internal CLI
capability, not an external API/service interface.

### Source Code (repository root)

```text
src/chess_transmission/
├── vision/
│   └── video_capture.py            # NEW: VideoFileCapture (mirrors CameraCapture, file semantics)
├── board_source/
│   └── video_file_source.py        # NEW: VideoFileBoardStateSource (implements BoardStateSource)
├── engine/
│   └── review.py                   # NEW: ReviewItem, ReviewLog — camera-free, unit-testable
├── cli/
│   ├── extract.py                  # NEW: `chess-transmission extract <video_file>`
│   └── main.py                     # + `extract` subcommand dispatch
└── publish/                        # unchanged — PgnFileWriter reused as-is

tests/unit/
├── test_video_capture.py           # NEW: synthetic .avi fixtures
├── test_video_file_source.py       # NEW: synthetic video -> BoardSnapshot stream
├── test_review_log.py              # NEW: ReviewLog accumulation + summary formatting
└── test_cli_extract.py             # NEW: end-to-end against a synthetic video, incl. FR-007 error path
```

**Structure Decision**: Single existing project. Extends `vision/`, `board_source/`,
and `engine/` with one new module each (matching each layer's existing pattern —
`CameraCapture`/`CameraBoardStateSource` get file-based counterparts, `engine/`
gets a small new concern alongside `move_inference.py`/`game_session.py`), adds one
new CLI entry point, and touches `cli/main.py` only to wire the new subcommand.
`publish/` (Lichess + local-save) is reused completely unchanged.

## Complexity Tracking

*No entries — Constitution Check has no unresolved violations.*
