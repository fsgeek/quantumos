"""SyndromeRound entity: lifecycle pending -> (admitted | deferred |
dropped); admitted -> (completed_in_deadline | completed_late | failed)
(design spec §5). `fail()` is the transition that triggers the §5
failure-cleanup cascade on the round's resources — decoder jobs, switch
reservations, and leases — each disposed via its own entity's method
elsewhere in this package; orchestrating the cascade itself is core/'s job."""

from dataclasses import dataclass
from enum import Enum


class RoundState(Enum):
    PENDING = "pending"
    ADMITTED = "admitted"
    DEFERRED = "deferred"
    DROPPED = "dropped"
    COMPLETED_IN_DEADLINE = "completed_in_deadline"
    COMPLETED_LATE = "completed_late"
    FAILED = "failed"


TERMINAL_ROUND_STATES = frozenset(
    {
        RoundState.DROPPED,
        RoundState.COMPLETED_IN_DEADLINE,
        RoundState.COMPLETED_LATE,
        RoundState.FAILED,
    }
)


@dataclass
class SyndromeRound:
    round_id: str
    lease_ids: list[str]
    qubit_ids: list[str]
    arrival_time: float
    deadline: float
    retry_ordinal: int = 0
    state: RoundState = RoundState.PENDING

    def admit(self) -> None:
        """Transition pending -> admitted. Illegal from any other state."""
        if self.state is not RoundState.PENDING:
            raise ValueError(
                f"round {self.round_id} cannot be admitted from state {self.state}"
            )
        self.state = RoundState.ADMITTED

    def defer(self) -> None:
        """Transition pending -> deferred. Illegal from any other state."""
        if self.state is not RoundState.PENDING:
            raise ValueError(
                f"round {self.round_id} cannot be deferred from state {self.state}"
            )
        self.state = RoundState.DEFERRED

    def drop(self) -> None:
        """Transition pending -> dropped. Illegal from any other state."""
        if self.state is not RoundState.PENDING:
            raise ValueError(
                f"round {self.round_id} cannot be dropped from state {self.state}"
            )
        self.state = RoundState.DROPPED

    def complete_in_deadline(self) -> None:
        """Transition admitted -> completed_in_deadline. Illegal unless
        currently admitted."""
        if self.state is not RoundState.ADMITTED:
            raise ValueError(
                f"round {self.round_id} cannot complete-in-deadline from state {self.state}"
            )
        self.state = RoundState.COMPLETED_IN_DEADLINE

    def complete_late(self) -> None:
        """Transition admitted -> completed_late. Illegal unless currently
        admitted."""
        if self.state is not RoundState.ADMITTED:
            raise ValueError(
                f"round {self.round_id} cannot complete-late from state {self.state}"
            )
        self.state = RoundState.COMPLETED_LATE

    def fail(self) -> None:
        """Transition admitted -> failed. Illegal unless currently
        admitted."""
        if self.state is not RoundState.ADMITTED:
            raise ValueError(
                f"round {self.round_id} cannot fail from state {self.state}"
            )
        self.state = RoundState.FAILED

    def is_terminal(self) -> bool:
        """True once the round has reached any terminal state."""
        return self.state in TERMINAL_ROUND_STATES
