# Feature Specification: Per-Square Piece Identity Recognition

**Feature Branch**: `004-piece-identity-recognition`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "Recognize the identity (piece type and color) of whatever occupies each square on the physical board, from photos or recorded video of the board, so the system can determine a full board position directly by observation rather than relying solely on matching binary occupancy against the set of legal moves from the prior position. This is intended to supersede or augment the current occupancy-only move inference for cases where occupancy-matching alone is insufficient or ambiguous (e.g. recovering from a missed/misread move, resuming from a non-standard position, or resolving cases where multiple legal moves would produce identical occupancy). Per-square piece-identity recognition is explicitly what the project's existing Occupancy-Over-Identity principle says must not be introduced without a documented justification -- this spec exists to state that justification and scope the feature, and will require a corresponding constitution amendment before implementation planning proceeds."

## Justification (required by the project's Occupancy-Over-Identity principle)

The project's governing principles currently require that move recognition be derived only from per-square occupancy (occupied vs. empty), matched against the resulting occupancy of every legal move from the current position — and that a per-square piece-identity classifier must not be introduced "unless a concrete, documented requirement proves occupancy-matching insufficient."

Occupancy-matching is provably insufficient in three concrete situations that already exist in the deployed system today, none of which a classifier over legal moves can ever solve because they are not a legal-move-matching problem in the first place:

1. **No legal move explains the observed occupancy change.** This already happens today (surfaced as an "unmatched" item in the review log) — for example when a camera frame is skipped and two moves' worth of change land in one observation, or the board briefly shows a transient state no single legal move produces. Today the system has no way to recover the actual position other than an operator's manual `resync`; it cannot even tell the operator *what* the board actually shows, only that it doesn't match. Reading piece identity directly from the frame is the only way to reconstruct the true position without an operator physically re-entering it.
2. **Resuming from a non-standard starting position.** The system currently assumes every session starts from the standard opening array, because occupancy-matching against legal moves requires knowing the starting position and only tracks *changes* from it. There is no way today to begin tracking a game that starts from an arbitrary position (e.g. resuming a broadcast after a restart, or setting up a puzzle/study position) without the operator manually constructing the correct FEN out-of-band.
3. **Confirming promotion piece choice without operator involvement.** Occupancy-matching cannot distinguish a queen from a rook/bishop/knight promotion (they yield identical occupancy), so it currently defaults to queen and depends on the operator noticing and correcting it within a window. Reading piece identity directly at the promotion square would let this resolve correctly without depending on an operator being present and attentive at that exact moment.

This spec scopes a feature to address these three situations specifically. It does **not** propose replacing occupancy-matching as the default, everyday move-recognition mechanism — occupancy-matching remains correct, cheap, and sufficient for the overwhelming majority of moves, and Principle I's reasoning for preferring it there is unaffected. Piece-identity recognition is scoped here as a supplementary capability invoked only when occupancy-matching cannot proceed on its own.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recovering when no legal move matches what the board shows (Priority: P1)

While a game is being tracked, the system observes a board state that no legal move from the current tracked position can explain (today, this is logged as "unmatched" and the session cannot proceed automatically). The operator needs the system to instead read the actual pieces present and reconcile the tracked game state with reality, rather than stalling on that observation or requiring the operator to reconstruct the position by hand.

**Why this priority**: This is the concrete, already-occurring failure mode with no existing recovery path other than full manual intervention. It's the clearest case where occupancy-matching is provably insufficient.

**Independent Test**: Can be fully tested by feeding a frame sequence engineered so no legal move matches the occupancy change, and confirming the system identifies the actual pieces present and produces a board position consistent with what's shown, rather than logging an unresolved "unmatched" item.

**Acceptance Scenarios**:

1. **Given** a tracked game and a new board observation where no legal move explains the occupancy change, **When** the system reads piece identity for the observed board, **Then** it MUST reconcile its tracked position with the observed one and continue tracking the game, instead of leaving the observation unresolved.
2. **Given** a reconciliation has occurred, **When** the run's review summary is generated, **Then** it MUST note that a reconciliation happened and at which point, so the operator can double check it later.

---

### User Story 2 - Starting a session from a non-standard position (Priority: P2)

An operator wants to begin tracking a game that does not start from the standard opening array — for example, resuming a broadcast round after an interruption, or transmitting a pre-set puzzle/study position. Today this isn't possible without the operator manually constructing the starting position out-of-band. The operator needs to instead point the camera at the board as currently set up and have the system read that position directly to begin tracking from there.

