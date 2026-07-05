from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.views import deadline_compliance


def _seed(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def test_deadline_compliance_reports_fractions_of_offered(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="round.arrived",
              entity_id="round-0", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=1, sim_time=0.1, event_type="round.arrived",
              entity_id="round-1", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=2, sim_time=0.2, event_type="round.arrived",
              entity_id="round-2", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=3, sim_time=0.3, event_type="round.arrived",
              entity_id="round-3", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=4, sim_time=0.4, event_type="round.completed_in_deadline",
              entity_id="round-0", causal_parent_id=None, payload={"success_probability": 0.9}),
        Event(run_id="r", seq=5, sim_time=0.5, event_type="round.completed_late",
              entity_id="round-1", causal_parent_id=None, payload={"success_probability": 0.9}),
        Event(run_id="r", seq=6, sim_time=0.6, event_type="round.failed",
              entity_id="round-2", causal_parent_id=None, payload={"success_probability": 0.1}),
        Event(run_id="r", seq=7, sim_time=0.7, event_type="round.dropped",
              entity_id="round-3", causal_parent_id=None, payload={}),
    ]
    path = _seed(tmp_path, "run-compliance", events)

    assert deadline_compliance(path) == {
        "completed_in_deadline": 0.25,
        "completed_late": 0.25,
        "failed": 0.25,
        "dropped": 0.25,
    }


def test_deadline_compliance_all_zero_on_empty_trace(tmp_path):
    path = _seed(tmp_path, "run-compliance-empty", [])

    assert deadline_compliance(path) == {
        "completed_in_deadline": 0.0,
        "completed_late": 0.0,
        "failed": 0.0,
        "dropped": 0.0,
    }
