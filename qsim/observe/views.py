"""Pure view functions over a run directory's events.jsonl (design spec §12).

These are strictly post-hoc computations over the trace: never a substitute
source of truth, never a place where new authoritative state is derived.
Primary metrics (goodput, logical_error_proxy) are offered-work-normalized
per §11 so an admission controller cannot trivially improve them by
rejecting work.
"""

from __future__ import annotations

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


def _to_hashable(value):
    if isinstance(value, list):
        return tuple(_to_hashable(v) for v in value)
    return value


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
