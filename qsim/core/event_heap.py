"""Event heap for the DES core: (time, seq) ordering (design spec §14)."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field


@dataclass(order=True)
class HeapEntry:
    time: float
    seq: int
    payload: object = field(compare=False)


class EventHeap:
    """Min-heap of (time, seq)-ordered entries.

    seq is assigned in push() call order and used as the tiebreak for
    equal-time entries, so events scheduled at the same simulated instant
    are popped in the order they were scheduled (FIFO), never in an order
    that depends on heap internal structure or payload identity/orderability.
    """

    def __init__(self) -> None:
        self._heap: list[HeapEntry] = []
        self._next_seq: int = 0

    def push(self, time: float, payload: object) -> int:
        seq = self._next_seq
        self._next_seq += 1
        heapq.heappush(self._heap, HeapEntry(time=time, seq=seq, payload=payload))
        return seq

    def pop(self) -> HeapEntry | None:
        if not self._heap:
            return None
        return heapq.heappop(self._heap)

    def __len__(self) -> int:
        return len(self._heap)
