"""Lineage views: replenish issue→deposit latency, withdrawal gaps, retry
cadence (design §2 with plan finding #1: round.retried is taxonomy-only,
never published — retries are fresh round.arrived with retry_ordinal)."""
import json

import pytest

from qsim.observe.views import (
    inter_withdrawal_times,
    replenishment_latency_samples,
    retry_cadence_samples,
)

KEY_A = [[["M0", 0], ["M1", 0]], "messenger"]


def _write_events(path, rows):
    with open(path, "w") as f:
        for seq, (t, event_type, entity_id, payload) in enumerate(rows):
            f.write(json.dumps({
                "run_id": "r", "seq": seq, "sim_time": t,
                "event_type": event_type, "entity_id": entity_id,
                "causal_parent_id": None, "payload": payload,
            }) + "\n")


def test_replenishment_latency_matches_issue_to_deposit(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        # replenish issue: round_id None + request_id, lease_id "<req>:L"
        (1.0, "reservation.acquired", "res:M0:0|M1:0",
         {"round_id": None, "lease_id": "R1:L", "request_id": "R1",
          "path_id": [["M0", 0], ["M1", 0]]}),
        # a ROUND-holder acquisition must be ignored
        (1.1, "reservation.acquired", "res:M1:0|M2:0",
         {"round_id": "round-1", "lease_id": "L9",
          "path_id": [["M1", 0], ["M2", 0]]}),
        (1.35, "pool.deposited", "R1:L",
         {"key": KEY_A, "depth": 1, "lease_id": "R1:L", "round_id": None,
          "source": "replenish"}),
        # round_return deposit must NOT produce a sample
        (2.0, "pool.deposited", "L9",
         {"key": KEY_A, "depth": 2, "lease_id": "L9", "round_id": "round-1",
          "source": "round_return"}),
    ])
    assert replenishment_latency_samples(events) == pytest.approx([0.35])


def test_replenishment_latency_skips_unmatched_deposit(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (1.0, "pool.deposited", "RX:L",
         {"key": KEY_A, "depth": 1, "lease_id": "RX:L", "round_id": None,
          "source": "replenish"}),
    ])
    assert replenishment_latency_samples(events) == []


def test_inter_withdrawal_times_per_key(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (1.0, "pool.withdrawn", "p1", {"key": KEY_A, "depth": 1,
                                        "pooled_lease_id": "p1", "lease_id": "l1",
                                        "round_id": "r1"}),
        (1.5, "pool.withdrawn", "p2", {"key": KEY_A, "depth": 0,
                                        "pooled_lease_id": "p2", "lease_id": "l2",
                                        "round_id": "r2"}),
        (2.5, "pool.withdrawn", "p3", {"key": KEY_A, "depth": 0,
                                        "pooled_lease_id": "p3", "lease_id": "l3",
                                        "round_id": "r3"}),
    ])
    key_a = (((("M0", 0), ("M1", 0))), "messenger")
    assert inter_withdrawal_times(events)[key_a] == pytest.approx([0.5, 1.0])


def test_retry_cadence_gaps_within_round_lineage(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (1.0, "round.arrived", "round-1", {"deadline": 3.0, "retry_ordinal": 0}),
        (1.2, "round.arrived", "round-2", {"deadline": 3.2, "retry_ordinal": 0}),
        (3.0, "round.arrived", "round-1", {"deadline": 5.0, "retry_ordinal": 1}),
        (5.5, "round.arrived", "round-1", {"deadline": 7.5, "retry_ordinal": 2}),
    ])
    assert retry_cadence_samples(events) == pytest.approx([2.0, 2.5])


def test_retry_cadence_empty_when_no_retries(tmp_path):
    events = tmp_path / "events.jsonl"
    _write_events(events, [
        (1.0, "round.arrived", "round-1", {"deadline": 3.0, "retry_ordinal": 0}),
    ])
    assert retry_cadence_samples(events) == []
