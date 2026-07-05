"""Engine state passed into Scheduler and InvariantChecker calls
(design spec §4, §8, §14).

Field types reference entities/ and models/ types by forward-reference
string only (never imported): core/ is the dependency-free foundation
package (§4's "dependency arrows point downward only"), and importing
entities/models here would invert that direction.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelBundle:
    decay: "DecayModel"
    memory_access: "MemoryAccessModel"
    heralding: "HeraldingModel"
    round_success: "RoundSuccessModel"
    decoder_service: "DecoderServiceModel"


@dataclass
class EngineState:
    """Read-only view passed into Scheduler calls. The engine constructs and
    mutates the underlying state; policies must not mutate it directly."""
    now: float
    epoch: "CalibrationEpoch"
    models: ModelBundle
    decoder_backlog: int
    active_reservations: dict["PathId", "SwitchPathReservation"]
    pool: dict[tuple["PathId", "CoherenceClass"], list["EntanglementLease"]]
    switch_capacity_c: int
    hold_until_consumption: bool
