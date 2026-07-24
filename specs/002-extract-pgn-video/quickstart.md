# Quickstart: Extract PGN from a Recorded Video File

Validates the feature end-to-end once implemented. See [data-model.md](./data-model.md)
for the new components and [research.md](./research.md) for the design decisions
behind each step.

## Prerequisites

```bash
uv sync
```

No real camera or recorded footage is required to validate this feature in
isolation (that's the point of research.md #7) — a synthetic video is enough.

## 1. Run the unit suite for this feature

```bash
uv run pytest tests/unit/test_video_capture.py tests/unit/test_video_file_source.py \
  tests/unit/test_review_log.py tests/unit/test_cli_extract.py -q
```

Expected: all pass, camera-free and with no checked-in video asset.

## 2. Exercise it against a real recorded video (manual, optional)

If you have an actual recorded game video and a matching calibration:

```bash
uv run chess-transmission extract path/to/game.mp4 --calibration config/calibration.json
```

Expected:
- Periodic progress lines while the video is processed (FR-008).
- The full extracted PGN printed at the end (FR-004).
- A review summary listing any unmatched frames or assumed promotions (FR-005) —
  or a clear "nothing to review" line if there were none.

## 3. Confirm it works with local saving too

```bash
uv run chess-transmission extract path/to/game.mp4 \
  --calibration config/calibration.json --pgn-save-folder games
```

Expected: same output as step 2, plus a PGN file appears under `games/` (same
behavior as `replay --pgn-save-folder`, reusing `PgnFileWriter` unchanged).

## 4. Confirm the error path for an unreadable video

```bash
uv run chess-transmission extract /path/to/nonexistent.mp4 --calibration config/calibration.json
```

Expected: one clear error message and a non-zero exit — no traceback, no partial
PGN printed (FR-007).
