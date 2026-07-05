import json

from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter


def test_append_event_writes_single_jsonl_line_with_all_fields(tmp_path):
    writer = RunDirWriter(root=tmp_path, run_id="run-1")
    event = Event(
        run_id="run-1", seq=0, sim_time=1.5, event_type="round.arrived",
        entity_id="round-1", causal_parent_id=None,
        payload={"retry_ordinal": 0},
    )

    writer.append_event(event)

    lines = (tmp_path / "run-1" / "events.jsonl").read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record == {
        "run_id": "run-1", "seq": 0, "sim_time": 1.5,
        "event_type": "round.arrived", "entity_id": "round-1",
        "causal_parent_id": None, "payload": {"retry_ordinal": 0},
    }


def test_append_event_serializes_causal_parent_id_tuple_as_list(tmp_path):
    writer = RunDirWriter(root=tmp_path, run_id="run-2")
    event = Event(
        run_id="run-2", seq=3, sim_time=2.0, event_type="lease.consumed",
        entity_id="lease-9", causal_parent_id=("run-2", 1),
        payload={"fidelity_at_consumption": 0.87},
    )

    writer.append_event(event)

    record = json.loads((tmp_path / "run-2" / "events.jsonl").read_text().splitlines()[0])
    assert record["causal_parent_id"] == ["run-2", 1]


def test_append_event_multiple_calls_preserve_order(tmp_path):
    writer = RunDirWriter(root=tmp_path, run_id="run-3")
    for i in range(3):
        writer.append_event(Event(
            run_id="run-3", seq=i, sim_time=float(i), event_type="round.arrived",
            entity_id=f"round-{i}", causal_parent_id=None, payload={"retry_ordinal": 0},
        ))

    lines = (tmp_path / "run-3" / "events.jsonl").read_text().splitlines()
    seqs = [json.loads(line)["seq"] for line in lines]
    assert seqs == [0, 1, 2]
