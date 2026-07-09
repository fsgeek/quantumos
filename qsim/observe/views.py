"""Pure view functions over a run directory's events.jsonl (design spec §12).

These are strictly post-hoc computations over the trace: never a substitute
source of truth, never a place where new authoritative state is derived.
Primary metrics (goodput, logical_error_proxy) are offered-work-normalized
per §11 so an admission controller cannot trivially improve them by
rejecting work.
"""

from __future__ import annotations

import math
from pathlib import Path

from qsim.observe.work_accounting import compute_work_accounting, iter_events


def goodput(events_path: Path) -> float:
    return compute_work_accounting(events_path).goodput()


def freshness_at_consumption(events_path: Path) -> list[float]:
    return [
        record["payload"]["fidelity_at_consumption"]
        for record in iter_events(events_path)
        if record["event_type"] == "lease.consumed"
    ]


def fidelity_at_outcome(events_path: Path) -> dict[tuple[str, str], list[float]]:
    """Per-lease fidelity at round terminal, for ALL outcomes, keyed by
    (outcome, cause) so success-vs-failure and rot-vs-deadline-vs-no_herald
    distributions stay separable (design defect fix: freshness_at_consumption
    reads only lease.consumed and so is blind to the aged-out leases that CAUSED
    failures — survivor bias).

    Reads lease.outcome_fidelity events. Null fidelities (cause="no_herald" and
    unheralded leases of a deadline failure — "never existed", not "rotted to
    zero") are EXCLUDED from the returned distributions; conflating them with a
    real 0.0 would corrupt the aggregate. Keys with only null fidelities are
    therefore absent from the result."""
    distributions: dict[tuple[str, str], list[float]] = {}
    for record in iter_events(events_path):
        if record["event_type"] != "lease.outcome_fidelity":
            continue
        payload = record["payload"]
        fidelity = payload["fidelity"]
        if fidelity is None:
            continue
        key = (payload["outcome"], payload["cause"])
        distributions.setdefault(key, []).append(fidelity)
    return distributions


def decoder_backlog_series(events_path: Path) -> list[tuple[float, int]]:
    series: list[tuple[float, int]] = []
    backlog = 0
    for record in iter_events(events_path):
        event_type = record["event_type"]
        if event_type == "decoder.enqueued":
            backlog += 1
        elif event_type in ("decoder.completed", "decoder.cancelled"):
            backlog -= 1
        else:
            continue
        series.append((record["sim_time"], backlog))
    return series


def deadline_compliance(events_path: Path) -> dict[str, float]:
    wa = compute_work_accounting(events_path)
    if wa.offered == 0:
        return {
            "completed_in_deadline": 0.0,
            "completed_late": 0.0,
            "failed": 0.0,
            "dropped": 0.0,
        }
    return {
        "completed_in_deadline": wa.completed_in_deadline / wa.offered,
        "completed_late": wa.completed_late / wa.offered,
        "failed": wa.failed / wa.offered,
        "dropped": wa.dropped / wa.offered,
    }


def _path_key(path_id_payload) -> str:
    return "|".join(f"{module_id}:{port_index}" for module_id, port_index in path_id_payload)


def resource_utilization(events_path: Path) -> dict[str, float]:
    records = list(iter_events(events_path))
    if not records:
        return {}
    total_duration = max(record["sim_time"] for record in records)
    busy_time: dict[str, float] = {}
    open_acquisitions: dict[str, float] = {}
    for record in records:
        if record["event_type"] == "reservation.acquired":
            key = _path_key(record["payload"]["path_id"])
            open_acquisitions[key] = record["sim_time"]
        elif record["event_type"] == "reservation.released":
            key = _path_key(record["payload"]["path_id"])
            acquired_at = open_acquisitions.pop(key, record["sim_time"])
            busy_time[key] = busy_time.get(key, 0.0) + (record["sim_time"] - acquired_at)
    if total_duration == 0:
        return {key: 0.0 for key in busy_time}
    return {key: duration / total_duration for key, duration in busy_time.items()}


