# Phase 0 Research: Save PGN to a Configured Folder

No open `NEEDS CLARIFICATION` markers came out of the spec — this feature is small
and its shape is already fixed by the existing `config.py`/`publish/` conventions.
The research below is the set of concrete design decisions that Phase 1 depends on.

## 1. Where does the folder-path setting live?

**Decision**: `config/settings.toml`, a new optional `pgn_save_folder` key. Absent
means the feature is off.

**Rationale**: The constitution's Technology Constraints section already draws the
line: secrets go in `.env`, non-secret settings go in `config/settings.toml`. A
folder path is not a secret.

**Alternatives considered**: `.env` — rejected, would mix a non-secret setting into
the secrets file against the project's existing convention. A dedicated new config
file — rejected, unnecessary; `settings.toml` already holds exactly this kind of
setting (camera index, round id, thresholds).

## 2. Must Lichess configuration become optional?

**Decision**: Yes. `Settings.lichess_token` and `Settings.round_id` become
`str | None`; `Settings.load()` no longer hard-requires `LICHESS_API_TOKEN`.
`cli/run.py` / `cli/replay.py` construct `LichessBroadcastPublisher` only when both
are present, and construct the new PGN file writer only when `pgn_save_folder` is
set. If neither is configured, `Settings.load()` raises a clear error (there would
be nothing for the tool to do).

**Rationale**: FR-001 and FR-008 require local saving to work "independent of
whether Lichess transmission is configured." Today `Settings.load()` crashes
immediately if `LICHESS_API_TOKEN` is absent — before a game even starts — so the
only way to honor that requirement literally is to stop hard-requiring the token.

**Alternatives considered**: Keep the token mandatory and only make *push failures*
non-fatal — rejected, this still fails the "is configured" case in FR-008 outright,
since the process won't even reach the point of playing a game without a token set.

## 3. Filename scheme for one distinct file per session

**Decision**: `{start-timestamp:%Y%m%d-%H%M%S}_{white-slug}-vs-{black-slug}.pgn`.
The timestamp is captured once, at session start, and reused for every save within
that session (so the file is updated in place, not renamed each time). Player names
are slugified (non-alphanumeric characters replaced with `-`) for filesystem safety.

**Rationale**: Satisfies FR-005 using data already on hand (`GameMetadata` plus
wall-clock start time), is human-readable, and sorts chronologically in a file
listing.

**Alternatives considered**: Random/UUID filename — rejected, not human-readable
and harder to locate a specific game later. Sequential counter — rejected, requires
tracking state across runs/scanning the folder, more complexity for no benefit over
a timestamp given games don't start concurrently in practice.

## 4. Error handling for save failures

**Decision**: The writer raises a dedicated `PgnSaveError` naming the failed path.
Callers (`cli/run.py`, `cli/replay.py`) catch it and print a warning, then continue
the loop — the same pattern already used around `LichessBroadcastPublisher.push()`.

**Rationale**: Satisfies FR-007 ("surface a clear, actionable error... without
interrupting move recognition or the Lichess push"). Reusing the existing
publisher's error-handling shape keeps the two output sinks symmetric and keeps the
decision of how to react in the caller, not buried in the writer.

**Alternatives considered**: Swallow errors internally and just log — rejected,
that's exactly the silent-failure outcome User Story 3 exists to prevent. Crash the
process — rejected, explicitly against FR-007.

## 5. Does `cli/replay.py` get this feature too?

**Decision**: Yes — identical wiring to `cli/run.py`. Both build a `GameSession`
and both benefit from a local save with no extra design work.

**Rationale**: Consistent behavior; nothing in the spec ties this feature to the
camera capture path specifically, and leaving `replay` without it would be an
arbitrary gap.

**Alternatives considered**: `run.py` only — rejected, replay-derived sessions
would lack the same durability for no real savings.
