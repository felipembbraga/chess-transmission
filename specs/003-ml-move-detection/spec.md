# Feature Specification: ML-Based Move-Timing Detection

**Feature Branch**: `003-ml-move-detection`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "At this point of the project, we don't know when a move is playing. Let's use some model of machine learning to recognize the pieces moving"

**Scope note**: This feature is about detecting *when* a move is happening on the physical board (the operator's hand and any moved piece are still in motion, vs. the board being genuinely at rest) — the timing signal that today comes from a fixed frame-to-frame pixel-difference threshold. It does **not** change how the system decides *which* move was played (that stays occupancy-matching against legal moves, per the project's Occupancy-Over-Identity principle) and it does **not** introduce per-square piece-identity recognition.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reliable move-boundary detection during live play (Priority: P1)

An operator plays a real game on the physical board while the camera streams frames. Today, the system decides "the board is at rest" purely by checking that consecutive frames differ by less than a fixed brightness threshold across a rolling window. This is fooled by things that aren't actually a move in progress — camera auto-exposure flicker, a shadow crossing the board, a hand hovering without touching a piece — and can also be fooled the other way, staying "not at rest" too long after a move genuinely finishes if lighting is uneven. The operator needs the system to correctly recognize the moment a move has *actually* completed, so the resulting move gets captured and transmitted promptly and without spurious retriggers.

**Why this priority**: This is the trigger for every downstream step (occupancy diff, move inference, publish). Getting it wrong either delays every move or produces false triggers that feed bad occupancy grids into move inference.

**Independent Test**: Can be fully tested by replaying a recorded sequence of frames spanning a single move (hand entering, moving a piece, hand leaving, board settling) and confirming the detector reports "at rest" only once, at the correct frame, and not before.

**Acceptance Scenarios**:

1. **Given** a frame stream showing a hand actively moving a piece, **When** the detector evaluates each frame, **Then** it MUST report "not at rest" for every frame until the hand has fully left the board and the position has stabilized.
2. **Given** a frame stream showing the board fully at rest but with incidental visual noise (lighting flicker, minor camera jitter) that would cross the old fixed pixel-difference threshold, **When** the detector evaluates these frames, **Then** it MUST still report "at rest" and MUST NOT trigger a spurious move-boundary event.
3. **Given** a frame stream where a move genuinely completes, **When** the detector evaluates the frames following completion, **Then** it MUST report "at rest" within the same order-of-magnitude latency as the current threshold-based detector (see SC-002), not materially slower.

---

### User Story 2 - Consistent behavior for live camera and recorded video (Priority: P2)

The system already has two capture paths that both rely on the same stability/move-timing signal: the live camera loop and offline extraction from a recorded video file. The operator extracting a game from a saved recording needs the same move-timing behavior as someone running the live loop, so a video processed after the fact reproduces the same PGN a live run would have produced.

**Why this priority**: The project's existing architecture is explicitly built so recognition behaves identically whether frames come from a live camera or a recorded file. A move-timing model that only works for one path would break that guarantee.

**Independent Test**: Can be fully tested by feeding the same synthetic frame sequence through both the live-capture-oriented stability check and the video-file-oriented stability check and confirming both report the same move-boundary frame index.

**Acceptance Scenarios**:

1. **Given** an identical frame sequence, **When** it is processed once via the live-capture stability path and once via the recorded-video stability path, **Then** both MUST report the same "at rest" decision on the same frame.

---

### User Story 3 - Graceful behavior when the model is uncertain (Priority: P3)

Sometimes the move-timing model won't be confident either way — for example, unusual lighting the model wasn't trained on, or a hand movement that doesn't clearly resemble either "mid-move" or "at rest." The operator needs the system to still make forward progress rather than hang indefinitely, while making it possible to notice that a low-confidence decision occurred.

**Why this priority**: Lower priority than correctness of the common case, but necessary so the live loop and unattended video extraction never stall or crash on an edge case the model wasn't trained for.

**Independent Test**: Can be fully tested by feeding a frame sequence engineered to produce a low-confidence signal and confirming the system still reaches an "at rest" decision within a bounded time and records that the decision was low-confidence.

**Acceptance Scenarios**:

