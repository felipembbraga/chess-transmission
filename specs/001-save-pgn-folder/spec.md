# Feature Specification: Save PGN to a Configured Folder

**Feature Branch**: `001-save-pgn-folder`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "add save pgn file in a setted folder"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Local PGN record of the live game (Priority: P1)

As the operator running a live broadcast session, I want the current game's PGN
automatically written to a folder I've configured, so that I have a local, durable
record of the game that doesn't depend on the Lichess push succeeding or the
network being available.

**Why this priority**: This is the core value of the feature — without it, the only
record of a game is what successfully reached Lichess. A local copy is the safety
net the rest of the feature exists for.

**Independent Test**: Configure a save folder, play a short sequence of moves
through the pipeline, and confirm a PGN file appears in that folder whose content
matches the game played — including with the network/Lichess push disabled or
failing.

**Acceptance Scenarios**:

1. **Given** a configured save folder and an active game session, **When** a move
   is recognized and applied, **Then** the PGN file in that folder is updated to
   reflect the game's current state (all moves so far).
2. **Given** a configured save folder, **When** the Lichess push fails or is
   unreachable, **Then** the local PGN file is still written/updated with the
   latest move.
3. **Given** a promotion default was corrected after the fact, **When** the
   correction is applied, **Then** the local PGN file reflects the corrected move,
   not the original queen-default guess.

---

### User Story 2 - Distinct file per game session (Priority: P2)

As the operator, I want each game session saved to its own distinctly named file,
so that starting a new game (or restarting the tool) never silently overwrites the
record of a previous game.

**Why this priority**: Without this, a second session could clobber the first
game's saved file, defeating the purpose of having a durable local record.

**Independent Test**: Run two separate game sessions against the same configured
folder and confirm two distinct files exist afterward, each containing only its
own game's moves.

**Acceptance Scenarios**:

1. **Given** a configured save folder already containing a PGN file from a prior
   session, **When** a new game session starts, **Then** a new file is created
   without modifying the existing one.
2. **Given** the configured folder does not yet exist, **When** a game session
   starts, **Then** the folder is created automatically.

---

### User Story 3 - Clear failure signal when saving fails (Priority: P3)

As the operator, I want to be told clearly if the local PGN save fails, so I don't
unknowingly lose the local record while assuming it's being kept.

**Why this priority**: Lower priority than the save itself working, but silent data
loss undermines the whole point of having a local safety net.

**Independent Test**: Point the configured folder at a location the process cannot
write to (e.g., permission denied) and confirm the operator sees a clear error
message while the live session continues running rather than crashing.

**Acceptance Scenarios**:

1. **Given** a configured save folder the process cannot write to, **When** a move
   is applied, **Then** an error is shown to the operator identifying the save
   failure, and move recognition/Lichess push continue unaffected.

---

### Edge Cases

- What happens when the configured folder does not exist yet? System creates it.
- What happens when the disk is full or the folder becomes unwritable mid-session?
  Operator is shown a clear error (User Story 3); the live session keeps running.
- What happens when two game sessions are started at (nearly) the same time
  against the same folder? Each session's filename must not collide with another
  session started in the same run of the tool.
- What happens when the game has zero moves yet (session just started)? A file
  with just the PGN headers (no moves) is an acceptable initial state.
- What happens when the result is set (e.g., resignation) after moves have already
  been saved? The saved file is updated to include the result.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow the operator to configure a folder path where PGN
  files are saved, independent of whether Lichess transmission is configured.
- **FR-002**: System MUST write the current game's full PGN to a file in the
  configured folder each time a move is recognized and applied to the game session.
- **FR-003**: System MUST update the file in place so its content always reflects
  the game's current full move list, rather than appending duplicate or partial
  records.
- **FR-004**: System MUST update the saved file when the game result is set, so the
  final saved PGN includes the result.
- **FR-005**: System MUST generate a distinct filename per game session so that
  separate sessions do not overwrite each other's saved files.
- **FR-006**: System MUST create the configured folder automatically if it does not
  already exist.
- **FR-007**: System MUST surface a clear, actionable error to the operator if the
  PGN file cannot be written (e.g., permission denied, disk full), without
  interrupting move recognition or the Lichess push.
- **FR-008**: Local saving MUST function whether or not the Lichess push succeeds,
  is configured, or is reachable — the two are independent outcomes of the same
  recognized move.

### Key Entities

- **Saved PGN File**: A file on disk holding one game session's PGN record.
  Reflects the game's headers and full move list as currently known, and is
  updated in place as the game progresses.
- **Configured Save Folder**: A directory path, set by the operator, under which
  saved PGN files are written. Created automatically if missing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After each recognized move, the saved PGN file's content matches the
  game's current state within 1 second.
- **SC-002**: 100% of game sessions produce a saved PGN file that a standard chess
  application can open and read without errors.
- **SC-003**: Running multiple game sessions against the same configured folder
  results in zero unintended overwrites of a previous session's saved file.
- **SC-004**: When the save folder is unwritable, the operator sees an error
  message and the live session continues recognizing moves and (if configured)
  pushing to Lichess without interruption, in 100% of observed cases.

## Assumptions

- One saved PGN file corresponds to one game session (one run of the live loop, or
  one replay); the feature does not need to merge or resume a file across process
  restarts for this iteration.
- The filename is generated automatically (e.g., from session start time and/or
  configured event/player metadata already used for PGN headers) rather than
  requiring the operator to name each file manually.
- The configured folder is a local filesystem path on the machine running the
  tool; saving to a remote/network location is out of scope for this feature.
- This feature reuses the PGN string already produced by the existing game session
  component — no new PGN-generation logic is required, only where/when it's
  persisted to disk.
