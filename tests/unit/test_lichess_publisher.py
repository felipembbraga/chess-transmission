from chess_transmission.publish.lichess_broadcast import LichessBroadcastPublisher


def test_push_sends_pgn_to_configured_round(mocker):
    mock_client_cls = mocker.patch(
        "chess_transmission.publish.lichess_broadcast.berserk.Client"
    )
    mock_client = mock_client_cls.return_value

    publisher = LichessBroadcastPublisher(token="test-token", round_id="round123")
    publisher.push("1. e4 e5 *")

    mock_client.broadcasts.push_pgn_update.assert_called_once_with(
        "round123", ["1. e4 e5 *"]
    )


def test_push_retries_on_transient_failure_then_succeeds(mocker):
    mock_client_cls = mocker.patch(
        "chess_transmission.publish.lichess_broadcast.berserk.Client"
    )
    mock_client = mock_client_cls.return_value
    mock_client.broadcasts.push_pgn_update.side_effect = [RuntimeError("boom"), None]
    mocker.patch("chess_transmission.publish.lichess_broadcast.time.sleep")

    publisher = LichessBroadcastPublisher(token="test-token", round_id="round123")
    publisher.push("1. e4 *")

    assert mock_client.broadcasts.push_pgn_update.call_count == 2


def test_push_raises_after_exhausting_retries(mocker):
    mock_client_cls = mocker.patch(
        "chess_transmission.publish.lichess_broadcast.berserk.Client"
    )
    mock_client = mock_client_cls.return_value
    mock_client.broadcasts.push_pgn_update.side_effect = RuntimeError("boom")
    mocker.patch("chess_transmission.publish.lichess_broadcast.time.sleep")

    publisher = LichessBroadcastPublisher(
        token="test-token", round_id="round123", max_attempts=3
    )

    try:
        publisher.push("1. e4 *")
    except RuntimeError as exc:
        assert "round123" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")

    assert mock_client.broadcasts.push_pgn_update.call_count == 3
