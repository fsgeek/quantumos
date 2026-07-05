"""qsim.entities: inert dataclass object model with lifecycle state
machines and no embedded decisions (design spec §4, §5).

Re-exports the package's public API so callers can use the package-level
import path the frozen interface contract assumes
(``from qsim.entities import CalibrationEpoch, ...``) as well as the
submodule path (``from qsim.entities.calibration import CalibrationEpoch``).

Import order below respects the one intra-package dependency that resolves
at import time: ``calibration`` imports ``CoherenceClass`` from ``qubit``,
so ``qubit`` is imported first. (``qubit`` itself references
``CalibrationEpoch`` only via a string annotation, so it carries no runtime
dependency back on ``calibration``.)
"""

from qsim.entities.module import Module, PathId, PortId, make_path_id
from qsim.entities.qubit import CoherenceClass, QubitHandle
from qsim.entities.calibration import CalibrationEpoch
from qsim.entities.lease import EntanglementLease, LeaseState
from qsim.entities.round import RoundState, SyndromeRound
from qsim.entities.decoder import DecoderJob
from qsim.entities.reservation import ReservationState, SwitchPathReservation
from qsim.entities.pauli_frame import PauliFrameToken

__all__ = [
    "Module",
    "PathId",
    "PortId",
    "make_path_id",
    "CoherenceClass",
    "QubitHandle",
    "CalibrationEpoch",
    "EntanglementLease",
    "LeaseState",
    "RoundState",
    "SyndromeRound",
    "DecoderJob",
    "ReservationState",
    "SwitchPathReservation",
    "PauliFrameToken",
]
