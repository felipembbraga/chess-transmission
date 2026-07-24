# Phase 0 Research: Extract PGN from a Recorded Video File

No `NEEDS CLARIFICATION` markers came out of the spec. The decisions below settle
how a video file becomes another frame source alongside the existing live camera,
without touching the recognition engine or the Lichess/local-save sinks.

## 1. CLI shape: new command vs. extending `replay`

**Decision**: A new `chess-transmission extract <video_file>` subcommand.

**Rationale**: `replay` already has a settled meaning — a directory of pre-extracted
PNGs. A video file is a different input shape (one file, not a directory), and
FR-001 itself frames this as "extract a PGN from a video file." A dedicated command
keeps both simple and avoids type-sniffing an argument to decide what it means.

**Alternatives considered**: Make `replay`'s positional argument accept either a
directory or a video file — rejected, adds implicit branching to a command that
already works, for marginal convenience.

## 2. Video decoding: new component vs. extending `CameraCapture`

**Decision**: A new `VideoFileCapture` (`vision/video_capture.py`), not a mode on
the existing `CameraCapture`.

**Rationale**: The two have different failure/timing semantics that don't mix
cleanly into one class:
- A live camera's failed `read()` is an error (`CameraCapture` raises). A video
  file's failed `read()` at the end of the file is normal termination, not an
  error.
- `CameraCapture.frames()` sleeps between reads to poll a live feed in real time.
  A video file should be read as fast as it decodes — real-time pacing would only
  slow down extraction for no benefit.

**Alternatives considered**: Branch inside `CameraCapture` on whether it was given
an int (camera index) or a string (file path) — rejected, mixes two different
error/timing models into one class for marginal code reuse.

## 3. Preserving "same recognition behavior as live capture" (FR-002)

**Decision**: Sample the video at roughly the same effective rate the live pipeline
polls at by default (`vision/capture.py`'s 8 fps), by skipping frames based on the
video's own reported FPS (`cv2.CAP_PROP_FPS`) — e.g. a 30 fps recording reads
roughly every 4th frame. Feed that sampled sequence through the existing
`StabilityDetector` with its current default window/threshold, unchanged.

**Rationale**: `StabilityDetector`'s window is a frame *count* (8 frames), which
the live pipeline implicitly turns into a real-time debounce window (~1s at 8 fps).
Reading every decoded frame from a high-fps recording would shrink that same
8-frame window to a fraction of a second, risking the detector locking onto a
frame while a hand is still mid-move — a materially different (and worse)
recognition behavior than FR-002 promises to preserve.

**Alternatives considered**: Process every decoded frame unmodified — rejected for
the reason above. Expose a `--sample-fps` operator flag — deferred; matching the
live default automatically already satisfies FR-002 without a new knob to explain.

## 4. Progress reporting (FR-008)

**Decision**: `VideoFileBoardStateSource` exposes read-only progress properties
(frames processed so far; total frame count, from `cv2.CAP_PROP_FRAME_COUNT`).
`cli/extract.py` polls these to print a periodic progress line (e.g. every N
processed frames).

**Rationale**: Keeps the existing `BoardStateSource`/`BoardSnapshot` contract
untouched — progress-through-a-known-length is meaningful only for a file, not a
live camera, so it doesn't belong on the shared abstraction every source has to
implement.

**Alternatives considered**: Add a `progress` field to `BoardSnapshot` — rejected,
would leak a file-specific concept into the seam `engine/`/`publish/` depend on
(Constitution Principle II).

## 5. Tracking what needs manual review (FR-005)

**Decision**: A small `ReviewLog` in `engine/` (hardware-independent, unit-testable
on its own) that `cli/extract.py` appends to whenever `GameSession.observe()`
returns `UNMATCHED` or `AMBIGUOUS_PROMOTION`. Printed as a distinct summary section
after the main PGN output.

**Rationale**: `engine/` already owns `InferenceStatus`; a review log is a natural
extension of that same layer, and keeping it separate from the CLI's I/O makes it
independently testable and reusable if `replay.py` ever wants the same summary.

**Alternatives considered**: Accumulate review items as local variables inside
`cli/extract.py` — rejected, harder to unit-test in isolation and not reusable.

## 6. Error handling for an unopenable/corrupt video (FR-007)

**Decision**: `VideoFileBoardStateSource` checks `cv2.VideoCapture.isOpened()` up
front and raises a clear, typed error, mirroring `CameraCapture`'s existing
`RuntimeError` pattern for a camera that won't open. `cli/extract.py` catches it
and reports one clean line plus a non-zero exit — never a partial PGN.

**Rationale**: Matches FR-007 directly and reuses the error-presentation
convention already established for camera-open failures.

**Alternatives considered**: Let the raw OpenCV/`cv2` exception propagate —
rejected, produces a confusing traceback instead of the clear, actionable error
FR-007 requires.

## 7. Test strategy: fully synthetic, no recorded footage anywhere

**Decision**: Build tiny synthetic video files on the fly inside tests using
`cv2.VideoWriter` with the lossless FFV1 codec into an `.avi` container — verified
working in this environment (write + read round-trip exactly, correct frame
count/FPS metadata). MJPG was tried first but is lossy and drifted pixel values
enough to break exact-value assertions; FFV1 round-trips exactly. Mirrors the
existing synthetic-frame approach already used for occupancy and CLI tests
(`test_occupancy_diff.py`, `test_replay_pgn_save_failure.py`).

**Rationale**: Per Constitution Principle III. This feature is in fact *more*
test-friendly than the live camera path: a video file is just a file, so full
end-to-end coverage (decode → sample → stability → occupancy → move inference →
PGN → review log) is achievable with zero real hardware anywhere in the suite.

**Alternatives considered**: Check in a real sample video file as a test fixture —
rejected, adds a binary asset to version control for no benefit over generating
one in-test.
