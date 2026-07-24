# chess-transmission

Recognizes chess moves played on a physical board via an overhead camera and
transmits them live to a **Lichess Broadcast** round.

Chess.com is out of scope: it has no public live-broadcast/push API equivalent to
Lichess's. A DGT electronic board is owned and planned as a second, alternative
capture backend, but isn't implemented yet.

## How it works

A `chess.Board` already knows what piece sits on every square between confirmed
moves — so the camera only needs to report **occupancy** (occupied vs. empty) per
square, not piece identity. Every legal move from the current position is tried
against the observed occupancy grid; whichever move reproduces it is the move that
was played. This single algorithm handles disambiguation, castling, and en passant
with no special-casing. The only case it can't resolve is promotion piece choice
(queen/rook/bishop/knight all give identical occupancy), which defaults to queen and
flags a correction window.

See `CLAUDE.md` for the full architectural breakdown and phased milestone roadmap.

## Status

Milestone 1 (pure inference engine) is complete and fully unit-tested. The camera
pipeline, calibration CLI, and Lichess publisher are implemented but need a real
camera/board and a live Lichess broadcast round to verify end-to-end — see
[Verification](#verification) below.

## Requirements

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)
- A camera positioned overhead of the physical board, for the live pipeline
- At least one of: a Lichess account with a broadcast round set up and an API
  token with the `study:write` scope (for live transmission), or a local folder
  to save PGN files to (for a local-only record) — see [Setup](#setup)

## Setup

```bash
uv sync
cp config/settings.example.toml config/settings.toml   # camera index, round ID, PGN headers
cp .env.example .env                                    # LICHESS_API_TOKEN
```

Edit `config/settings.toml` and `.env` with your camera, Lichess broadcast round ID,
player names, and API token. Both files are gitignored (per-machine/secret).

Lichess transmission and local PGN saving are each optional and independent —
`config/settings.toml`'s `round_id` (plus `.env`'s `LICHESS_API_TOKEN`) and
`pgn_save_folder` can be set on their own or together, but at least one is
required. With only `pgn_save_folder` set, the tool runs with no Lichess account
at all, saving each game session to its own file in that folder.

## Usage

```bash
uv run chess-transmission calibrate   # one-time: click board corners, capture empty-board baseline
uv run chess-transmission run         # live loop: camera -> Lichess broadcast round and/or local PGN file
uv run chess-transmission replay <dir> [--pgn-save-folder <dir>]  # replay recorded frames, no camera needed
uv run chess-transmission extract <video_file> [--pgn-save-folder <dir>]  # extract a PGN from a recorded video
```

`extract` recognizes a full game from a pre-recorded video file (given a matching
calibration) and runs to completion with no operator interaction — a pawn
promotion always defaults to queen, and any frame that couldn't be recognized is
skipped, both flagged in an end-of-run review summary printed after the PGN so
you know exactly what to double-check, rather than having to scrub the whole
video. No camera is used or required.

`calibrate` must be run once per camera/board setup before `run` will work — it
asks you to click the board's 4 corners (in order: a8, h8, h1, a1, which also
encodes orientation) and then capture one frame of the **empty** board.

While `run` is live, you can type commands at its prompt for state the board can't
express on its own:

```
result 1-0       # or 0-1, 1/2-1/2 — set the game result and push it
resync           # re-push the full current PGN (e.g. after a failed push)
```

To build fixtures or debug the vision pipeline offline:

```bash
uv run python scripts/dev_capture_frames.py <out_dir>   # record frames from the camera
```

## Testing

```bash
uv run pytest tests/unit -q
```

The unit suite is fully camera-free: move inference and game/PGN state are tested
against fixtures derived by applying moves to a `chess.Board`, the occupancy
classifier is tested against synthetic images, the Lichess publisher is tested
with `berserk`'s client mocked out, and the local PGN file writer is tested against
a real (temporary) filesystem. `extract`'s whole pipeline — video decode, frame
sampling, occupancy, move inference, PGN, and the review summary — is also
covered end-to-end using tiny synthetic video files generated on the fly, with no
recorded footage checked into the repo. Nothing in `tests/unit` requires a camera,
a physical board, or network access.

## Verification

Since `calibrate` and `run` need real hardware, checking them end-to-end is manual:

1. Run `chess-transmission calibrate` against your actual camera/board and confirm
   it reports all 32 squares occupied on the starting position.
2. Play a single move and confirm the printed SAN matches what was actually played
   (try a quiet move, a capture, and a castle).
3. Play a short full game live and confirm the accumulated PGN is complete and
   replayable.
4. Run against a real (test) Lichess broadcast round and confirm moves appear live
   on the round's page as they're played on the board.

## Project layout

```
src/chess_transmission/
  board_source/   # BoardStateSource ABC + Camera-/VideoFile-BoardStateSource (DGT is a stub)
  vision/         # capture, stability/debounce, perspective warp, occupancy diff
  engine/         # move inference + GameSession (chess.Board/PGN state) + ReviewLog -- camera-free
  publish/        # LichessBroadcastPublisher (berserk) and PgnFileWriter (local save)
  cli/            # calibrate / run / replay / extract entry points
tests/unit/       # camera-free, runs in CI
tests/integration/ # needs real hardware, manual
scripts/          # dev_capture_frames.py -- record frames for fixtures/replay
```

## License

MIT — see [LICENSE](LICENSE).
