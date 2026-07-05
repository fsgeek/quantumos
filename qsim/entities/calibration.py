"""CalibrationEpoch entity: a versioned, immutable parameter snapshot the
scheduler and model surfaces consult (design spec §5, §6)."""

from dataclasses import dataclass

from qsim.entities.module import PathId
from qsim.entities.qubit import CoherenceClass


@dataclass(frozen=True)
class CalibrationEpoch:
    epoch_id: str
    decay_rate_per_class: dict[CoherenceClass, float]
    memory_access_channel_s: float
    memory_access_wear_rate: float
    heralding_p_per_path: dict[PathId, float]
    heralded_fidelity_per_path: dict[PathId, float]
    round_success_logistic_midpoint: float
    round_success_logistic_slope: float
    round_success_slack_penalty_per_s: float
    decoder_service_rate: float
