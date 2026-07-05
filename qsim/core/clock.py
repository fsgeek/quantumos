"""Simulation clock (design spec §14: event-time monotonicity)."""

from __future__ import annotations


class SimClock:
    """Monotonic simulation-time clock owned by the DES engine."""

    def __init__(self) -> None:
        self._now: float = 0.0

    def now(self) -> float:
        return self._now

    def advance_to(self, t: float) -> None:
        if t < self._now:
            raise ValueError(
                f"SimClock cannot move backward: now={self._now!r}, requested={t!r}"
            )
        self._now = t
