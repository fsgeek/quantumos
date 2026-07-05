import math

import pytest

from qsim.core.rng import draw_uniform
from qsim.entities import RoundState
from qsim.workload.generator import WorkloadGenerator


def test_interarrival_deterministic_same_seed_and_index():
    # Same run_seed + same arrival_index => identical interarrival draw (§10 CRN guarantee).
    g1 = WorkloadGenerator(run_seed=42, arrival_rate_hz=2.0, leases_per_round=3, deadline_slack_s=1.0)
    g2 = WorkloadGenerator(run_seed=42, arrival_rate_hz=2.0, leases_per_round=3, deadline_slack_s=1.0)
    r1 = g1.next_arrival(after_time=0.0, arrival_index=7)
    r2 = g2.next_arrival(after_time=0.0, arrival_index=7)
    assert r1.arrival_time == r2.arrival_time


def test_different_seed_changes_interarrival():
    g1 = WorkloadGenerator(run_seed=1, arrival_rate_hz=2.0, leases_per_round=1, deadline_slack_s=1.0)
    g2 = WorkloadGenerator(run_seed=2, arrival_rate_hz=2.0, leases_per_round=1, deadline_slack_s=1.0)
    r1 = g1.next_arrival(after_time=0.0, arrival_index=7)
    r2 = g2.next_arrival(after_time=0.0, arrival_index=7)
    assert r1.arrival_time != r2.arrival_time


def test_interarrival_keyed_by_index_not_call_order():
    # The draw is keyed by arrival_index, so call order must not affect the result (§10).
    g1 = WorkloadGenerator(run_seed=1, arrival_rate_hz=1.0, leases_per_round=1, deadline_slack_s=0.5)
    a = g1.next_arrival(after_time=0.0, arrival_index=1)
    b = g1.next_arrival(after_time=0.0, arrival_index=2)

    g2 = WorkloadGenerator(run_seed=1, arrival_rate_hz=1.0, leases_per_round=1, deadline_slack_s=0.5)
    b2 = g2.next_arrival(after_time=0.0, arrival_index=2)  # reversed call order
    a2 = g2.next_arrival(after_time=0.0, arrival_index=1)

    assert a.arrival_time == a2.arrival_time
    assert b.arrival_time == b2.arrival_time


def test_interarrival_is_exponential_inverse_transform_of_keyed_uniform():
    seed, rate, idx = 99, 4.0, 3
    g = WorkloadGenerator(run_seed=seed, arrival_rate_hz=rate, leases_per_round=1, deadline_slack_s=0.0)
    u = draw_uniform(seed, "workload", ("arrival", idx))
    expected_interarrival = -math.log(1.0 - u) / rate
    r = g.next_arrival(after_time=10.0, arrival_index=idx)
    # arrival_time = after_time + exponential(rate) interarrival.
    assert r.arrival_time == pytest.approx(10.0 + expected_interarrival)


def test_next_arrival_builds_pending_round_with_leases_and_deadline():
    g = WorkloadGenerator(run_seed=5, arrival_rate_hz=1.0, leases_per_round=4, deadline_slack_s=2.5)
    r = g.next_arrival(after_time=0.0, arrival_index=11)
    assert r.round_id == "round-11"
    assert len(r.lease_ids) == 4
    assert r.retry_ordinal == 0
    assert r.state is RoundState.PENDING
    assert r.deadline == pytest.approx(r.arrival_time + 2.5)