def logical_error_proxy(events_path: Path) -> float:
    wa = compute_work_accounting(events_path)
    if wa.offered == 0:
        return 0.0
    # Only scoring failures carry a success_probability (a logical-correction
    # failure); pre-scoring resource failures (capacity/endpoint) carry None and
    # are not logical errors, so they are skipped rather than counted as full
    # error weight.
    total_error_weight = sum(
        1.0 - record["payload"]["success_probability"]
        for record in iter_events(events_path)
        if record["event_type"] == "round.failed"
        and record["payload"].get("success_probability") is not None
    )
    return total_error_weight / wa.offered


# The ONLY pool.* events that move pool depth (B3, prereg T1). The two
# diagnostics are deliberately absent: pool.replenish_abandoned changes no
# inventory, and lease.pool_returned CO-OCCURS with
# pool.deposited(source="round_return") at round terminals — counting it here
# would double-count every round return (the standing annotation/terminal
# double-count lesson, applied one level down).
_POOL_DEPTH_DELTAS = {
    "pool.deposited": 1,
    "pool.withdrawn": -1,
    "pool.expired": -1,
}


def pool_depth_series(events_path: Path) -> dict[tuple, list[tuple[float, int]]]:
    """Per-(path, coherence)-key pool-depth time series, reconstructed from the
    trace ALONE (prereg T1): each depth-changing pool.* event contributes one
    (sim_time, running_depth) point. The payload's own after-op `depth` field is
    NOT read — the series is derived purely from deltas so tests can use the
    payload field as an independent self-check."""
    series: dict[tuple, list[tuple[float, int]]] = {}
    depth: dict[tuple, int] = {}
    for record in iter_events(events_path):
        delta = _POOL_DEPTH_DELTAS.get(record["event_type"])
        if delta is None:
            continue
        key = _to_hashable(record["payload"]["key"])
        depth[key] = depth.get(key, 0) + delta
        series.setdefault(key, []).append((record["sim_time"], depth[key]))
    return series


def _to_hashable(value):
    if isinstance(value, list):
        return tuple(_to_hashable(v) for v in value)
    return value


