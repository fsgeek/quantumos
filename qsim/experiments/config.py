from dataclasses import dataclass

from qsim.entities import CalibrationEpoch

_VALID_SCHEDULERS = ("S0", "S1")
_VALID_PATH_POLICIES = ("round_robin", "best_heralding")


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
    retry_cap: int | None = None               # None => unlimited retries (§9 closed-loop,
    #                                            current behaviour); N => a round is dropped
    #                                            after N retries. A sweep knob for isolating
    #                                            whether the retry storm self-sustains a
    #                                            congestion collapse (spiral) vs. plain overload.
    path_policy: str = "round_robin"           # B1 seam: "round_robin" (bit-identical
    #                                            pre-B1 default) | "best_heralding"
    #                                            (comparative: argmax heralding_p among
    #                                            epoch-enumerated viable paths). Trailing
    #                                            defaulted field: existing construction
    #                                            sites and events.jsonl are untouched; the
    #                                            field reaches header.json via _json_safe.
    herald_retry_interval_s: float = 1e-4      # Failed-herald attempt cycle time (the
    #                                            in-place retry spacing on a configured
    #                                            path). Default IS the old hard-coded
    #                                            engine constant so existing configs
    #                                            reproduce traces byte-identically. The
    #                                            binding knob for whether path-quality
    #                                            spread can reach outcomes: penalty per
    #                                            round ~ (E[1/p]-1/p_bar) * this value
    #                                            (2026-07-10 mechanism-correction note).

    def __post_init__(self) -> None:
        if self.path_policy not in _VALID_PATH_POLICIES:
            raise ValueError(
                f"path_policy must be one of {_VALID_PATH_POLICIES}, got {self.path_policy!r}"
            )
        if self.scheduler not in _VALID_SCHEDULERS:
            raise ValueError(
                f"scheduler must be one of {_VALID_SCHEDULERS}, got {self.scheduler!r}"
            )
        if self.herald_retry_interval_s <= 0.0:
            raise ValueError(
                f"herald_retry_interval_s must be positive, got {self.herald_retry_interval_s!r}"
            )
        if self.retry_cap is not None and (not isinstance(self.retry_cap, int) or self.retry_cap < 0):
            raise ValueError(
                f"retry_cap must be a non-negative int or None, got {self.retry_cap!r}"
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
