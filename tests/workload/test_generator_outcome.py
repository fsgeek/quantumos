from qsim.entities import RoundState
from qsim.workload.generator import WorkloadGenerator


def _round(index=0):
    g = WorkloadGenerator(run_seed=1, arrival_rate_hz=1.0, leases_per_round=2, deadline_slack_s=1.0)
    return g, g.next_arrival(after_time=0.0, arrival_index=index)


def test_on_outcome_success_returns_none():
    g, r = _round()
    assert g.on_outcome(r, succeeded=True) is None


def test_on_outcome_failure_returns_retry_with_incremented_ordinal_same_identity():
    g, r = _round(index=8)
    retry = g.on_outcome(r, succeeded=False)
    assert retry is not None
    assert retry.round_id == r.round_id            # round identity preserved for lineage
    assert retry.lease_ids == r.lease_ids
    assert retry.retry_ordinal == r.retry_ordinal + 1
    assert retry.state is RoundState.PENDING


def test_retry_ordinal_increments_across_repeated_failures():
    g, r = _round(index=3)
    r1 = g.on_outcome(r, succeeded=False)
    r2 = g.on_outcome(r1, succeeded=False)
    assert (r1.retry_ordinal, r2.retry_ordinal) == (1, 2)
    assert r2.round_id == r.round_id               # lineage held across multiple retries


def test_retry_is_a_distinct_object_from_the_original():
    g, r = _round()
    retry = g.on_outcome(r, succeeded=False)
    assert retry is not r
    assert r.retry_ordinal == 0                    # original round is not mutated
    assert r.state is RoundState.PENDING
