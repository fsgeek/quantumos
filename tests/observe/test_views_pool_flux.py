"""Flux + backlog-slope views: delta-derived, payload depth reserved as
self-check (design §2)."""
import json

import pytest

from qsim.observe.views import backlog_slope_series, pool_flux_series

KEY_A = [[["M0", 0], ["M1", 0]], "messenger"]
KEY_B = [[["M1", 0], ["M2", 0]], "messenger"]


def _write_events(path, rows):
    with open(path, "w") as f:
        for seq, (t, event_type, payload) in enumerate(rows):
            f.write(json.dumps({
                "run_id": "r", "seq": seq, "sim_time": t,
                "event_type": event_type, "entity_id": f"e{seq}",
                "causal_parent_id": None, "payload": payload,
            }) + "\n")


def test_pool_flux_bins_net_deltas_per_key_as_rate(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (0.05, "pool.deposited", {"key": KEY_A, "depth": 1}),
        (0.15, "pool.deposited", {"key": KEY_A, "depth": 2}),
        (0.18, "pool.deposited", {"key": KEY_B, "depth": 1}),
        (0.25, "pool.withdrawn", {"key": KEY_A, "depth": 1}),
        (0.27, "pool.expired", {"key": KEY_A, "depth": 0}),
        (0.29, "lease.pool_returned", {"key": KEY_A}),  # annotation: must NOT count
    ])
    flux = pool_flux_series(events, bin_s=0.1)
    key_a = (((("M0", 0), ("M1", 0))), "messenger")
    key_b = (((("M1", 0), ("M2", 0))), "messenger")
    assert flux[key_a] == pytest.approx([10.0, 10.0, -20.0])
    assert flux[key_b] == pytest.approx([0.0, 10.0, 0.0])


def test_pool_flux_empty_trace_is_empty(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text("")
    assert pool_flux_series(events, bin_s=0.1) == {}


def test_backlog_slope_bins_enqueue_complete_deltas(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (0.05, "decoder.enqueued", {}),
        (0.12, "decoder.enqueued", {}),
        (0.28, "decoder.completed", {}),
    ])
    assert backlog_slope_series(events, bin_s=0.1) == pytest.approx([10.0, 10.0, -10.0])


def test_backlog_slope_counts_cancelled_as_exit(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (0.02, "decoder.enqueued", {}),
        (0.05, "decoder.cancelled", {}),
    ])
    assert backlog_slope_series(events, bin_s=0.1) == pytest.approx([0.0])