def _bin_deltas(deltas: list[tuple[float, float]], bin_s: float,
                horizon: float) -> list[float]:
    """Net delta per bin over [0, horizon). Reconstruction granularity, not
    statistics — series arithmetic proper lives in qsim.analysis.numerics
    (disclosed deviation in the 2026-07-09 plan: keeping this loop here means
    observe never imports analysis)."""
    n = max(1, math.ceil(horizon / bin_s))
    bins = [0.0] * n
    for t, d in deltas:
        i = min(int(t // bin_s), n - 1)
        bins[i] += d
    return bins


def pool_flux_series(events_path: Path, bin_s: float) -> dict[tuple, list[float]]:
    """Binned d(pool)/dt per (path, coherence) key, from depth-moving pool.*
    deltas ALONE (design §2; prereg T1 statistic). Values are rates
    (net delta / bin_s). Bin span is [0, horizon) with horizon = max
    sim_time over ALL events, so every key's series is index-aligned."""
    deltas_by_key: dict[tuple, list[tuple[float, float]]] = {}
    horizon = 0.0
    for record in iter_events(events_path):
        t = float(record["sim_time"])
        if t > horizon:
            horizon = t
        delta = _POOL_DEPTH_DELTAS.get(record["event_type"])
        if delta is None:
            continue
        key = _to_hashable(record["payload"]["key"])
        deltas_by_key.setdefault(key, []).append((t, float(delta)))
    return {
        key: [v / bin_s for v in _bin_deltas(deltas, bin_s, horizon)]
        for key, deltas in deltas_by_key.items()
    }


_BACKLOG_DELTAS = {
    "decoder.enqueued": 1.0,
    "decoder.completed": -1.0,
    "decoder.cancelled": -1.0,
}


def backlog_slope_series(events_path: Path, bin_s: float) -> list[float]:
    """Binned slope of decoder backlog (design §2; T2 statistic): net
    enqueue/complete/cancel delta per bin / bin_s — exactly the per-bin
    slope of the `decoder_backlog_series` step function."""
    deltas: list[tuple[float, float]] = []
    horizon = 0.0
    for record in iter_events(events_path):
        t = float(record["sim_time"])
        if t > horizon:
            horizon = t
        delta = _BACKLOG_DELTAS.get(record["event_type"])
        if delta is not None:
            deltas.append((t, delta))
    if not deltas:
        return []
    return [v / bin_s for v in _bin_deltas(deltas, bin_s, horizon)]


def _draw_key(record: dict):
    return (record["payload"]["stream"], _to_hashable(record["payload"]["key"]))


def shared_key_fraction(events_path_a: Path, events_path_b: Path,
                         window_s: float) -> list[tuple[float, float]]:
    windows: dict[float, tuple[set, set]] = {}
    for events_path, side in ((events_path_a, 0), (events_path_b, 1)):
        for record in iter_events(events_path):
            if record["event_type"] != "draw.sampled":
                continue
            window_start = (record["sim_time"] // window_s) * window_s
            bucket = windows.setdefault(window_start, (set(), set()))
            bucket[side].add(_draw_key(record))

    result = []
    for window_start in sorted(windows):
        keys_a, keys_b = windows[window_start]
        union = keys_a | keys_b
        if not union:
            continue
        intersection = keys_a & keys_b
        result.append((window_start, len(intersection) / len(union)))
    return result


def replenishment_latency_samples(events_path: Path) -> list[float]:
    """POOL_REPLENISH issue → pool deposit latency samples (prereg T1 lag
    definition). Issue is the replenish reservation acquisition: the ONLY
    reservation.acquired with round_id=None is the §8.2 replenish holder
    (engine.py: holder_id is the request id, lease_id "<request_id>:L");
    the matching deposit is pool.deposited(source="replenish") with the
    same lease_id. Measured from events that are NOT the ACF (prereg
    attribution rule)."""
    issued_at: dict[str, float] = {}
    samples: list[float] = []
    for record in iter_events(events_path):
        event_type = record["event_type"]
        payload = record["payload"]
        if (event_type == "reservation.acquired"
                and payload.get("round_id") is None
                and "request_id" in payload):
            issued_at[payload["lease_id"]] = record["sim_time"]
        elif (event_type == "pool.deposited"
                and payload.get("source") == "replenish"):
            t0 = issued_at.pop(payload["lease_id"], None)
            if t0 is not None:
                samples.append(record["sim_time"] - t0)
    return samples


def inter_withdrawal_times(events_path: Path) -> dict[tuple, list[float]]:
    """Per-pool-key gaps between successive pool.withdrawn events (the
    low-water oscillation cycle basis: mean gap x L, prereg attribution)."""
    last_at: dict[tuple, float] = {}
    gaps: dict[tuple, list[float]] = {}
    for record in iter_events(events_path):
        if record["event_type"] != "pool.withdrawn":
            continue
        key = _to_hashable(record["payload"]["key"])
        t = record["sim_time"]
        prev = last_at.get(key)
        if prev is not None:
            gaps.setdefault(key, []).append(t - prev)
        last_at[key] = t
    return gaps


def retry_cadence_samples(events_path: Path) -> list[float]:
    """Retry lineage cycle times. `round.retried` exists in the taxonomy but
    is NEVER published (2026-07-09 plan finding #1): a retry is a fresh
    round.arrived with incremented payload.retry_ordinal on the SAME
    entity_id (the stable round_id). A sample is the gap between consecutive
    arrivals of one lineage where the later arrival is a retry."""
    last_arrival: dict[str, float] = {}
    samples: list[float] = []
    for record in iter_events(events_path):
        if record["event_type"] != "round.arrived":
            continue
        round_id = record["entity_id"]
        t = record["sim_time"]
        prev = last_arrival.get(round_id)
        if prev is not None and record["payload"].get("retry_ordinal", 0) >= 1:
            samples.append(t - prev)
        last_arrival[round_id] = t
    return samples
