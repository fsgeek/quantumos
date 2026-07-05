from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.views import decoder_backlog_series


def _seed(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def test_decoder_backlog_series_tracks_jobs_in_system(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="decoder.enqueued",
              entity_id="job-0", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=1, sim_time=1.0, event_type="decoder.enqueued",
              entity_id="job-1", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=2, sim_time=2.0, event_type="decoder.dequeued",
              entity_id="job-0", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=3, sim_time=3.0, event_type="decoder.completed",
              entity_id="job-0", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=4, sim_time=4.0, event_type="decoder.cancelled",
              entity_id="job-1", causal_parent_id=None, payload={}),
    ]
    path = _seed(tmp_path, "run-backlog", events)

    assert decoder_backlog_series(path) == [
        (0.0, 1),
        (1.0, 2),
        (3.0, 1),
        (4.0, 0),
    ]


def test_decoder_backlog_series_empty_on_empty_trace(tmp_path):
    path = _seed(tmp_path, "run-backlog-empty", [])
    assert decoder_backlog_series(path) == []
