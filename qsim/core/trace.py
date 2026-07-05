"""Trace bus: every state transition is a typed, causally-linked event
(design spec §12: "the trace is the deliverable").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from qsim.core.clock import SimClock

EventId = tuple[str, int]


@dataclass(frozen=True)
class Event:
    run_id: str
    seq: int
    sim_time: float
    event_type: str
    entity_id: str
    causal_parent_id: EventId | None
    payload: dict


EVENT_TYPES = [
    # lease lifecycle (§5)
    "lease.requested", "lease.heralded", "lease.consumed", "lease.expired", "lease.cancelled",
    "lease.pool_returned",  # pregen return path, accounted separately per §5/§11
    # per-lease fidelity at EVERY round terminal (success AND failure), tagged by
    # cause so failure sub-types stay separable. payload: {round_id, outcome:
    # "success"|"failure", cause, fidelity: float|null (null == never heralded,
    # NOT rotted to zero)}
    "lease.outcome_fidelity",
    # round lifecycle (§5, §11)
    "round.arrived", "round.admitted", "round.deferred", "round.dropped",
    "round.completed_in_deadline", "round.completed_late", "round.failed", "round.retried",
    # switch reservation lifecycle (§7)
    "reservation.acquired", "reservation.configuring", "reservation.active", "reservation.released",
    # decoder job lifecycle (§5)
    "decoder.enqueued", "decoder.dequeued", "decoder.completed", "decoder.cancelled",
    # randomness (§10) — every draw is itself a trace event
    "draw.sampled",  # payload: {stream, key, uniform}
]

_EVENT_TYPE_SET = frozenset(EVENT_TYPES)


class TraceBus:
    """Publishes trace events and fans them out to subscribers.

    Construction takes the run's identity and the shared SimClock so that
    publish()'s frozen signature (event_type, entity_id, causal_parent_id,
    payload) -> EventId never needs an explicit time argument: sim_time is
    always the engine's current clock reading at publish time.
    """

    def __init__(self, run_id: str, clock: SimClock) -> None:
        self._run_id = run_id
        self._clock = clock
        self._next_seq = 0
        self._subscribers: list[Callable[[Event], None]] = []

    def publish(self, event_type: str, entity_id: str,
                causal_parent_id: EventId | None, payload: dict) -> EventId:
        if event_type not in _EVENT_TYPE_SET:
            raise ValueError(f"unknown event_type: {event_type!r}")

        seq = self._next_seq
        self._next_seq += 1
        event = Event(
            run_id=self._run_id,
            seq=seq,
            sim_time=self._clock.now(),
            event_type=event_type,
            entity_id=entity_id,
            causal_parent_id=causal_parent_id,
            payload=payload,
        )
        for subscriber in self._subscribers:
            subscriber(event)
        return (self._run_id, seq)

    def subscribe(self, fn: Callable[[Event], None]) -> None:
        self._subscribers.append(fn)
