import json

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.experiments.run import build_model_bundle, build_scheduler, run
from qsim.models.decay import ExponentialDecayModel, NoDecayModel
from qsim.models.memory_access import LinearMemoryAccessModel, ZeroCostMemoryAccessModel
from qsim.policies.s0 import S0Scheduler
from qsim.policies.s1 import S1Scheduler


def _epoch() -> CalibrationEpoch:
    a = PortId(module_id="mod-a", port_index=0)
    b = PortId(module_id="mod-b", port_index=0)
    path = make_path_id(a, b)
    return CalibrationEpoch(
        epoch_id="run-test-epoch",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.01, CoherenceClass.MEMORY: 0.001},
        memory_access_channel_s=0.001,
        memory_access_wear_rate=0.01,
        heralding_p_per_path={path: 0.7},
        heralded_fidelity_per_path={path: 0.95},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=10.0,
        round_success_slack_penalty_per_s=1.0,
        decoder_service_rate=5.0,
    )


def _s0_config(**overrides) -> RunConfig:
    fields = dict(
        run_seed=42,
        scheduler="S0",
        epoch=_epoch(),
        arrival_rate_hz=1.0,
        leases_per_round=1,
        deadline_slack_s=5.0,
        switch_capacity_c=1,
        reconfig_delay_s=0.01,
        max_sim_time_s=20.0,
    )
    fields.update(overrides)
    return RunConfig(**fields)


def test_run_produces_a_run_directory_with_header_and_events(tmp_path):
    config = _s0_config()
    run_dir = run(config, tmp_path)

    assert run_dir.is_dir()
    header_path = run_dir / "header.json"
    events_path = run_dir / "events.jsonl"
    assert header_path.exists()
    assert events_path.exists()

    header = json.loads(header_path.read_text())
    assert header["run_seed"] == 42

    lines = events_path.read_text().strip().splitlines()
    assert len(lines) > 0
    first_event = json.loads(lines[0])
    assert "event_type" in first_event
    assert "sim_time" in first_event


def test_run_with_s1_scheduler_wires_admission_and_pregen_params(tmp_path):
    config = _s0_config(scheduler="S1", admission_theta=0.5, pregen_low_water_mark=2)
    run_dir = run(config, tmp_path)
    events_path = run_dir / "events.jsonl"
    assert events_path.exists()

    events = [json.loads(line) for line in events_path.read_text().strip().splitlines()]
    assert len(events) > 0

    # The S1 AdmissionMixin (§8.1) — not the S0 baseline — must actually make the
    # admission decisions during the run: its decision `reason` embeds the
    # configured theta_admit, so its presence in an admitted/deferred event
    # proves admission_theta was threaded through build_scheduler into the live
    # decision path (S0's reasons never mention theta_admit). A weak
    # "events non-empty" check would pass even if the S1 params were ignored.
    admission_events = [
        e for e in events if e["event_type"] in ("round.admitted", "round.deferred")
    ]
    assert admission_events, "expected at least one admission decision event"
    assert any(
        "theta_admit=0.5" in (e["payload"].get("reason") or "")
        for e in admission_events
    ), "no admission decision carried the S1 admission_theta — params not wired"


def test_build_scheduler_wires_admission_theta_and_low_water_mark_into_s1():
    config = _s0_config(scheduler="S1", admission_theta=0.5, pregen_low_water_mark=2)
    scheduler = build_scheduler(config)
    # §8.1 AdmissionMixin threshold and §8.2 PregenMixin low-water-mark must be
    # populated from the config, not left at defaults.
    assert scheduler._theta_admit == 0.5
    assert scheduler._low_water_mark == 2


def test_build_scheduler_returns_s0_scheduler_for_s0_tag():
    assert isinstance(build_scheduler(_s0_config()), S0Scheduler)


def test_build_scheduler_returns_s1_scheduler_for_s1_tag():
    config = _s0_config(scheduler="S1", admission_theta=0.5, pregen_low_water_mark=2)
    assert isinstance(build_scheduler(config), S1Scheduler)


def test_build_model_bundle_honors_decay_control_flag():
    on = build_model_bundle(_s0_config(decay_control_enabled=True))
    off = build_model_bundle(_s0_config(decay_control_enabled=False))
    assert isinstance(on.decay, ExponentialDecayModel)
    assert isinstance(off.decay, NoDecayModel)


def test_build_model_bundle_honors_memory_cost_control_flag():
    on = build_model_bundle(_s0_config(memory_cost_control_enabled=True))
    off = build_model_bundle(_s0_config(memory_cost_control_enabled=False))
    assert isinstance(on.memory_access, LinearMemoryAccessModel)
    assert isinstance(off.memory_access, ZeroCostMemoryAccessModel)
