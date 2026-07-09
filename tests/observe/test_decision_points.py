"""T3 decision-point reconstruction (design §2 last row; prereg T3).

Hand-built traces with known co-pending sets (design §11)."""
import json

import pytest

from qsim.observe.decision_points import t3_decision_points

KEY_A = [[["M0", 0], ["M1", 0]], "messenger"]


def _write_events(path, rows):
    with open(path, "w") as f:
        for seq, (t, event_type, entity_id, payload) in enumerate(rows):
            f.write(json.dumps({
                "run_id": "r", "seq": seq, "sim_time": t,
                "event_type": event_type, "entity_id": entity_id,
                "causal_parent_id": None, "payload": payload,
            }) + "\n")


def test_decision_point_snapshots_co_pending_set_with_terminals(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (0.0, "lease.requested", "L1", {"round_id": "r1"}),
        (0.5, "lease.requested", "L2", {"round_id": "r2"}),
        (1.0, "lease.heralded", "L1", {"round_id": "r1", "fidelity_at_herald": 0.9}),
        (2.0, "lease.heralded", "L2", {"round_id": "r2", "fidelity_at_herald": 0.8}),
        (5.0, "lease.consumed", "L1", {"round_id": "r1", "fidelity_at_consumption": 0.85}),
        (6.0, "lease.expired", "L2", {"round_id": "r2"}),
    ])
    points = t3_decision_points(events)
    assert len(points) == 1
    dp = points[0]
    assert dp.sim_time == 5.0
    assert dp.consumed_lease_id == "L1"
    by_id = {l.lease_id: l for l in dp.co_pending}
    assert set(by_id) == {"L1", "L2"}
    assert by_id["L1"].heralded_at == 1.0
    assert by_id["L1"].fidelity_at_herald == 0.9
    assert by_id["L1"].terminal_type == "lease.consumed"
    assert by_id["L1"].terminal_time == 5.0
    assert by_id["L2"].terminal_type == "lease.expired"
    assert by_id["L2"].terminal_time == 6.0


def test_pool_sourced_lease_backdates_heralded_at_to_deposit(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (2.5, "pool.deposited", "P1", {"key": KEY_A, "depth": 1, "lease_id": "P1",
                                        "round_id": None, "source": "replenish"}),
        (4.0, "lease.requested", "L1", {"round_id": "r1"}),
        (4.0, "pool.withdrawn", "P1", {"key": KEY_A, "depth": 0,
                                        "pooled_lease_id": "P1", "lease_id": "L1",
                                        "round_id": "r1"}),
        (4.0, "lease.heralded", "L1", {"round_id": "r1", "fidelity_at_herald": 0.95,
                                        "source": "pool", "pooled_lease_id": "P1"}),
        (4.5, "lease.requested", "L2", {"round_id": "r2"}),
        (4.6, "lease.heralded", "L2", {"round_id": "r2", "fidelity_at_herald": 0.7}),
        (5.0, "lease.consumed", "L1", {"round_id": "r1", "fidelity_at_consumption": 0.9}),
        (5.5, "lease.consumed", "L2", {"round_id": "r2", "fidelity_at_consumption": 0.65}),
    ])
    points = t3_decision_points(events)
    assert len(points) == 2
    by_id = {l.lease_id: l for l in points[0].co_pending}
    assert by_id["L1"].heralded_at == 2.5  # deposit instant, not withdrawal
    # second decision point: only L2 remains co-pending (degenerate set)
    assert [l.lease_id for l in points[1].co_pending] == ["L2"]


def test_lease_id_reuse_across_retries_is_segmented(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (1.0, "lease.requested", "L1", {"round_id": "r1"}),
        (1.5, "lease.heralded", "L1", {"round_id": "r1", "fidelity_at_herald": 0.9}),
        (2.0, "lease.cancelled", "L1", {"round_id": "r1"}),
        # retry: same lease_id, fresh incarnation
        (3.0, "lease.requested", "L1", {"round_id": "r1"}),
        (3.5, "lease.heralded", "L1", {"round_id": "r1", "fidelity_at_herald": 0.6}),
        (4.0, "lease.consumed", "L1", {"round_id": "r1", "fidelity_at_consumption": 0.55}),
    ])
    points = t3_decision_points(events)
    assert len(points) == 1
    (lease,) = points[0].co_pending
    assert lease.incarnation == 2
    assert lease.fidelity_at_herald == 0.6
    assert lease.heralded_at == 3.5


def test_censored_lease_has_none_terminal(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (1.0, "lease.requested", "L1", {"round_id": "r1"}),
        (1.5, "lease.heralded", "L1", {"round_id": "r1", "fidelity_at_herald": 0.9}),
        (2.0, "lease.requested", "L2", {"round_id": "r2"}),
        (2.5, "lease.heralded", "L2", {"round_id": "r2", "fidelity_at_herald": 0.8}),
        (3.0, "lease.consumed", "L2", {"round_id": "r2", "fidelity_at_consumption": 0.75}),
        # L1 never reaches a terminal (horizon censoring)
    ])
    points = t3_decision_points(events)
    by_id = {l.lease_id: l for l in points[0].co_pending}
    assert by_id["L1"].terminal_type is None
    assert by_id["L1"].terminal_time is None
