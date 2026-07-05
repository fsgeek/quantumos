from dataclasses import dataclass

from qsim.entities import CalibrationEpoch

_VALID_SCHEDULERS = ("S0", "S1")


@dataclass(frozen=True)
class RunConfig:
    run_seed: int
    scheduler: str  # "S0" | "S1"
    epoch: CalibrationEpoch
    arrival_rate_hz: float
    leases_per_round: int
    deadline_slack_s: float
    switch_capacity_c: int
    reconfig_delay_s: float
    max_sim_time_s: float
    hold_until_consumption: bool = False
    admission_theta: float | None = None       # required if scheduler == "S1" (§8.1)
    pregen_low_water_mark: int | None = None   # required if scheduler == "S1" (§8.2)
    decay_control_enabled: bool = True         # False => NoDecayModel (§6, §15)
    memory_cost_control_enabled: bool = True   # False => ZeroCostMemoryAccessModel (§6, §15)

    def __post_init__(self) -> None:
        if self.scheduler not in _VALID_SCHEDULERS:
            raise ValueError(
                f"scheduler must be one of {_VALID_SCHEDULERS}, got {self.scheduler!r}"
            )
        if self.scheduler == "S1":
            if self.admission_theta is None:
                raise ValueError(
                    "admission_theta is required when scheduler == 'S1' (spec §8.1)"
                )
            if self.pregen_low_water_mark is None:
                raise ValueError(
                    "pregen_low_water_mark is required when scheduler == 'S1' (spec §8.2)"
                )
