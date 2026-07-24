from chess_transmission.engine.review import ReviewLog


def test_empty_log_reports_nothing_to_review():
    log = ReviewLog()

    summary = log.summary()

    assert "nothing to review" in summary.lower()


def test_records_unmatched_and_assumed_promotion_items():
    log = ReviewLog()

    log.record_unmatched(move_number=5, frame_index=120)
    log.record_assumed_promotion(move_number=8, frame_index=200, assumed_san="e8=Q")

    assert len(log.items) == 2
    assert log.items[0].kind == "unmatched"
    assert log.items[1].kind == "assumed_promotion"

    summary = log.summary()
    assert "move 5" in summary
    assert "frame 120" in summary
    assert "move 8" in summary
    assert "frame 200" in summary
    assert "e8=Q" in summary


def test_summary_handles_missing_move_number_and_frame_index():
    log = ReviewLog()

    log.record_unmatched(move_number=None, frame_index=None)

    summary = log.summary()
    assert "unknown frame" in summary
