from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.views import resource_utilization


def _seed(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def test_resource_utilization_computes_busy_fraction_per_path(tmp_path):
    path_ab = [["modA", 0], ["modB", 1]]
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="reservation.acquired",
              entity_id="resv-0", causal_parent_id=None,
              payload={"path_id": path_ab, "holder_id": "round-0"}),
        Event(run_id="r", seq=1, sim_time=4.0, event_type="reservation.released",
              entity_id="resv-0", causal_parent_id=None,
              payload={"path_id": path_ab, "holder_id": "round-0"}),
        Event(run_id="r", seq=2, sim_time=10.0, event_type="round.arrived",
              entity_id="round-1", causal_parent_id=None, payload={"retry_ordinal": 0}),
    ]
    path = _seed(tmp_path, "run-util", events)

    utilization = resource_utilization(path)

    assert utilization == {"modA:0|modB:1": 0.4}  # busy 4s of 10s total run


def test_resource_utilization_empty_on_empty_trace(tmp_path):
    path = _seed(tmp_path, "run-util-empty", [])
    assert resource_utilization(path) == {}
