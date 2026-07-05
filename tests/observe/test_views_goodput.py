from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.views import goodput


def _seed(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def test_goodput_is_completed_in_deadline_over_offered(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="round.arrived",
              entity_id="round-0", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=1, sim_time=0.1, event_type="round.arrived",
              entity_id="round-1", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=2, sim_time=0.2, event_type="round.completed_in_deadline",
              entity_id="round-0", causal_parent_id=None, payload={"success_probability": 0.95}),
        Event(run_id="r", seq=3, sim_time=0.3, event_type="round.failed",
              entity_id="round-1", causal_parent_id=None, payload={"success_probability": 0.2}),
    ]
    path = _seed(tmp_path, "run-gp", events)

    assert goodput(path) == 0.5


def test_goodput_is_not_fooled_by_dropping_work_to_raise_compliance_among_admitted(tmp_path):
    # 4 rounds offered. Only 1 is admitted and completes in time; the other 3
    # are dropped outright. A naive "compliance among admitted" metric
    # (completed_in_deadline / admitted == 1/1 == 100%) would look perfect,
    # but the primary offered-normalized goodput view must reflect that most
    # offered work never got served.
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="round.arrived",
              entity_id="round-0", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=1, sim_time=0.1, event_type="round.arrived",
              entity_id="round-1", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=2, sim_time=0.2, event_type="round.arrived",
              entity_id="round-2", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=3, sim_time=0.3, event_type="round.arrived",
              entity_id="round-3", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=4, sim_time=0.4, event_type="round.admitted",
              entity_id="round-0", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=5, sim_time=0.5, event_type="round.completed_in_deadline",
              entity_id="round-0", causal_parent_id=None, payload={"success_probability": 0.95}),
        Event(run_id="r", seq=6, sim_time=0.6, event_type="round.dropped",
              entity_id="round-1", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=7, sim_time=0.7, event_type="round.dropped",
              entity_id="round-2", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=8, sim_time=0.8, event_type="round.dropped",
              entity_id="round-3", causal_parent_id=None, payload={}),
    ]
    path = _seed(tmp_path, "run-gaming", events)

    naive_compliance_among_admitted = 1 / 1  # what a work-rejecting admission controller would show
    assert naive_compliance_among_admitted == 1.0

    assert goodput(path) == 0.25


def test_goodput_is_zero_on_empty_trace(tmp_path):
    path = _seed(tmp_path, "run-empty", [])
    assert goodput(path) == 0.0
