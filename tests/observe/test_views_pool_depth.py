"""pool_depth_series: per-(path, coherence)-key pool depth reconstructed from
the trace ALONE (prereg 2026-07-06 T1: "the depth series must be derivable
from the trace alone, per the capture-everything norm").

Only the three depth-changing pool.* annotations move the series
(deposit +1, withdraw -1, expire -1); lease.pool_returned co-occurs with
pool.deposited(source="round_return") at round terminals and must be IGNORED
here or every round return double-counts (the standing annotation/terminal
lesson, one level down).
"""
from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.views import pool_depth_series

_KEY_A = [[["M0", 0], ["M1", 0]], "messenger"]
_KEY_B = [[["M2", 0], ["M3", 0]], "messenger"]


def _pool_event(seq, sim_time, event_type, key, depth, payload_extra=None):
    payload = {"key": key, "depth": depth}
    payload.update(payload_extra or {})
    return Event(run_id="r", seq=seq, sim_time=sim_time, event_type=event_type,
                 entity_id=f"lease-{seq}", causal_parent_id=None, payload=payload)


def _seed_events(tmp_path, events):
    writer = RunDirWriter(root=tmp_path, run_id="run-pool-depth")
    for e in events:
        writer.append_event(e)
    return writer.events_path


def _hashable(key):
    return tuple(
        tuple(tuple(p) for p in part) if isinstance(part, list) else part
        for part in key
    )


def test_depth_series_reconstructs_per_key_and_matches_payload_depth(tmp_path):
    events = [
        _pool_event(0, 0.0, "pool.deposited", _KEY_A, 1, {"source": "replenish"}),
        _pool_event(1, 1.0, "pool.deposited", _KEY_A, 2, {"source": "round_return"}),
        _pool_event(2, 1.5, "pool.deposited", _KEY_B, 1, {"source": "replenish"}),
        _pool_event(3, 2.0, "pool.withdrawn", _KEY_A, 1),
        _pool_event(4, 3.0, "pool.expired", _KEY_A, 0),
        _pool_event(5, 4.0, "pool.deposited", _KEY_A, 1, {"source": "replenish"}),
    ]
    path = _seed_events(tmp_path, events)

    series = pool_depth_series(path)

    key_a, key_b = _hashable(_KEY_A), _hashable(_KEY_B)
    assert set(series) == {key_a, key_b}
    assert series[key_a] == [(0.0, 1), (1.0, 2), (2.0, 1), (3.0, 0), (4.0, 1)]
    assert series[key_b] == [(1.5, 1)]
    # The series is self-checking: the running depth reconstructed from deltas
    # alone must equal each event's payload depth field.
    for events_for_key, reconstructed in ((events[:2] + events[3:], series[key_a]),):
        payload_depths = [e.payload["depth"] for e in events_for_key]
        assert [depth for _, depth in reconstructed] == payload_depths
    # And it never goes negative.
    for per_key in series.values():
        assert all(depth >= 0 for _, depth in per_key)


def test_lease_pool_returned_and_replenish_abandoned_do_not_move_depth(tmp_path):
    events = [
        _pool_event(0, 0.0, "pool.deposited", _KEY_A, 1, {"source": "round_return"}),
        # co-occurring §5/§11 counter event — a diagnostic, not a depth delta
        Event(run_id="r", seq=1, sim_time=0.0, event_type="lease.pool_returned",
              entity_id="lease-x", causal_parent_id=None, payload={"round_id": "r1"}),
        _pool_event(2, 1.0, "pool.replenish_abandoned", _KEY_A, 1,
                    {"request_id": "pool-1", "reason": "herald_failed"}),
    ]
    path = _seed_events(tmp_path, events)

    series = pool_depth_series(path)

    assert series[_hashable(_KEY_A)] == [(0.0, 1)]


def test_empty_trace_yields_empty_series(tmp_path):
    path = _seed_events(tmp_path, [])
    assert pool_depth_series(path) == {}
