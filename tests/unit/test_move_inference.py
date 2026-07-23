import chess
import pytest

from chess_transmission.engine.move_inference import infer_move
from chess_transmission.engine.types import InferenceStatus, occupancy_from_board


def occupancy_after(fen: str, move_uci: str) -> dict:
    board = chess.Board(fen)
    board.push_uci(move_uci)
    return occupancy_from_board(board)


@pytest.mark.parametrize(
    "fen, move_uci, expected_san",
    [
        (chess.STARTING_FEN, "e2e4", "e4"),
        (chess.STARTING_FEN, "g1f3", "Nf3"),
        (
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            "f1c4",
            "Bc4",
        ),
        ("4k3/8/8/8/8/8/8/N1N1K3 w - - 0 1", "a1b3", "Nab3"),
        ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1g1", "O-O"),
        ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1c1", "O-O-O"),
        (
            "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3",
            "e5f6",
            "exf6",
        ),
    ],
)
def test_infer_move_matches_expected_san(fen, move_uci, expected_san):
    board = chess.Board(fen)
    observed = occupancy_after(fen, move_uci)

    result = infer_move(board, observed)

    assert result.status == InferenceStatus.MATCHED
    assert result.san == expected_san


def test_infer_move_idle_when_occupancy_unchanged():
    board = chess.Board()

    result = infer_move(board, occupancy_from_board(board))

    assert result.status == InferenceStatus.IDLE
    assert result.move is None


def test_infer_move_promotion_is_ambiguous_with_queen_default():
    fen = "8/P6k/8/8/8/8/7K/8 w - - 0 1"
    board = chess.Board(fen)
    observed = occupancy_after(fen, "a7a8q")

    result = infer_move(board, observed)

    assert result.status == InferenceStatus.AMBIGUOUS_PROMOTION
    assert result.needs_confirmation is True
    assert result.move.promotion == chess.QUEEN
    promotions = {m.promotion for m in result.promotion_candidates}
    assert promotions == {chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT}


def test_infer_move_unmatched_for_garbage_occupancy():
    board = chess.Board()
    observed = occupancy_from_board(board)
    observed[chess.E4] = True
    observed[chess.A6] = True

    result = infer_move(board, observed)

    assert result.status == InferenceStatus.UNMATCHED
    assert result.move is None
