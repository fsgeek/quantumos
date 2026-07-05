import pytest

from qsim.core.invariants import InvariantChecker, InvariantViolation
from qsim.core.state import EngineState, ModelBundle
from qsim.core.trace import Event


def make_state(active_reservations=None):
    bundle = ModelBundle(decay="d", memory_access="m", heralding="h", round_success="r", decoder_service="s")
    return EngineState(
        now=0.0, epoch="epoch-0", models=bundle, decoder_backlog=0,
        active_reservations=active_reservations or {}, pool={},
        switch_capacity_c=4, hold_until_consumption=False,
    )


def make_event(event_type, entity_id, sim_time=0.0, payload=None, seq=0, causal_parent_id=None):
    return Event(
        run_id="run-1", seq=seq, sim_time=sim_time, event_type=event_type,
        entity_id=entity_id, causal_parent_id=causal_parent_id, payload=payload or {},
    )


class FakeReservation:
    def __init__(self, holder_id, state):
        self.holder_id = holder_id
        self.state = state  # plain string, mirrors ReservationState.value


def test_legal_lease_lifecycle_does_not_raise():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("lease.requested", "lease-1", sim_time=0.0, seq=0), state)
    checker.observe(make_event("lease.heralded", "lease-1", sim_time=1.0, seq=1), state)
    checker.observe(make_event("lease.consumed", "lease-1", sim_time=2.0, seq=2), state)


def test_event_time_non_monotonicity_raises():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("round.arrived", "round-1", sim_time=5.0, seq=0), state)
    with pytest.raises(InvariantViolation):
        checker.observe(make_event("round.admitted", "round-1", sim_time=4.9, seq=1), state)


def test_equal_sim_time_is_not_a_monotonicity_violation():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("round.arrived", "round-1", sim_time=3.0, seq=0), state)
    checker.observe(make_event("round.admitted", "round-1", sim_time=3.0, seq=1), state)


def test_invariant_violation_carries_offending_event():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("round.arrived", "round-1", sim_time=5.0, seq=0), state)
    offending = make_event("round.admitted", "round-1", sim_time=4.0, seq=1)
    with pytest.raises(InvariantViolation) as exc_info:
        checker.observe(offending, state)
    assert exc_info.value.event is offending


def test_illegal_lease_transition_consumed_without_heralding_raises():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("lease.requested", "lease-1", sim_time=0.0, seq=0), state)
    with pytest.raises(InvariantViolation):
        checker.observe(make_event("lease.consumed", "lease-1", sim_time=1.0, seq=1), state)


def test_double_consumption_raises():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("lease.requested", "lease-1", sim_time=0.0, seq=0), state)
    checker.observe(make_event("lease.heralded", "lease-1", sim_time=1.0, seq=1), state)
    checker.observe(make_event("lease.consumed", "lease-1", sim_time=2.0, seq=2), state)
    with pytest.raises(InvariantViolation):
        checker.observe(make_event("lease.consumed", "lease-1", sim_time=3.0, seq=3), state)


def test_pool_returned_event_is_not_checked_as_a_lease_transition():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("lease.requested", "lease-1", sim_time=0.0, seq=0), state)
    checker.observe(make_event("lease.heralded", "lease-1", sim_time=1.0, seq=1), state)
    checker.observe(make_event("lease.pool_returned", "lease-1", sim_time=2.0, seq=2), state)
    checker.observe(make_event("lease.consumed", "lease-1", sim_time=3.0, seq=3), state)


def test_fidelity_above_one_raises():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("lease.requested", "lease-1", sim_time=0.0, seq=0), state)
    with pytest.raises(InvariantViolation, match="fidelity"):
        checker.observe(
            make_event("lease.heralded", "lease-1", sim_time=1.0, seq=1, payload={"fidelity": 1.5}),
            state,
        )


def test_fidelity_below_zero_raises():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("lease.requested", "lease-1", sim_time=0.0, seq=0), state)
    with pytest.raises(InvariantViolation, match="fidelity"):
        checker.observe(
            make_event("lease.heralded", "lease-1", sim_time=1.0, seq=1, payload={"fidelity": -0.01}),
            state,
        )


@pytest.mark.parametrize("boundary_fidelity", [0.0, 1.0])
def test_fidelity_at_boundary_is_legal(boundary_fidelity):
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("lease.requested", "lease-1", sim_time=0.0, seq=0), state)
    checker.observe(
        make_event("lease.heralded", "lease-1", sim_time=1.0, seq=1, payload={"fidelity": boundary_fidelity}),
        state,
    )


def test_heralded_without_requested_raises_even_with_fidelity():
    # The fail-stop net must catch an engine that heralds a lease it never
    # requested, including when the heralded event carries a (valid) fidelity
    # reading -- the realistic shape of a requested-skip bug (§14).
    checker = InvariantChecker()
    state = make_state()
    with pytest.raises(InvariantViolation, match="illegal lease transition"):
        checker.observe(
            make_event("lease.heralded", "lease-1", sim_time=0.0, seq=0, payload={"fidelity": 0.9}),
            state,
        )


def test_reservation_outliving_its_holder_raises():
    checker = InvariantChecker()
    leaked = FakeReservation(holder_id="round-1", state="active")
    state = make_state(active_reservations={"path-a": leaked})

    checker.observe(make_event("round.arrived", "round-1", sim_time=0.0, seq=0), state)
    with pytest.raises(InvariantViolation):
        checker.observe(make_event("round.failed", "round-1", sim_time=1.0, seq=1), state)


def test_reservation_released_before_or_at_terminal_event_does_not_raise():
    checker = InvariantChecker()
    released = FakeReservation(holder_id="round-1", state="released")
    state = make_state(active_reservations={"path-a": released})

    checker.observe(make_event("round.arrived", "round-1", sim_time=0.0, seq=0), state)
    checker.observe(make_event("round.failed", "round-1", sim_time=1.0, seq=1), state)


def test_reservation_leak_for_unrelated_holder_does_not_raise():
    checker = InvariantChecker()
    other = FakeReservation(holder_id="round-2", state="active")
    state = make_state(active_reservations={"path-a": other})

    checker.observe(make_event("round.arrived", "round-1", sim_time=0.0, seq=0), state)
    checker.observe(make_event("round.failed", "round-1", sim_time=1.0, seq=1), state)


def test_round_rearrival_clears_terminated_holder_so_a_retry_reservation_is_legal():
    # A round_id is reused across retries for lineage. After the first attempt
    # fails (round.failed marks it terminated), a retry RE-ARRIVES with the same
    # round_id and legitimately holds a fresh reservation. The re-arrival must
    # clear the terminated mark, or the retry's active reservation false-trips
    # the leak check -- which would fire in exactly the S0-churns-under-load
    # regime the falsification studies. Without the fix, the final observe below
    # raises InvariantViolation.
    checker = InvariantChecker()
    empty = make_state()
    checker.observe(make_event("round.arrived", "round-1", sim_time=0.0, seq=0), empty)
    checker.observe(make_event("round.failed", "round-1", sim_time=1.0, seq=1), empty)
    checker.observe(make_event("round.arrived", "round-1", sim_time=2.0, seq=2), empty)  # retry
    retry_reservation = FakeReservation(holder_id="round-1", state="active")
    held = make_state(active_reservations={"path-a": retry_reservation})
    # Must NOT raise: round-1 is alive again, so its active reservation is legal.
    checker.observe(make_event("reservation.acquired", "path-a", sim_time=2.0, seq=3), held)
