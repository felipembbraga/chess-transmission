from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

import chess

OccupancyGrid = dict[chess.Square, bool]


def occupancy_from_board(board: chess.Board) -> OccupancyGrid:
    return {square: board.piece_at(square) is not None for square in chess.SQUARES}


class InferenceStatus(Enum):
    IDLE = auto()
    MATCHED = auto()
    AMBIGUOUS_PROMOTION = auto()
    UNMATCHED = auto()


@dataclass
class InferredMove:
    status: InferenceStatus
    move: chess.Move | None = None
    san: str | None = None
    needs_confirmation: bool = False
    promotion_candidates: list[chess.Move] = field(default_factory=list)
