import chess
import chess.pgn
import io

from chess_transmission.engine.game_session import GameMetadata, GameSession
from chess_transmission.engine.types import InferenceStatus, occupancy_from_board


def apply_uci_sequence(session: GameSession, moves_uci: list[str]) -> None:
    for move_uci in moves_uci:
        candidate_board = session.board.copy()
        candidate_board.push_uci(move_uci)
        observed = occupancy_from_board(candidate_board)
        result = session.observe(observed)
        assert result.status in (InferenceStatus.MATCHED, InferenceStatus.AMBIGUOUS_PROMOTION)


def test_game_session_round_trips_through_pgn():
    metadata = GameMetadata(event="Test Event", site="Test Site", white="Alice", black="Bob", round="1")
    session = GameSession(metadata)

    apply_uci_sequence(session, ["e2e4", "e7e5", "g1f3", "b8c6"])
    session.set_result("*")

    pgn = session.pgn_string()
    parsed = chess.pgn.read_game(io.StringIO(pgn))

    assert parsed.headers["Event"] == "Test Event"
    assert parsed.headers["White"] == "Alice"
    assert parsed.headers["Black"] == "Bob"
    assert parsed.headers["Round"] == "1"
    assert [move.uci() for move in parsed.mainline_moves()] == ["e2e4", "e7e5", "g1f3", "b8c6"]


def test_game_session_promotion_default_and_correction():
    session = GameSession()
    session.board.set_fen("8/P6k/8/8/8/8/7K/8 w - - 0 1")

    candidate_board = session.board.copy()
    candidate_board.push_uci("a7a8q")
    result = session.observe(occupancy_from_board(candidate_board))

    assert result.status == InferenceStatus.AMBIGUOUS_PROMOTION
    assert session.board.piece_at(chess.A8).piece_type == chess.QUEEN

    session.correct_promotion(chess.ROOK)

    assert session.board.piece_at(chess.A8).piece_type == chess.ROOK


def test_game_session_set_result_rejects_invalid_value():
    session = GameSession()
    try:
        session.set_result("nonsense")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for invalid result")
