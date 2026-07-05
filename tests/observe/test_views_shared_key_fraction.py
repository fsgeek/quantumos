import pytest

from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.views import shared_key_fraction


def _seed(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def _draw(run_id, seq, sim_time, stream, key):
    return Event(
        run_id=run_id, seq=seq, sim_time=sim_time, event_type="draw.sampled",
        entity_id=stream, causal_parent_id=None,
        payload={"stream": stream, "key": list(key), "uniform": 0.5},
    )


def test_shared_key_fraction_known_overlap_per_window(tmp_path):
    # Window 0 [0,10): A draws keys {r1, r2}; B draws keys {r1, r4}.
    #   intersection = {r1} (size 1), union = {r1, r2, r4} (size 3) -> 1/3
    # Window 1 [10,20): A and B both draw {r3} -> intersection == union -> 1.0
    events_a = [
        _draw("a", 0, 1.0, "herald", ("herald", "r1", "p1", 1)),
        _draw("a", 1, 2.0, "herald", ("herald", "r2", "p1", 1)),
        _draw("a", 2, 15.0, "herald", ("herald", "r3", "p1", 1)),
    ]
    events_b = [
        _draw("b", 0, 1.0, "herald", ("herald", "r1", "p1", 1)),
        _draw("b", 1, 3.0, "herald", ("herald", "r4", "p1", 1)),
        _draw("b", 2, 16.0, "herald", ("herald", "r3", "p1", 1)),
    ]
    path_a = _seed(tmp_path, "run-a", events_a)
    path_b = _seed(tmp_path, "run-b", events_b)

    result = shared_key_fraction(path_a, path_b, window_s=10.0)

    assert result == [
        pytest.approx((0.0, 1 / 3)),
        pytest.approx((10.0, 1.0)),
    ]


def test_shared_key_fraction_no_draws_returns_empty(tmp_path):
    path_a = _seed(tmp_path, "run-a-empty", [])
    path_b = _seed(tmp_path, "run-b-empty", [])

    assert shared_key_fraction(path_a, path_b, window_s=10.0) == []
