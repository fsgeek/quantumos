"""QubitHandle entity: location, role class, calibration epoch, and the
lazily materialized fidelity-tracking state described in design spec §5 —
passive decay is evaluated by the engine from `state_held_since` at access
and evaluation instants; nothing here updates per tick."""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qsim.entities.calibration import CalibrationEpoch


class CoherenceClass(Enum):
    MESSENGER = "messenger"
    MEMORY = "memory"


@dataclass
class QubitHandle:
    qubit_id: str
    module_id: str
    coherence_class: CoherenceClass
    calibration_epoch: "CalibrationEpoch"
    state_held_since: float | None = None
    fidelity_at_hold_start: float | None = None
    access_count: int = 0  # drives MemoryAccessModel's linear wear (§6)

    def hold(self, at: float, fidelity: float) -> None:
        """Begin holding entangled state at the given fidelity. Illegal
        while already holding (must release first)."""
        if self.state_held_since is not None:
            raise ValueError(
                f"qubit {self.qubit_id} is already held since "
                f"{self.state_held_since}; cannot hold again at {at}"
            )
        self.state_held_since = at
        self.fidelity_at_hold_start = fidelity

    def release(self) -> None:
        """Stop holding entangled state. Illegal if not currently held."""
        if self.state_held_since is None:
            raise ValueError(f"qubit {self.qubit_id} is not currently held")
        self.state_held_since = None
        self.fidelity_at_hold_start = None

    def record_access(self) -> None:
        """Record a memory-access event; drives MemoryAccessModel wear."""
        self.access_count += 1