1. **Given** a frame sequence that produces a sustained low-confidence signal from the model, **When** a bounded maximum wait is reached, **Then** the system MUST fall back to declaring "at rest" rather than waiting indefinitely, and MUST record that this occurred.

### Edge Cases

- What happens when the model has no prior frames to compare against (the very first frames of a session)? It must not report "at rest" prematurely based on insufficient history.
- What happens when a piece is adjusted (picked up and put back on the same square) without a move actually being completed? The detector must not misreport this as a completed move boundary any more often than the current threshold-based approach does.
- What happens during unattended video extraction when a long stretch of a recorded video is ambiguous (e.g., a hand lingers over the board for an extended period)? The end-of-run review summary must be able to surface that a low-confidence "at rest" decision was made there, consistent with how unmatched frames and assumed promotions are already surfaced.
- What happens if the model's runtime dependency is missing or fails to load? The system must fail with a clear error rather than silently falling back to different behavior unannounced.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST determine, from a stream of board frames, the specific frame at which an in-progress move has completed (hand and moved piece have left the board and the position has settled), replacing or superseding today's fixed-threshold rolling-window comparison for that decision.
- **FR-002**: The system MUST continue to suppress occupancy capture for every frame it judges to still be "mid-move" (hand or piece still in motion over the board).
- **FR-003**: The move-timing decision logic MUST be shared identically between the live camera capture path and the recorded-video-file capture path, so the two produce the same result on the same input frames.
- **FR-004**: When the move-timing decision is low-confidence for longer than a bounded maximum wait, the system MUST still resolve to "at rest" rather than waiting indefinitely, and MUST record that the resolution was low-confidence.
- **FR-005**: The system MUST NOT use this capability to infer per-square piece identity (which piece is on which square) — only the binary "is the board currently at rest" signal is in scope, preserving the existing occupancy-only move-inference approach.
- **FR-006**: The move-timing detection logic MUST be testable end-to-end using synthetic, programmatically generated frame sequences, with no live camera or physical board required for the default automated test suite.
- **FR-007**: Low-confidence move-timing resolutions occurring during unattended video extraction MUST be surfaced in the existing end-of-run review summary, alongside unmatched frames and assumed promotions.
- **FR-008**: If the move-timing model's runtime dependency is unavailable or fails to load, the system MUST fail with a clear, actionable error rather than silently reverting to different behavior.

### Key Entities

- **Move-Timing Model**: Evaluates a window of recent frames and produces an "at rest" / "still moving" judgment (with a confidence signal), replacing the current fixed pixel-difference-threshold rolling-window check. Consumed identically by the live camera and recorded-video capture paths.
- **Low-Confidence Resolution Record**: A note that a move-boundary decision was made under low confidence and a bounded-wait fallback was used, surfaced through the existing review/summary mechanism.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across a representative recorded test set of full games, the move-timing detector identifies the correct move-boundary frame (within one sampled-frame tolerance) for at least 95% of moves.
- **SC-002**: The detector's false-trigger rate (declaring "at rest" while a hand or piece is still genuinely in motion) is no higher than the current threshold-based detector's on the same test set.
- **SC-003**: Time from a move's physical completion to the system declaring "at rest" does not regress by more than one polling interval compared to the current threshold-based detector.
- **SC-004**: 100% of low-confidence move-timing resolutions during a video extraction run appear in that run's end-of-run review summary.

## Assumptions

- The move-timing model runs fully locally/offline, consistent with the rest of the pipeline (no cloud dependency is introduced for this decision).
- A representative set of recorded frame sequences (drawn from existing dev-capture recordings and/or newly recorded sessions) is available to build and validate the model against; collecting that dataset is in scope for implementation planning but its exact source is not fixed by this spec.
- The existing threshold-based detector remains available in the codebase as the documented fallback behavior referenced by FR-004, rather than being deleted outright.
- "Bounded maximum wait" reuses the same order of magnitude as other existing timeout/confirmation windows in the system (e.g., the promotion-confirmation window), pending a concrete value chosen during planning.
- This feature targets the same milestone status as the rest of the live-loop pipeline (Milestone 4, per the project's phased milestone plan) and does not require a DGT board or any other new hardware.
