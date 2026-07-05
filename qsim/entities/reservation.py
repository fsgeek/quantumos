"""SwitchPathReservation entity: lifecycle
acquired -> configuring -> active -> released (design spec §7). Release is
also the §5 failure-cleanup cascade's disposition for reservations held on
behalf of a failed or cancelled round, and can occur directly from
`acquired` or `configuring` if the round is cancelled before heralding
attempts ever start."""

from dataclasses import dataclass
from enum import Enum

from qsim.entities.module import PathId


class ReservationState(Enum):
    ACQUIRED = "acquired"
    CONFIGURING = "configuring"
    ACTIVE = "active"
    RELEASED = "released"


@dataclass
class SwitchPathReservation:
    path_id: PathId
    holder_id: str  # round_id or lease_id
    acquired_at: float
    released_at: float | None = None
    state: ReservationState = ReservationState.ACQUIRED

    def configure(self) -> None:
        """Transition acquired -> configuring. Illegal from any other
        state."""
        if self.state is not ReservationState.ACQUIRED:
            raise ValueError(
                f"reservation on {self.path_id} cannot configure from state {self.state}"
            )
        self.state = ReservationState.CONFIGURING

    def activate(self) -> None:
        """Transition configuring -> active. Illegal from any other
        state."""
        if self.state is not ReservationState.CONFIGURING:
            raise ValueError(
                f"reservation on {self.path_id} cannot activate from state {self.state}"
            )
        self.state = ReservationState.ACTIVE

    def release(self, at: float) -> None:
        """Transition (acquired | configuring | active) -> released, at
        the first of heralding success, attempt-window/deadline expiry, or
        round cancellation (design spec §7). Illegal if already released
        (rejects a reservation being released twice, which would otherwise
        mask a resource leak)."""
        if self.state is ReservationState.RELEASED:
            raise ValueError(
                f"reservation on {self.path_id} already released at {self.released_at}"
            )
        self.released_at = at
        self.state = ReservationState.RELEASED
