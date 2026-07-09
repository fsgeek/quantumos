"""Co-pending lease sets at scheduling decision points (design §2; prereg T3).

Reconstruction only: this module emits RAW decision-point records
(herald instant, herald fidelity, eventual terminal from the trace).
Fidelity projection and the inversion verdict live in qsim.analysis.t3 —
the physics constants come from header.json, which views never read.

Episode segmentation: lease_ids recur across retries (prereg T3 feasibility
note), so each lease.requested opens a fresh INCARNATION of its lease_id and
all herald/terminal state is keyed by (lease_id, incarnation). Envelope seq
orders same-sim-time events; iter_events yields file order, which is seq
order, so replay order is exact.

Pool-sourced heralds (plan finding #4): lease.heralded(source="pool") fires
at WITHDRAWAL time, but the pair's true herald instant is its generation —
the sim_time of pool.deposited(lease_id=<pooled_lease_id>), which is the
herald-resolution instant (engine.py pool.deposited publication).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qsim.observe.work_accounting import iter_events

_TERMINAL_LEASE_EVENTS = frozenset({
    "lease.consumed", "lease.expired", "lease.cancelled", "lease.pool_returned",
})


@dataclass(frozen=True)
class LeaseAtDecision:
    lease_id: str
    incarnation: int
    heralded_at: float
    fidelity_at_herald: float
    terminal_type: str | None
    terminal_time: float | None


@dataclass(frozen=True)
class DecisionPoint:
    sim_time: float
    consumed_lease_id: str
    co_pending: tuple[LeaseAtDecision, ...]


def t3_decision_points(events_path: Path) -> list[DecisionPoint]:
    records = list(iter_events(events_path))

    # Pass 1: index deposits, incarnations, heralds, first terminals.
    deposit_time: dict[str, float] = {}
    incarnation: dict[str, int] = {}
    herald: dict[tuple[str, int], tuple[float, float]] = {}
    terminal: dict[tuple[str, int], tuple[str, float]] = {}
    incarnation_of_event: list[int | None] = []
    for record in records:
        event_type = record["event_type"]
        lease_id = record["entity_id"]
        if event_type == "pool.deposited":
            deposit_time[record["payload"]["lease_id"]] = record["sim_time"]
        if event_type == "lease.requested":
            incarnation[lease_id] = incarnation.get(lease_id, 0) + 1
        if event_type == "lease.heralded":
            inc = incarnation.get(lease_id, 1)
            payload = record["payload"]
            if payload.get("source") == "pool":
                heralded_at = deposit_time.get(
                    payload["pooled_lease_id"], record["sim_time"])
            else:
                heralded_at = record["sim_time"]
            herald[(lease_id, inc)] = (heralded_at, payload["fidelity_at_herald"])
        if event_type in _TERMINAL_LEASE_EVENTS:
            key = (lease_id, incarnation.get(lease_id, 1))
            terminal.setdefault(key, (event_type, record["sim_time"]))
        incarnation_of_event.append(incarnation.get(lease_id))

    # Pass 2: replay live-heralded set; snapshot at each lease.consumed.
    def _lease_record(key: tuple[str, int]) -> LeaseAtDecision:
        heralded_at, fidelity = herald[key]
        term = terminal.get(key)
        return LeaseAtDecision(
            lease_id=key[0], incarnation=key[1],
            heralded_at=heralded_at, fidelity_at_herald=fidelity,
            terminal_type=term[0] if term else None,
            terminal_time=term[1] if term else None,
        )

    live: set[tuple[str, int]] = set()
    points: list[DecisionPoint] = []
    for i, record in enumerate(records):
        event_type = record["event_type"]
        lease_id = record["entity_id"]
        inc = incarnation_of_event[i]
        if inc is None:
            continue
        key = (lease_id, inc)
        if event_type == "lease.heralded" and key in herald:
            live.add(key)
        if event_type == "lease.consumed" and key in live:
            points.append(DecisionPoint(
                sim_time=record["sim_time"],
                consumed_lease_id=lease_id,
                co_pending=tuple(sorted(
                    (_lease_record(k) for k in live),
                    key=lambda l: (l.lease_id, l.incarnation))),
            ))
        if event_type in _TERMINAL_LEASE_EVENTS:
            live.discard(key)
    return points
