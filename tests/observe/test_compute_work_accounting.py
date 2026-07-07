from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.work_accounting import compute_work_accounting, iter_events


def _seed_events(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def test_iter_events_yields_dicts_in_file_order(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="round.arrived",
              entity_id="round-0", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=1, sim_time=1.0, event_type="round.admitted",
              entity_id="round-0", causal_parent_id=("r", 0), payload={}),
    ]
    path = _seed_events(tmp_path, "run-iter", events)

    records = list(iter_events(path))

    assert [r["event_type"] for r in records] == ["round.arrived", "round.admitted"]


def test_compute_work_accounting_counts_each_event_type(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="round.arrived",
              entity_id="round-0", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=1, sim_time=0.1, event_type="round.arrived",
              entity_id="round-1", causal_parent_id=None, payload={"retry_ordinal": 1}),
        Event(run_id="r", seq=2, sim_time=0.2, event_type="round.admitted",
              entity_id="round-0", causal_parent_id=("r", 0), payload={}),
        Event(run_id="r", seq=3, sim_time=0.3, event_type="round.deferred",
              entity_id="round-1", causal_parent_id=("r", 1), payload={}),
        Event(run_id="r", seq=4, sim_time=0.4, event_type="round.dropped",
              entity_id="round-2", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=5, sim_time=0.5, event_type="round.completed_in_deadline",
              entity_id="round-0", causal_parent_id=("r", 2), payload={"success_probability": 0.9}),
        Event(run_id="r", seq=6, sim_time=0.6, event_type="round.completed_late",
              entity_id="round-3", causal_parent_id=None, payload={"success_probability": 0.8}),
        Event(run_id="r", seq=7, sim_time=0.7, event_type="round.failed",
              entity_id="round-4", causal_parent_id=None, payload={"success_probability": 0.3}),
        Event(run_id="r", seq=8, sim_time=0.8, event_type="lease.pool_returned",
              entity_id="lease-0", causal_parent_id=None, payload={}),
    ]
    path = _seed_events(tmp_path, "run-wa", events)

    wa = compute_work_accounting(path)

    assert wa.offered == 1
    assert wa.retries == 1
    assert wa.admitted == 1
    assert wa.deferred == 1
    assert wa.dropped == 1
    assert wa.completed_in_deadline == 1
    assert wa.completed_late == 1
    assert wa.failed == 1
    assert wa.pool_returned == 1


def test_pool_annotation_events_change_no_work_accounting_counter(tmp_path):
    # B3 guard: the four pool.* events are ANNOTATIONS of pool state, not round
    # terminals — none may increment a WorkAccounting counter, while the
    # co-occurring lease.pool_returned keeps its separate §5/§11 counter with
    # exactly one increment per occurrence (the double-count failure mode).
    key = [[["M0", 0], ["M1", 0]], "messenger"]
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="pool.deposited",
              entity_id="lease-0", causal_parent_id=None,
              payload={"key": key, "depth": 1, "source": "round_return"}),
        Event(run_id="r", seq=1, sim_time=0.0, event_type="lease.pool_returned",
              entity_id="lease-0", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=2, sim_time=1.0, event_type="pool.withdrawn",
              entity_id="lease-0", causal_parent_id=None,
              payload={"key": key, "depth": 0}),
        Event(run_id="r", seq=3, sim_time=2.0, event_type="pool.expired",
              entity_id="lease-1", causal_parent_id=None,
              payload={"key": key, "depth": 0}),
        Event(run_id="r", seq=4, sim_time=3.0, event_type="pool.replenish_abandoned",
              entity_id="pool-req-1", causal_parent_id=None,
              payload={"key": key, "depth": 0, "reason": "herald_failed"}),
    ]
    path = _seed_events(tmp_path, "run-pool-annotations", events)

    wa = compute_work_accounting(path)

    assert wa.pool_returned == 1
    assert (wa.offered, wa.retries, wa.admitted, wa.deferred, wa.dropped,
            wa.completed_in_deadline, wa.completed_late, wa.failed) == (
        0, 0, 0, 0, 0, 0, 0, 0)


def test_compute_work_accounting_empty_trace_is_all_zero(tmp_path):
    path = _seed_events(tmp_path, "run-empty", [])

    wa = compute_work_accounting(path)

    assert wa.offered == 0
    assert wa.attempts() == 0
    assert wa.goodput() == 0.0
