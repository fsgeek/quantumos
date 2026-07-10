import pytest
from dataclasses import FrozenInstanceError

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig


def _epoch() -> CalibrationEpoch:
    a = PortId(module_id="mod-a", port_index=0)
    b = PortId(module_id="mod-b", port_index=0)
    path = make_path_id(a, b)
    return CalibrationEpoch(
        epoch_id="test-epoch",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.01, CoherenceClass.MEMORY: 0.001},
        memory_access_channel_s=0.001,
        memory_access_wear_rate=0.01,
        heralding_p_per_path={path: 0.5},
        heralded_fidelity_per_path={path: 0.95},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=10.0,
        round_success_slack_penalty_per_s=1.0,
        decoder_service_rate=5.0,
    )


def _base_kwargs(**overrides) -> dict:
    kwargs = dict(
        run_seed=1,
        scheduler="S0",
        epoch=_epoch(),
        arrival_rate_hz=1.0,
        leases_per_round=2,
        deadline_slack_s=1.0,
        switch_capacity_c=2,
        reconfig_delay_s=0.01,
        max_sim_time_s=100.0,
    )
    kwargs.update(overrides)
    return kwargs


def test_runconfig_valid_s0_construction_has_expected_defaults():
    config = RunConfig(**_base_kwargs())
    assert config.hold_until_consumption is False
    assert config.admission_theta is None
    assert config.pregen_low_water_mark is None
    assert config.decay_control_enabled is True
    assert config.memory_cost_control_enabled is True


def test_runconfig_valid_s1_construction_requires_admission_and_pregen_params():
    config = RunConfig(
        **_base_kwargs(scheduler="S1", admission_theta=0.8, pregen_low_water_mark=3)
    )
    assert config.admission_theta == 0.8
    assert config.pregen_low_water_mark == 3


def test_runconfig_s1_missing_admission_theta_raises():
    with pytest.raises(ValueError, match="admission_theta"):
        RunConfig(**_base_kwargs(scheduler="S1", pregen_low_water_mark=3))


def test_runconfig_s1_missing_pregen_low_water_mark_raises():
    with pytest.raises(ValueError, match="pregen_low_water_mark"):
        RunConfig(**_base_kwargs(scheduler="S1", admission_theta=0.8))


def test_runconfig_rejects_unknown_scheduler_tag():
    with pytest.raises(ValueError, match="scheduler"):
        RunConfig(**_base_kwargs(scheduler="S2"))


def test_runconfig_is_frozen():
    config = RunConfig(**_base_kwargs())
    with pytest.raises(FrozenInstanceError):
        config.run_seed = 2


def test_runconfig_path_policy_defaults_to_round_robin():
    config = RunConfig(**_base_kwargs())
    assert config.path_policy == "round_robin"


def test_runconfig_accepts_best_heralding_path_policy():
    config = RunConfig(**_base_kwargs(path_policy="best_heralding"))
    assert config.path_policy == "best_heralding"


def test_runconfig_rejects_unknown_path_policy():
    with pytest.raises(ValueError, match="path_policy"):
        RunConfig(**_base_kwargs(path_policy="fastest_first"))


def test_runconfig_herald_retry_interval_defaults_to_engine_constant():
    # The knob's default IS the old hard-coded constant: existing configs
    # must reproduce their traces byte-identically (2026-07-10
    # mechanism-correction note). Drift guard: the two literals live in
    # different layers (engine cannot import experiments.config).
    from qsim.core.engine import HERALD_RETRY_INTERVAL_S

    config = RunConfig(**_base_kwargs())
    assert config.herald_retry_interval_s == HERALD_RETRY_INTERVAL_S == 1e-4


def test_runconfig_accepts_herald_retry_interval_override():
    config = RunConfig(**_base_kwargs(herald_retry_interval_s=0.25))
    assert config.herald_retry_interval_s == 0.25


def test_runconfig_rejects_nonpositive_herald_retry_interval():
    with pytest.raises(ValueError, match="herald_retry_interval_s"):
        RunConfig(**_base_kwargs(herald_retry_interval_s=0.0))
