"""Engine unit E1 — Task 2: path allocation and switch-reservation lifecycle.

Reconciled per .superpowers/sdd/engine-reconciliation-spec.md: path selection
is driven through the real Scheduler queue (register_round_demand /
next_lease_request) rather than the placeholder allocate_path, but the brief's
assertions about reservation trace events, timing, and causal parents are
unchanged.
"""

from qsim.core.clock import SimClock
from qsim.core.trace import TraceBus
from qsim.core.invariants import InvariantChecker
from qsim.core.engine import Engine, _RoundContext
from qsim.policies.s0 import S0Scheduler
from qsim.policies.protocol import LeaseRequest, LeaseRequestPurpose
from qsim.entities import CoherenceClass, ReservationState, make_path_id

from tests.core.test_engine import make_config, make_models, make_workload


def test_admitted_round_acquires_configures_and_activates_a_path():
    workload = make_workload()
    first_round = workload.next_arrival(0.0, 1)
    config = make_config(switch_capacity_c=2)
    config = config.__class__(**{**config.__dict__, "reconfig_delay_s": 0.5})

    events = []
    clock = SimClock()
    trace = TraceBus(run_id="test-run", clock=clock)
    trace.subscribe(events.append)
    engine = Engine(config=config, scheduler=S0Scheduler(), models=make_models(),
                    workload=make_workload(), trace=trace, invariants=InvariantChecker())

    engine.run_to(first_round.arrival_time + config.reconfig_delay_s + 1e-6)

    types = [e.event_type for e in events]
    assert types[:2] == ["round.arrived", "round.admitted"]
    assert "reservation.acquired" in types
    assert "reservation.configuring" in types
    assert "reservation.active" in types

    acquired = events[types.index("reservation.acquired")]
    configuring = events[types.index("reservation.configuring")]
    active = events[types.index("reservation.active")]
    assert acquired.sim_time == configuring.sim_time == first_round.arrival_time
    assert active.sim_time == first_round.arrival_time + config.reconfig_delay_s
    assert configuring.causal_parent_id == (acquired.run_id, acquired.seq)
    assert active.causal_parent_id == (configuring.run_id, configuring.seq)

    ctx = engine._round_contexts[first_round.round_id]
    path_id = ctx.reservations[next(iter(ctx.reservations))].path_id
    reservation = engine._state.active_reservations[path_id]
    assert reservation.state == ReservationState.ACTIVE


def test_capacity_exhaustion_fails_the_round_rather_than_deferring():
    # Two capacity-1 rounds contend for the single switch path. The first
    # admitted round reserves it; the second is admitted (S0 checks only the
    # deadline) but finds no capacity, so it FAILS and retries — it is never
    # deferred. This is the churn semantics the reconciliation spec mandates.
    config = make_config(switch_capacity_c=1)

    events = []
    clock = SimClock()
    trace = TraceBus(run_id="test-run", clock=clock)
    trace.subscribe(events.append)
    engine = Engine(config=config, scheduler=S0Scheduler(), models=make_models(),
                    workload=make_workload(), trace=trace, invariants=InvariantChecker())

    workload = make_workload()
    r1 = workload.next_arrival(0.0, 1)
    r2 = workload.next_arrival(r1.arrival_time, 2)

    # Run just far enough to admit the second arrival and see it fail.
    engine.run_to(r2.arrival_time + 1e-6)

    # The first round holds an ACTIVE-or-configuring reservation (reconfig=0 so
    # it is ACTIVE); the second round produced a round.failed, never deferred.
    failed = [e for e in events if e.event_type == "round.failed"]
    assert failed, "capacity-exhausted round must fail"
    assert failed[0].entity_id == r2.round_id
    assert all(e.event_type != "round.deferred" for e in events)
    # Exactly one live reservation (the first round's) at capacity 1.
    live = [r for r in engine._state.active_reservations.values()
            if r.state != ReservationState.RELEASED]
    assert len(live) == 1
    assert live[0].holder_id == r1.round_id


def _acquire_for(engine, round_, path_id):
    """Reserve `path_id` for `round_` and return (ctx, reservation)."""
    lease_id = round_.lease_ids[0]
    ctx = _RoundContext(round=round_, causal_parent_id=None)
    ctx.path_to_lease[path_id] = lease_id
    engine._round_contexts[round_.round_id] = ctx
    request = LeaseRequest(
        request_id=lease_id, path_id=path_id,
        coherence_class=CoherenceClass.MESSENGER,
        purpose=LeaseRequestPurpose.ROUND,
        requested_at_s=0.0, round_id=round_.round_id,
    )
    engine._acquire_path(ctx, request)
    return ctx, ctx.reservations[lease_id]


def test_stale_activation_does_not_flip_a_reacquired_paths_new_reservation():
    # Regression: a reservation released while still CONFIGURING leaves a stale
    # activation event on the heap. If a DIFFERENT round re-acquires that same
    # path before the stale activation fires, the activation must be a no-op —
    # it must NOT flip the new reservation to ACTIVE nor emit reservation.active
    # with the failed round's round_id/lease_id. The handler guards by
    # reservation IDENTITY, not merely `active_reservations.get(...) is None`.
    config = make_config(switch_capacity_c=2)
    config = config.__class__(**{**config.__dict__, "reconfig_delay_s": 0.5})

    events = []
    clock = SimClock()
    trace = TraceBus(run_id="test-run", clock=clock)
    trace.subscribe(events.append)
    engine = Engine(config=config, scheduler=S0Scheduler(), models=make_models(),
                    workload=make_workload(), trace=trace, invariants=InvariantChecker())

    workload = make_workload()
    round_a = workload.next_arrival(0.0, 1)
    round_b = workload.next_arrival(round_a.arrival_time, 2)
    path_id = make_path_id(engine._ports[0], engine._ports[1])

    # Round A acquires the path and begins configuring it.
    ctx_a, reservation_a = _acquire_for(engine, round_a, path_id)
    assert reservation_a.state == ReservationState.CONFIGURING
    # A's pending activation is now the sole heap entry (fires at reconfig_delay).
    stale_entry = engine._heap.pop()
    assert stale_entry.payload.reservation is reservation_a

    # Round A fails on a later lease, releasing the path BEFORE its activation.
    engine._release_round_reservations(ctx_a, causal_parent_id=None)
    assert reservation_a.state == ReservationState.RELEASED
    assert path_id not in engine._state.active_reservations

    # Round B re-acquires the SAME path in the interim.
    _ctx_b, reservation_b = _acquire_for(engine, round_b, path_id)
    assert reservation_b.state == ReservationState.CONFIGURING
    assert engine._state.active_reservations[path_id] is reservation_b

    events.clear()
    # A's stale activation fires: it must not touch B's reservation.
    engine._state.now = stale_entry.time
    engine._clock.advance_to(stale_entry.time)
    engine._dispatch(stale_entry.payload)

    assert reservation_b.state == ReservationState.CONFIGURING
    assert reservation_a.state == ReservationState.RELEASED
    assert all(e.event_type != "reservation.active" for e in events)
