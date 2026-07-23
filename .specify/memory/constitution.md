<!--
Sync Impact Report
- Version change: 1.0.0 → 1.1.0
- Modified principles: none renamed
- Added sections:
  - Technology Constraints: added a Black formatting requirement for all Python
    files (materially expanded guidance within an existing section)
- Removed sections: none
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ (Constitution Check gate is generic,
    reads from this file — no edit needed)
  - .specify/templates/spec-template.md ✅ (no constitution-specific references)
  - .specify/templates/tasks-template.md ✅ (no constitution-specific references)
  - .specify/templates/commands/*.md — n/a, directory does not exist in this project
  - CLAUDE.md ✅ updated (Commands section now lists `uv run black .`)
  - pyproject.toml / codebase ✅ updated (black added as a dev dependency with
    target-version pinned to py312, entire src/tests/scripts tree reformatted)
- Follow-up TODOs: none
-->

# Chess Transmission Constitution

## Core Principles

### I. Occupancy-Over-Identity

Move recognition MUST be derived by matching observed per-square occupancy (occupied
vs. empty) against the resulting occupancy of every legal move from the current
`chess.Board` position — never by classifying piece type/color per square. A
per-square piece classifier (or any trained model) MUST NOT be introduced unless a
concrete, documented requirement proves occupancy-matching insufficient (e.g.,
resuming a broadcast from a non-standard position). Rationale: the board object
already knows what occupies every square between confirmed moves, so identity
classification is redundant complexity that buys no correctness for move inference
and only adds training-data and inference-latency costs.

### II. Hardware-Decoupled Core

`engine/` (move inference, game/PGN state) and `publish/` (broadcast transmission)
MUST depend only on the `BoardStateSource`/`BoardSnapshot` abstraction and MUST NOT
import OpenCV, serial/USB/BLE libraries, or any other hardware-specific API directly.
Every new capture backend (camera, DGT board, or otherwise) MUST implement
`BoardStateSource` and plug in without modifying `engine/` or `publish/`. Rationale:
this is what lets the camera path ship first while keeping the DGT board a drop-in
addition later, and what makes the core logic testable without physical hardware.

### III. Camera-Free Determinism

Move-inference and game-session logic MUST be fully unit-tested using fixtures
derived programmatically (starting FEN + move → expected occupancy/SAN via
`python-chess`), with no camera, image, or physical board involved. Vision-layer
algorithms (occupancy classification, stability detection) MUST be tested against
synthetic, programmatically generated images, not real photographs. Tests that
require a live camera or physical board MUST live under `tests/integration/` (or be
manual checks), and MUST NEVER be required for the default test run — real-hardware
accuracy is lighting- and rig-dependent and would make the suite flaky. Rationale:
correctness of the inference algorithm must be provable independent of hardware
variance, so regressions are caught before they ever reach a physical rig.

### IV. No Silent Guessing on Unknowable State

Anything that cannot be deduced from board occupancy — promotion piece choice, game
result (resignation, draw agreement, timeout) — MUST resolve to an explicit, safe
default (e.g., queen promotion) AND MUST expose a correction path to the operator
before or shortly after being treated as final. The system MUST NEVER silently
finalize an assumption about unknowable state with no way to correct it. Rationale:
these are the only points where the occupancy-matching algorithm is fundamentally
underdetermined; hiding that from the operator turns a known limitation into a
silent data-integrity bug in the transmitted game record.

### V. Lichess-Only Transmission, Deferred Scope

Live transmission targets the Lichess Broadcast API exclusively. Chess.com and any
other platform integration MUST remain out of scope until that platform exposes a
public, equivalent live-broadcast API — undocumented or unofficial integrations MUST
NOT be built as a workaround. Work on deferred items (DGT board backend, per-square
piece classification, automatic corner detection, lighting robustness, automated
broadcast-round creation) MUST NOT begin before the current milestone's vertical
slice is demonstrated end-to-end, per the milestone breakdown in the project plan.
Rationale: this project's risk is scope creep into speculative hardware/platform
support before the core recognition pipeline is proven; each deferred item is real
future work, not work to smuggle in early.

## Technology Constraints

Implementation language is Python (>=3.12), chosen for OpenCV's CV ecosystem and
`python-chess`'s legal-move/PGN/SAN handling. Lichess integration MUST use `berserk`
rather than hand-rolled HTTP calls, to avoid re-deriving endpoint/auth/header
behavior that the client already encodes correctly. Configuration MUST separate
secrets (Lichess API token, via `.env`/environment variable) from non-secret settings
(camera index, round ID, PGN metadata, thresholds, via `config/settings.toml`) and
from per-machine calibration data (`config/calibration.json`) — none of the latter
two are committed to version control. New dependencies for functionality already
achievable with the existing stack (e.g., a full ML framework before Principle I's
bar is met) require explicit justification. Every Python file MUST be formatted with
Black using its default settings before being committed; run `uv run black .` (or
equivalent) as part of finishing any change that touches `.py` files, so formatting
is never a matter of individual style or a source of unrelated review noise.

## Development Workflow

Work proceeds by the phased, independently demoable milestones defined in the
project's implementation plan (skeleton → pure inference engine → static
calibration/occupancy read → single-move vertical slice → continuous live loop →
Lichess push). Each milestone's stated demo/verification step MUST pass before
starting the next. Automated tests (`uv run pytest tests/unit`) MUST pass camera-free
before any change is considered complete; hardware-dependent verification steps are
manual and are called out explicitly rather than assumed. Constitution compliance
(Principles I–V) MUST be checked at planning time for any change touching capture,
inference, or publishing — a violation must be justified in writing (why simpler
compliant options were rejected) or the design must be revised.

## Governance

This constitution supersedes ad hoc practice for this project. Amendments require:
updating this file, incrementing the version per the policy below, and recording the
change in a Sync Impact Report comment at the top of this file. Versioning follows
semantic versioning: MAJOR for backward-incompatible principle removals or
redefinitions, MINOR for new principles or materially expanded guidance, PATCH for
wording/clarification fixes with no rule change. Every plan MUST pass through a
Constitution Check gate (see `.specify/templates/plan-template.md`) before
implementation begins; any complexity that conflicts with a principle must be
justified there or removed. Compliance is reviewed whenever a plan or spec is
produced for a feature touching capture, inference, or publishing.

**Version**: 1.1.0 | **Ratified**: 2026-07-23 | **Last Amended**: 2026-07-23
