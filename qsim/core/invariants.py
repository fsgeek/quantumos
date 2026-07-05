"""Mechanical invariant checks over the trace (design spec §14).

These invariants prove the bookkeeping is legal; they provide zero
protection against a wrong physics model (see §14's scope statement).
Violation is fail-stop: InvariantViolation carries the offending event so
the caller can flush the trace and crash loudly with its causal chain.
"""

from __future__ import annotations

from qsim.core.state import EngineState
from qsim.core.trace import Event


class InvariantViolation(Exception):
    """Raised with the causal chain of the offending event (§14)."""

    def __init__(self, message: str, event: Event) -> None:
        super().__init__(f"{message} | offending event: {event!r}")
        self.event = event


# Lease-lifecycle legality (design spec §5, §14), expressed directly over
# EVENT_TYPES' lease.* strings rather than entities.LeaseState: core/ does
# not import entities/ (dependency arrows point downward only, §4).
_LEASE_TRANSITION_EVENTS = {
    "lease.requested": "requested",
    "lease.heralded": "heralded",
    "lease.consumed": "consumed",
    "lease.expired": "expired",
    "lease.cancelled": "cancelled",
    # lease.pool_returned is bookkeeping for the pregen pool, not a
    # LeaseState transition (design spec §5), so it is deliberately absent
    # and never checked for lifecycle legality.
}

_LEGAL_LEASE_TRANSITIONS: dict[str | None, set[str]] = {
    None: {"requested"},
    "requested": {"heralded", "cancelled"},
    "heralded": {"consumed", "expired", "cancelled"},
    "consumed": set(),
    "expired": set(),
    "cancelled": set(),
}

_ROUND_TERMINAL_EVENTS = {
    "round.completed_in_deadline", "round.completed_late", "round.failed", "round.dropped",
}
_LEASE_TERMINAL_EVENTS = {"lease.consumed", "lease.expired", "lease.cancelled"}


class InvariantChecker:
    """Continuously checks mechanical correctness (§14).

    Maintains its own history of lease states and terminated holders,
    reconstructed purely from the Event stream it observes — EngineState is
    a present-moment view (§4) and does not itself retain that history.
    """

    def __init__(self) -> None:
        self._last_sim_time: float | None = None
        self._lease_states: dict[str, str | None] = {}
        self._terminated_holders: set[str] = set()

    def observe(self, event: Event, state: EngineState) -> None:
        self._check_monotonicity(event)
        self._check_lease_transition(event)
        self._check_fidelity(event)
        self._record_terminated_holder(event)
        self._check_reservation_leak(event, state)
        self._last_sim_time = event.sim_time

    def _check_monotonicity(self, event: Event) -> None:
        if self._last_sim_time is not None and event.sim_time < self._last_sim_time:
            raise InvariantViolation(
                f"event-time non-monotonicity: {event.sim_time} follows {self._last_sim_time}",
                event,
            )

    def _check_lease_transition(self, event: Event) -> None:
        target = _LEASE_TRANSITION_EVENTS.get(event.event_type)
        if target is None:
            return
        current = self._lease_states.get(event.entity_id)
        if target not in _LEGAL_LEASE_TRANSITIONS[current]:
            raise InvariantViolation(
                f"illegal lease transition for {event.entity_id!r}: "
                f"{current!r} -> {target!r} via {event.event_type!r}",
                event,
            )
        self._lease_states[event.entity_id] = target

    def _check_fidelity(self, event: Event) -> None:
        if "fidelity" not in event.payload:
            return
        fidelity = event.payload["fidelity"]
        if not (0.0 <= fidelity <= 1.0):
            raise InvariantViolation(
                f"fidelity {fidelity!r} outside [0,1] on entity {event.entity_id!r}",
                event,
            )

    def _record_terminated_holder(self, event: Event) -> None:
        if event.event_type == "round.arrived":
            # A round_id is reused across retries for lineage (WorkloadGenerator
            # keeps the same identity on retry). A retry re-arriving is the holder
            # ALIVE AGAIN, so clear any prior terminal mark — otherwise the
            # retry's legitimately-held new reservations false-trip the
            # reservation-leak check below. If the reborn round later terminates
            # without releasing them, round.failed/etc. re-adds it and the leak is
            # caught then.
            self._terminated_holders.discard(event.entity_id)
            return
        if event.event_type in _ROUND_TERMINAL_EVENTS or event.event_type in _LEASE_TERMINAL_EVENTS:
            self._terminated_holders.add(event.entity_id)

    def _check_reservation_leak(self, event: Event, state: EngineState) -> None:
        for path_id, reservation in state.active_reservations.items():
            holder_id = reservation.holder_id
            if holder_id not in self._terminated_holders:
                continue
            state_value = getattr(reservation.state, "value", reservation.state)
            if state_value != "released":
                raise InvariantViolation(
                    f"SwitchPathReservation on {path_id!r} outlives terminated holder {holder_id!r}",
                    event,
                )
