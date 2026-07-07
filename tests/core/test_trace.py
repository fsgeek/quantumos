from dataclasses import FrozenInstanceError

import pytest

from qsim.core.clock import SimClock
from qsim.core.trace import EVENT_TYPES, Event, TraceBus


def test_publish_returns_event_id_with_run_id_and_incrementing_seq():
    bus = TraceBus(run_id="run-1", clock=SimClock())
    first = bus.publish("round.arrived", "round-1", None, {})
    second = bus.publish("round.arrived", "round-2", None, {})
    assert first == ("run-1", 0)
    assert second == ("run-1", 1)


def test_publish_stamps_event_with_current_clock_time():
    clock = SimClock()
    bus = TraceBus(run_id="run-1", clock=clock)
    clock.advance_to(4.5)

    received = []
    bus.subscribe(received.append)
    bus.publish("round.arrived", "round-1", None, {"x": 1})

    assert len(received) == 1
    event = received[0]
    assert isinstance(event, Event)
    assert event.sim_time == 4.5
    assert event.run_id == "run-1"
    assert event.entity_id == "round-1"
    assert event.event_type == "round.arrived"
    assert event.causal_parent_id is None
    assert event.payload == {"x": 1}


def test_subscribe_supports_multiple_subscribers_all_notified():
    bus = TraceBus(run_id="run-1", clock=SimClock())
    seen_a, seen_b = [], []
    bus.subscribe(seen_a.append)
    bus.subscribe(seen_b.append)

    bus.publish(
        "draw.sampled", "herald:round-1:0", None,
        {"stream": "herald", "key": (), "uniform": 0.4},
    )

    assert len(seen_a) == 1
    assert len(seen_b) == 1
    assert seen_a[0] is seen_b[0]


def test_publish_carries_causal_parent_id():
    bus = TraceBus(run_id="run-1", clock=SimClock())
    parent_id = bus.publish("round.arrived", "round-1", None, {})
    child_id = bus.publish("round.admitted", "round-1", parent_id, {})

    received = []
    bus.subscribe(received.append)
    bus.publish("round.completed_in_deadline", "round-1", child_id, {})
    assert received[0].causal_parent_id == child_id


def test_publish_rejects_unknown_event_type():
    bus = TraceBus(run_id="run-1", clock=SimClock())
    with pytest.raises(ValueError):
        bus.publish("round.made_up_type", "round-1", None, {})


def test_event_dataclass_is_frozen():
    event = Event(
        run_id="run-1", seq=0, sim_time=0.0, event_type="round.arrived",
        entity_id="round-1", causal_parent_id=None, payload={},
    )
    with pytest.raises(FrozenInstanceError):
        event.seq = 1


def test_pool_annotation_event_types_are_registered():
    # B3: the four pregen-pool annotation events (per prereg 2026-07-06 T1's
    # depth-series requirement) must be publishable trace types.
    assert "pool.deposited" in EVENT_TYPES
    assert "pool.withdrawn" in EVENT_TYPES
    assert "pool.expired" in EVENT_TYPES
    assert "pool.replenish_abandoned" in EVENT_TYPES


@pytest.mark.parametrize("event_type", EVENT_TYPES)
def test_every_event_type_is_publishable_and_round_trips(event_type):
    bus = TraceBus(run_id="run-1", clock=SimClock())
    received = []
    bus.subscribe(received.append)

    event_id = bus.publish(event_type, "entity-1", None, {"note": event_type})

    assert event_id == ("run-1", 0)
    assert len(received) == 1
    assert received[0].event_type == event_type
