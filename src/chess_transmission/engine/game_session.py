from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import chess
import chess.pgn

from chess_transmission.engine.move_inference import infer_move
from chess_transmission.engine.types import InferenceStatus, InferredMove, OccupancyGrid

VALID_RESULTS = {"1-0", "0-1", "1/2-1/2", "*"}


@dataclass
class GameMetadata:
    event: str = "Live Broadcast"
    site: str = "?"
    white: str = "White"
    black: str = "Black"
    round: str = "-"


class GameSession:
    """Tracks a single game's board state and PGN as moves are observed."""

    def __init__(self, metadata: GameMetadata | None = None):
        self.metadata = metadata or GameMetadata()
        self.board = chess.Board()
        self.game = chess.pgn.Game()
        self.game.headers["Event"] = self.metadata.event
        self.game.headers["Site"] = self.metadata.site
        self.game.headers["Date"] = dt.date.today().strftime("%Y.%m.%d")
        self.game.headers["Round"] = self.metadata.round
        self.game.headers["White"] = self.metadata.white
        self.game.headers["Black"] = self.metadata.black
        self._node = self.game

    def observe(self, occupancy: OccupancyGrid) -> InferredMove:
        """Feed a stable observed occupancy grid; applies the move if one is found."""
        inferred = infer_move(self.board, occupancy)
        if inferred.move is not None:
            self._apply(inferred.move)
        return inferred

    def correct_promotion(self, piece_type: chess.PieceType) -> None:
        """Replace the last move's (queen-default) promotion with the correct piece."""
        last_move = self.board.pop()
        self._node = self._node.parent
        self._apply(
            chess.Move(last_move.from_square, last_move.to_square, promotion=piece_type)
        )

    def force_san(self, san: str) -> None:
        """Manually apply a move the inference engine couldn't recognize."""
        self._apply(self.board.parse_san(san))

    def set_result(self, result: str) -> None:
        if result not in VALID_RESULTS:
            raise ValueError(
                f"invalid result: {result!r}, expected one of {VALID_RESULTS}"
            )
        self.game.headers["Result"] = result

    def pgn_string(self) -> str:
        exporter = chess.pgn.StringExporter(
            headers=True, variations=False, comments=False
        )
        return self.game.accept(exporter)

    def _apply(self, move: chess.Move) -> None:
        self.board.push(move)
        self._node = self._node.add_variation(move)
