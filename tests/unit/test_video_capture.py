import numpy as np
import pytest

from chess_transmission.vision.video_capture import VideoFileCapture
from tests.unit.video_fixtures import write_synthetic_video


def _frame(value: int) -> np.ndarray:
    return np.full((32, 32, 3), value, dtype=np.uint8)


def test_reads_frames_in_order_and_stops_cleanly_at_eof(tmp_path):
    path = tmp_path / "video.avi"
    write_synthetic_video(path, [_frame(0), _frame(40), _frame(80)], fps=10.0)

    with VideoFileCapture(path) as cap:
        first = cap.read()
        second = cap.read()
        third = cap.read()
        fourth = cap.read()

    assert first is not None and first[0, 0, 0] == 0
    assert second is not None and second[0, 0, 0] == 40
    assert third is not None and third[0, 0, 0] == 80
    assert fourth is None


def test_frames_read_and_total_frames_are_accurate(tmp_path):
    path = tmp_path / "video.avi"
    write_synthetic_video(path, [_frame(i * 10) for i in range(5)], fps=10.0)

    with VideoFileCapture(path) as cap:
        assert cap.total_frames == 5
        assert cap.frames_read == 0
        for _ in range(5):
            cap.read()
        assert cap.frames_read == 5


def test_frames_samples_at_roughly_target_fps(tmp_path):
    path = tmp_path / "video.avi"
    # 32 fps source, sampled at 8 fps -> every 4th frame.
    write_synthetic_video(path, [_frame(i) for i in range(16)], fps=32.0)

    with VideoFileCapture(path) as cap:
        sampled = [frame[0, 0, 0] for frame in cap.frames(target_fps=8.0)]

    assert sampled == [0, 4, 8, 12]


def test_open_failure_raises_clear_error(tmp_path):
    missing = tmp_path / "does-not-exist.avi"

    with pytest.raises(RuntimeError):
        with VideoFileCapture(missing):
            pass
