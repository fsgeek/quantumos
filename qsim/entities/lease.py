"""EntanglementLease entity: lifecycle
requested -> heralded -> (consumed | expired | cancelled), exactly one
terminal state (design spec §5)."""

from dataclasses import dataclass
from enum import Enum

from qsim.entities.module import PathId, PortId


class LeaseState(Enum):
    REQUESTED = "requested"
    HERALDED = "heralded"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


TERMINAL_LEASE_STATES = frozenset(
    {LeaseState.CONSUMED, LeaseState.EXPIRED, LeaseState.CANCELLED}
)


@dataclass
class EntanglementLease:
    lease_id: str
    endpoints: tuple[PortId, PortId]
    path_id: PathId
    created_at: float
    freshness_bound_s: float
    fidelity_at_herald: float | None = None
    heralded_at: float | None = None
    state: LeaseState = LeaseState.REQUESTED
    retry_count: int = 0

    def mark_heralded(self, at: float, fidelity: float) -> None:
        """Transition requested -> heralded. Illegal from any other state."""
        if self.state is not LeaseState.REQUESTED:
            raise ValueError(
                f"lease {self.lease_id} cannot be heralded from state {self.state}"
            )
        self.heralded_at = at
        self.fidelity_at_herald = fidelity
        self.state = LeaseState.HERALDED

    def consume(self) -> None:
        """Transition heralded -> consumed. Illegal unless currently
        heralded (rejects double consumption and consumption of an
        expired, cancelled, or never-heralded lease)."""
        if self.state is not LeaseState.HERALDED:
            raise ValueError(
                f"lease {self.lease_id} cannot be consumed from state {self.state}"
            )
        self.state = LeaseState.CONSUMED

    def expire(self) -> None:
        """Transition (requested|heralded) -> expired. Illegal once the
        lease has already reached a terminal state."""
        if self.state in TERMINAL_LEASE_STATES:
            raise ValueError(
                f"lease {self.lease_id} cannot expire from terminal state {self.state}"
            )
        self.state = LeaseState.EXPIRED

    def cancel(self) -> None:
        """Transition (requested|heralded) -> cancelled — the round-bound
        (S0) disposition of the §5 failure-cleanup cascade. Illegal once
        the lease has already reached a terminal state."""
        if self.state in TERMINAL_LEASE_STATES:
            raise ValueError(
                f"lease {self.lease_id} cannot be cancelled from terminal state {self.state}"
            )
        self.state = LeaseState.CANCELLED

    def is_fresh(self, now: float) -> bool:
        """True iff a heralded, unconsumed lease is still within its
        freshness bound at `now` — the pooling-policy (pre-generation)
        disposition check of the §5 failure-cleanup cascade / §8.2 pool
        maintenance: fresh leases return to the pool untouched (no state
        transition), stale ones are expired via `expire()`."""
        if self.state is not LeaseState.HERALDED or self.heralded_at is None:
            return False
        return (now - self.heralded_at) <= self.freshness_bound_s