**Why this priority**: A real, named use case (explicitly called out as the sanctioned exception in the project's constitution) and a meaningful capability gap, but less urgent than recovering from an already-occurring failure mode (Story 1).

**Independent Test**: Can be fully tested by presenting a photo of a board in a known non-standard, legal position and confirming the system begins a new tracked game from that exact position.

**Acceptance Scenarios**:

1. **Given** a photo of a board showing a legal, non-standard position, **When** the operator starts a new session from that photo, **Then** the system MUST begin tracking the game from the position shown, correctly identifying every occupied square's piece type and color.
2. **Given** a photo of a board showing an inconsistent or illegal arrangement (e.g., two white kings), **When** the operator attempts to start a session from it, **Then** the system MUST reject it with a clear explanation rather than starting from an invalid position.

---

### User Story 3 - Resolving promotion piece choice without operator involvement (Priority: P3)

When a pawn promotes, the system currently assumes queen and gives the operator a window to correct it. The operator would like the system to instead read which piece is actually on the promotion square and record the correct promotion automatically, without needing to be present and attentive at that exact moment.

**Why this priority**: A real gap, but the lowest-impact of the three — the existing default-to-queen-plus-correction-window behavior already produces a usable result and only misfires on the minority of promotions that aren't to a queen.

**Independent Test**: Can be fully tested by feeding an observation of a promotion to a non-queen piece and confirming the recorded move reflects the correct promotion piece without requiring a manual correction.

**Acceptance Scenarios**:

1. **Given** a pawn promotion where the resulting piece is a rook, bishop, or knight, **When** the system reads the promotion square's piece identity, **Then** it MUST record the move with the correct promotion piece, without depending on an operator's manual correction.

### Edge Cases

- What happens when piece-identity reading itself is uncertain about a square (e.g., ambiguous lighting, partial occlusion)? The system MUST NOT silently guess a specific piece with no way to flag or correct it — consistent with the project's existing "no silent guessing on unknowable state" principle.
- What happens when piece-identity reading disagrees with what occupancy-matching would have concluded, in a case occupancy-matching *could* otherwise resolve on its own? Since occupancy-matching remains the default/authoritative path when it succeeds, this feature MUST only be invoked in the three situations described above, not used to second-guess occupancy-matching's own successful conclusions.
- What happens if a session started from a non-standard position (Story 2) later needs to have its result set or PGN headers filled in? The existing result-setting and header behavior MUST continue to work unchanged for sessions started this way.
- What happens when the reconciliation in Story 1 itself cannot confidently identify the pieces on the board (e.g., the same low-confidence condition as the first edge case, but during a recovery attempt rather than routine tracking)? The system MUST fall back to the existing "unmatched, needs manual review" behavior rather than reconciling with low-confidence data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST be able to determine the piece type and color occupying a given square from a photo or video frame of the board.
- **FR-002**: The system MUST use this capability to reconcile its tracked game position with the observed board when no legal move from the current position explains an observed occupancy change, rather than leaving that observation unresolved.
- **FR-003**: Every reconciliation performed under FR-002 MUST be recorded and surfaced to the operator for later review (consistent with how unmatched frames and assumed promotions are already surfaced).
- **FR-004**: The system MUST allow an operator to start a new tracked session from a photo of a legal, non-standard board position, correctly identifying every occupied square's piece.
- **FR-005**: The system MUST reject starting a session from a photo showing an inconsistent or illegal piece arrangement, with a clear explanation of the problem.
- **FR-006**: The system MUST use this capability to determine the correct promotion piece at the moment of a pawn promotion, without depending on operator confirmation, while still flagging low-confidence promotion reads for review rather than silently guessing.
- **FR-007**: The system MUST NOT use piece-identity recognition to override or second-guess occupancy-matching's conclusion for moves occupancy-matching can already resolve on its own — this capability is invoked only for the specific situations in FR-002, FR-004, and FR-006.
- **FR-008**: When piece-identity recognition cannot confidently determine a square's contents, the system MUST NOT silently finalize a guess with no way to flag or correct it — it MUST fall back to existing manual-review/correction paths.
- **FR-009**: This capability MUST be testable end-to-end using synthetic, programmatically generated images, with no live camera or physical board required for the default automated test suite.

### Key Entities

- **Board Position Reading**: A full board position (piece type and color per occupied square) derived by observation from a single photo or frame, independent of any prior tracked state.
- **Reconciliation Record**: A note that the tracked game position was corrected using a Board Position Reading because no legal move matched the prior observation, surfaced through the existing review/summary mechanism.
- **Session Starting Position**: The board position a new tracked session begins from — today always the standard array; this feature allows it to instead come from a Board Position Reading.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When no legal move matches an observed occupancy change, the system successfully reconciles and continues tracking (instead of leaving the observation unresolved) in at least 90% of such cases on a representative recorded test set.
- **SC-002**: 100% of sessions started from a non-standard position via this feature begin tracking from a position that exactly matches the photographed board, when that photo is unambiguous.
- **SC-003**: 100% of illegal or inconsistent starting-position photos are rejected with an explanation, none are silently accepted.
- **SC-004**: Promotion moves are recorded with the correct piece (not defaulted to queen incorrectly) in at least 95% of promotions on a representative recorded test set, without operator correction.
- **SC-005**: 100% of reconciliations and low-confidence promotion reads appear in the operator-facing review summary.

## Assumptions

- Piece-identity recognition runs fully locally/offline, consistent with the rest of the pipeline.
- A representative set of recorded/photographed board positions is available to build and validate this capability against; collecting that dataset is in scope for implementation planning, not fixed by this spec.
- This feature depends on the same board-corner calibration already required for the rest of the system (`chess-transmission calibrate`) — it does not introduce a separate calibration step.
- Occupancy-matching remains the default, primary move-recognition mechanism for the common case; this feature is additive and only engages for the three named situations.
- This feature requires an accompanying amendment to the project's constitution (Principle I) documenting this justification before implementation planning proceeds; it is not itself the constitution amendment.
