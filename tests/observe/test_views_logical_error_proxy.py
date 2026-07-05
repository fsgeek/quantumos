import pytest

from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.views import logical_error_proxy


def _seed(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def test_logical_error_proxy_aggregates_failure_weight_over_offered(tmp_path):
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
              entity_id="round-0", causal_parent_id=None, payload={"success_probability": 0.95}),
        Event(run_id="r", seq=5, sim_time=0.5, event_type="round.failed",
              entity_id="round-1", causal_parent_id=None, payload={"success_probability": 0.4}),
        Event(run_id="r", seq=6, sim_time=0.6, event_type="round.failed",
              entity_id="round-2", causal_parent_id=None, payload={"success_probability": 0.0}),
        Event(run_id="r", seq=7, sim_time=0.7, event_type="round.dropped",
              entity_id="round-3", causal_parent_id=None, payload={}),
    ]
    path = _seed(tmp_path, "run-error-proxy", events)

    # failures contribute (1 - 0.4) + (1 - 0.0) = 1.6, over 4 offered rounds
    assert logical_error_proxy(path) == pytest.approx(1.6 / 4)


def test_logical_error_proxy_is_zero_with_no_failures(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="round.arrived",
              entity_id="round-0", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=1, sim_time=0.1, event_type="round.completed_in_deadline",
              entity_id="round-0", causal_parent_id=None, payload={"success_probability": 0.99}),
    ]
    path = _seed(tmp_path, "run-error-proxy-zero", events)

    assert logical_error_proxy(path) == 0.0


def test_logical_error_proxy_is_zero_on_empty_trace(tmp_path):
    path = _seed(tmp_path, "run-error-proxy-empty", [])
    assert logical_error_proxy(path) == 0.0
