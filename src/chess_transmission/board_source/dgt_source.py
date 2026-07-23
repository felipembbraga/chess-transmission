from __future__ import annotations

from collections.abc import Iterator

from chess_transmission.board_source.base import BoardSnapshot, BoardStateSource


class DGTBoardStateSource(BoardStateSource):
    """Stub for a DGT electronic board backend (deferred, not part of the MVP).

    A DGT board reports full piece identity per square over serial/USB/BLE, so this
    would populate BoardSnapshot.piece_hints in full -- but engine/ and publish/ only
    consume `occupancy`, so no downstream code needs to change once this is built.
    It also doubles as a natural ground-truth oracle for validating the camera
    pipeline: run both sources against the same game and diff their inferred moves.
    """

    def calibrate(self) -> None:
        raise NotImplementedError("DGT board support is not yet implemented")

    def stream(self) -> Iterator[BoardSnapshot]:
        raise NotImplementedError("DGT board support is not yet implemented")

    def capture_once(self) -> BoardSnapshot:
        raise NotImplementedError("DGT board support is not yet implemented")
