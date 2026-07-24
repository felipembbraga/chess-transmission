# Feature Specification: Extract PGN from a Recorded Video File

**Feature Branch**: `002-extract-pgn-video`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "add support to extract pgn from video file"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get a PGN from a recorded game video (Priority: P1)

As someone who recorded a physical chess game on video (e.g. on a phone, or a
camera that wasn't hooked up for live transmission at the time), I want to feed
that video file into the tool afterward and get the game's full PGN out, so I
don't have to manually transcribe the game move by move.

**Why this priority**: This is the entire point of the feature — without it,
a recorded-but-not-live-streamed game has no path to becoming a usable PGN at
all.

**Independent Test**: Point the tool at a real recorded video of a full game
(with a calibration matching that camera's framing already available) and
confirm the printed PGN matches the game that was actually played.

**Acceptance Scenarios**:

1. **Given** a recorded video file of a complete game and a matching
   calibration, **When** the operator runs extraction against it, **Then** the
   tool outputs a PGN whose moves match the game as played, with no operator
   interaction required while it runs.
2. **Given** a video that starts after the very first move was already made,
   **When** extraction runs, **Then** the tool reports it could not match the
   first observed position to the starting position rather than guessing.

---

### User Story 2 - See what needs manual review (Priority: P2)

As the operator, I want a clear, scannable summary of any moves the tool
couldn't confidently recognize (or where it had to guess a promotion piece),
so I know exactly which moments in a long video to double-check instead of
re-watching the whole recording.

**Why this priority**: Extraction from video is not always perfect (motion
blur, occlusion, lighting); without a summary, finding the handful of
uncertain moments in a long recording is impractical.

**Independent Test**: Run extraction against a video containing at least one
frame the system can't match and one pawn promotion, and confirm both appear
in a final review list (not just scattered across a long processing log).

**Acceptance Scenarios**:

1. **Given** a video containing a stretch of unrecognizable frames (e.g. a
   hand blocking the board), **When** extraction completes, **Then** that
   moment appears in an end-of-run list the operator can act on.
2. **Given** a video containing a pawn promotion, **When** extraction
   completes, **Then** the assumed promotion piece is called out in that same
   list, alongside the move number it affects.

---

### User Story 3 - Save the extracted PGN to a file (Priority: P3)

As the operator, I want the extracted PGN saved to a folder I've configured
(the same local-save behavior already available for live sessions), so the
result is preserved as a file without an extra manual step.

**Why this priority**: Convenient, and reuses existing behavior, but the
console output from User Story 1 already delivers the core value on its own.

**Independent Test**: Run extraction with a save folder configured and confirm
a PGN file appears there matching the console output.

**Acceptance Scenarios**:

1. **Given** a configured save folder, **When** extraction completes, **Then**
   a PGN file appears in that folder with the extracted game.
2. **Given** no save folder configured, **When** extraction completes, **Then**
   the tool still prints the PGN — saving is additive, not required.

---

### Edge Cases

- What happens when the video file doesn't exist, can't be opened, or is in an
  unsupported/corrupt format? A clear error is shown; no PGN (partial or
  otherwise) is produced.
- What happens when no calibration matching the video's camera framing exists?
  Same as any mismatched calibration: occupancy readings will be nonsensical
  and most/all frames will end up unmatched — the tool doesn't try to detect
  or auto-correct a bad calibration.
- What happens with a very long recording (e.g. an hour or more)? The operator
  can tell the tool is actively working through it rather than appearing hung.
- What happens if the video never shows a single recognizable move (e.g. the
  camera never actually captured the board)? Extraction completes with a
  PGN containing no moves, not an error.
- What happens if a video contains more than one game (e.g. several games
  recorded back to back in one file)? Out of scope for this iteration — one
  video produces one PGN, covering from the first recognized position onward.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow the operator to extract a full game's PGN from
  a single pre-recorded video file, given a calibration matching the camera
  framing that produced the video.
- **FR-002**: System MUST recognize moves from the video's frames using the
  same move-recognition behavior already used for a live camera feed (the
  video is just another source of frames, not a different recognition
  method).
- **FR-003**: System MUST run to completion without requiring operator
  interaction — a pawn promotion MUST default to queen (and be flagged for
  review per FR-005) and a frame that matches no legal move MUST be recorded
  and skipped, rather than pausing to ask the operator.
- **FR-004**: System MUST output the fully extracted PGN once processing
  completes.
- **FR-005**: System MUST produce an end-of-run summary listing every point in
  the game that needs manual review (unmatched frames, assumed promotions),
  distinct from the moment-by-moment processing output.
- **FR-006**: System MUST let the operator also save the extracted PGN to a
  configured folder, using the same local-save behavior already available for
  live sessions, independent of whether that folder is configured.
- **FR-007**: System MUST show a clear, actionable error if the video file
  can't be opened or read (missing file, unsupported/corrupt format), and MUST
  NOT produce a partial or misleading PGN in that case.
- **FR-008**: System MUST periodically report processing progress through the
  video, so the operator can tell a long-running extraction is still working.

### Key Entities

- **Source Video File**: A recorded video, supplied by the operator, showing a
  physical chess game being played. Read once per extraction run.
- **Extracted PGN**: The move-by-move game record produced from the video —
  the same kind of PGN a live session would produce.
- **Review Item**: A specific point in the extraction flagged for the
  operator's attention (an unmatched frame, or an assumed promotion), with
  enough context (e.g. move number, approximate position in the video) to
  find it again.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a clearly recorded video of a full game with correct
  calibration, the extracted PGN's moves match the game actually played, when
  checked against a known reference game.
- **SC-002**: Extracting a full game from a recorded video completes with zero
  operator prompts, regardless of video length.
- **SC-003**: 100% of moves needing manual review (unmatched frames, assumed
  promotions) appear in the end-of-run summary — none are only discoverable by
  reading the full processing log.
- **SC-004**: A missing or unreadable video file produces a clear error within
  seconds, never a silently empty or incorrect PGN.

## Assumptions

- A calibration for the camera framing/angle used in the video already exists
  (the same one-time calibration step already required for live sessions);
  this feature doesn't add a way to calibrate from within a video file.
- One video file produces one game's PGN; multi-game recordings are out of
  scope for this iteration (see Edge Cases).
- Processing doesn't need to happen in real time — a long video may take
  longer than its own runtime to process, as long as progress is visible
  (FR-008).
- Extraction is a one-shot, non-interactive run (unlike the live loop, there's
  no operator standing by to correct an ambiguous promotion in the moment) —
  consistent with how offline frame-replay already behaves in this project.
- The extracted PGN reuses the same PGN-generation and local-save logic
  already built for live sessions; no new PGN format or storage location is
  introduced.
