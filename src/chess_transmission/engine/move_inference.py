from __future__ import annotations

import chess

from chess_transmission.engine.types import (
    InferenceStatus,
    InferredMove,
    OccupancyGrid,
    occupancy_from_board,
)


def infer_move(board: chess.Board, observed: OccupancyGrid) -> InferredMove:
    """Match an observed occupancy grid against the current position's legal moves.

    A `chess.Board` already knows what piece sits on every square between confirmed
    moves, so the sensor layer only needs to report occupancy (not piece identity):
    the legal move whose resulting occupancy matches `observed` is the move played.
    """
    expected = occupancy_from_board(board)
    if observed == expected:
        return InferredMove(status=InferenceStatus.IDLE)

    matches: list[chess.Move] = []
    for candidate in board.legal_moves:
        board.push(candidate)
        resulting = occupancy_from_board(board)
        board.pop()
        if resulting == observed:
            matches.append(candidate)

    if not matches:
        return InferredMove(status=InferenceStatus.UNMATCHED)

    if len(matches) == 1:
        move = matches[0]
        return InferredMove(
            status=InferenceStatus.MATCHED, move=move, san=board.san(move)
        )

    # Multiple matches only occurs for promotion: Q/R/B/N promotions of the same
    # pawn move produce identical occupancy, so occupancy alone can't pick one.
    default = next((m for m in matches if m.promotion == chess.QUEEN), matches[0])
    return InferredMove(
        status=InferenceStatus.AMBIGUOUS_PROMOTION,
        move=default,
        san=board.san(default),
        needs_confirmation=True,
        promotion_candidates=matches,
    )
