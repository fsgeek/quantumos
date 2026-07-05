"""v1 MemoryAccessModel implementations (spec sec 6): linear per-access wear
and the required zero-cost control."""
from __future__ import annotations

from qsim.entities.calibration import CalibrationEpoch
from qsim.entities.qubit import QubitHandle
from qsim.models.protocols import AccessCost


class LinearMemoryAccessModel:
    """Each access costs a fixed electron-channel duration and linearly wears
    retention: retention_factor = max(0.0, 1 - wear_rate * access_count).
    Floored at zero to keep retention_factor in [0,1] per sec 6's convention."""

    def access_cost(self, qubit: QubitHandle,
                    epoch: CalibrationEpoch) -> AccessCost:
        wear = epoch.memory_access_wear_rate * qubit.access_count
        retention_factor = max(0.0, 1.0 - wear)
        return AccessCost(electron_channel_s=epoch.memory_access_channel_s,
                          retention_factor=retention_factor)


class ZeroCostMemoryAccessModel:
    """Required control (spec sec 6): free reads -- zero channel time, no
    retention loss, regardless of access history. Neutralizes the
    memory-access surface entirely."""

    def access_cost(self, qubit: QubitHandle,
                    epoch: CalibrationEpoch) -> AccessCost:
        return AccessCost(electron_channel_s=0.0, retention_factor=1.0)
