from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field

import chess

from chess_transmission.engine.types import OccupancyGrid


@dataclass
class PieceObservation:
    piece_type: chess.PieceType
    color: chess.Color


@dataclass
class BoardSnapshot:
    occupancy: OccupancyGrid
    timestamp: float
    piece_hints: dict[chess.Square, PieceObservation] = field(default_factory=dict)


class BoardStateSource(ABC):
    """Produces a sequence of board snapshots from a physical capture device.

    Downstream code (engine/, publish/) depends only on this interface, never on
    OpenCV or serial specifics, so camera- and DGT-backed sources are interchangeable.
    """

    @abstractmethod
    def calibrate(self) -> None: ...

    @abstractmethod
    def stream(self) -> Iterator[BoardSnapshot]: ...

    @abstractmethod
    def capture_once(self) -> BoardSnapshot: ...
