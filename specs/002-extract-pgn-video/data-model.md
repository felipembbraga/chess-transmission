# Phase 1 Data Model: Extract PGN from a Recorded Video File

No persistent storage/database entities. The "entities" below are the conceptual
objects this feature introduces or reuses, per research.md's decisions.

## Source Video File

The operator-supplied input — a path to a recorded video.

- **Fields**: `path`.
- **Validation**: existence/openability is checked at `VideoFileBoardStateSource`
  construction (or first read); failure raises a typed error caught by the CLI
  (research.md #6), never silently producing a partial result.
- **Lifecycle**: opened once per extraction run, read start-to-end, released when
  extraction finishes (successfully or on error).

## `VideoFileCapture` (new, `vision/video_capture.py`)

Mirrors `CameraCapture`'s shape, but for a file instead of a live device:

| Aspect | `CameraCapture` (existing) | `VideoFileCapture` (new) |
|--------|---------------------------|--------------------------|
| Source | camera index (int) | file path (str/Path) |
| Failed `read()` | raises (camera error) | signals end-of-file (normal stop) |
| Timing | sleeps to poll at `poll_fps` | no sleep; reads as fast as decode allows |
| Extra state | none | frame position / total frame count (for progress) |

## `VideoFileBoardStateSource` (new, `board_source/video_file_source.py`)

Implements the existing `BoardStateSource` ABC — no changes to that interface or
to `BoardSnapshot`.

- Wraps `VideoFileCapture` + the existing `StabilityDetector`, `classify_occupancy`,
  `warp_board` — identical downstream pipeline to `CameraBoardStateSource`.
- Samples frames at approximately the live pipeline's default effective rate
  (research.md #3), computed from the video's own reported FPS.
- `stream()` yields `BoardSnapshot`s until the video ends (no infinite loop, unlike
  the camera source).
- Exposes read-only progress: `frames_processed`, `total_frames` (research.md #4) —
  not part of `BoardSnapshot`, queried directly by `cli/extract.py`.
- `calibrate()` raises `NotImplementedError`, same as `CameraBoardStateSource` — a
  calibration is supplied up front (spec Assumptions), not produced from the video.

## Review Item (new, `engine/review.py`)

One entry per point in the extraction that needs the operator's attention.

| Field | Description |
|-------|--------------|
| `kind` | `"unmatched"` or `"assumed_promotion"` |
| `move_number` | the game's move number in progress when this happened, if known |
| `frame_index` | which sampled frame this corresponds to, for locating it again |
| `detail` | short human-readable note (e.g. the assumed SAN, or "no legal move matched") |

### `ReviewLog` (new, `engine/review.py`)

- Accumulates `ReviewItem`s during extraction.
- `record_unmatched(...)` / `record_assumed_promotion(...)` — one call per
  occurrence, called from `cli/extract.py` wherever it already inspects
  `InferenceStatus.UNMATCHED` / `InferenceStatus.AMBIGUOUS_PROMOTION`.
- `summary() -> str` — renders all recorded items as the end-of-run review section
  (FR-005); empty log renders a short "nothing to review" line rather than an empty
  section.

## Extracted PGN

No new entity — identical to any other session's output: `GameSession.pgn_string()`.
Printed via `cli/extract.py` (FR-004) and optionally persisted via the existing
`PgnFileWriter` (FR-006), exactly as `cli/replay.py` already does.
