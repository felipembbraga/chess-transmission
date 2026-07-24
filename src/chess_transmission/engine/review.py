from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReviewItem:
    kind: str  # "unmatched" or "assumed_promotion"
    move_number: int | None
    frame_index: int | None
    detail: str


class ReviewLog:
    """Accumulates points in an extraction that need the operator's manual
    review -- unmatched frames and assumed promotions -- so they can be
    surfaced as one scannable summary instead of scattered through a long
    per-frame processing log."""

    def __init__(self) -> None:
        self._items: list[ReviewItem] = []

    def record_unmatched(
        self, move_number: int | None, frame_index: int | None
    ) -> None:
        self._items.append(
            ReviewItem(
                kind="unmatched",
                move_number=move_number,
                frame_index=frame_index,
                detail="no legal move matched the observed position",
            )
        )

    def record_assumed_promotion(
        self, move_number: int | None, frame_index: int | None, assumed_san: str
    ) -> None:
        self._items.append(
            ReviewItem(
                kind="assumed_promotion",
                move_number=move_number,
                frame_index=frame_index,
                detail=f"assumed {assumed_san} (queen)",
            )
        )

    @property
    def items(self) -> list[ReviewItem]:
        return list(self._items)

    def summary(self) -> str:
        if not self._items:
            return "Review: nothing to review -- every frame was recognized with confidence."
        lines = ["Review: the following need a manual look:"]
        for item in self._items:
            location = (
                f"frame {item.frame_index}"
                if item.frame_index is not None
                else "unknown frame"
            )
            if item.move_number is not None:
                location = f"move {item.move_number}, {location}"
            lines.append(f"  - [{item.kind}] {location}: {item.detail}")
        return "\n".join(lines)
