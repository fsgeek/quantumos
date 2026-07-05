from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.views import freshness_at_consumption


def _seed(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def test_freshness_at_consumption_returns_fidelity_values_in_order(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="lease.consumed",
              entity_id="lease-0", causal_parent_id=None, payload={"fidelity_at_consumption": 0.91}),
        Event(run_id="r", seq=1, sim_time=1.0, event_type="lease.expired",
              entity_id="lease-1", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=2, sim_time=2.0, event_type="lease.consumed",
              entity_id="lease-2", causal_parent_id=None, payload={"fidelity_at_consumption": 0.77}),
    ]
    path = _seed(tmp_path, "run-fresh", events)

    assert freshness_at_consumption(path) == [0.91, 0.77]


def test_freshness_at_consumption_empty_when_no_consumptions(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="lease.expired",
              entity_id="lease-0", causal_parent_id=None, payload={}),
    ]
    path = _seed(tmp_path, "run-nofresh", events)

    assert freshness_at_consumption(path) == []
