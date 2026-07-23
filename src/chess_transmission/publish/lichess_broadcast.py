from __future__ import annotations

import time

import berserk


class LichessBroadcastPublisher:
    """Pushes PGN updates to a Lichess broadcast round.

    Requires an API token with the `study:write` scope (broadcasts share studies'
    infrastructure). Lichess matches games in the round by player name, so the PGN's
    White/Black headers must match the names already configured for that round.
    """

    def __init__(
        self,
        token: str,
        round_id: str,
        max_attempts: int = 3,
        retry_delay_seconds: float = 1.0,
    ):
        session = berserk.TokenSession(token)
        self._client = berserk.Client(session=session)
        self._round_id = round_id
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds

    def push(self, pgn: str) -> None:
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                self._client.broadcasts.push_pgn_update(self._round_id, [pgn])
                return
            except Exception as exc:  # retry on any transient failure
                last_error = exc
                if attempt < self._max_attempts:
                    time.sleep(self._retry_delay_seconds)
        raise RuntimeError(
            f"failed to push PGN to broadcast round {self._round_id} "
            f"after {self._max_attempts} attempts"
        ) from last_error
