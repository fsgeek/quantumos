"""Integration gate for the steady-state / convergence classifier (spec §13).

Runs the FULL pipeline (`qsim.experiments.run.run`) on a benign and a collapse
config and asserts the classifier — verified against the REAL trace, not a
hand-built fixture — separates them, and that the verdict is stamped into
header.json. Config shape copied from tests/experiments/test_views_integration.py
with the logistic midpoint/slope set so decay actually bites.
"""
import json
from pathlib import Path

import pytest

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.experiments.run import run
from qsim.observe.steady_state import (
    SteadyStateError,
    assert_or_flag_steady_state,
    compute_steady_state,
)

_PA = make_path_id(PortId("M0", 0), PortId("M1", 0))


def _epoch(decay_rate: float) -> CalibrationEpoch:
    return CalibrationEpoch(
        epoch_id="e",
        decay_rate_per_class={
            CoherenceClass.MESSENGER: decay_rate,
            CoherenceClass.MEMORY: decay_rate,
        },
        memory_access_channel_s=0.0,
        memory_access_wear_rate=0.0,
        heralding_p_per_path={_PA: 1.0},
        heralded_fidelity_per_path={_PA: 0.9},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=20.0,
        round_success_slack_penalty_per_s=0.0,
        decoder_service_rate=5.0,
    )


def _config(decay_rate: float) -> RunConfig:
    return RunConfig(
        run_seed=7,
        scheduler="S0",
        epoch=_epoch(decay_rate),
        arrival_rate_hz=2.0,
        leases_per_round=1,
        deadline_slack_s=100.0,
        switch_capacity_c=1,
        reconfig_delay_s=0.0,
        max_sim_time_s=200.0,
        decay_control_enabled=True,
    )


def test_benign_run_is_converged(tmp_path):
    run_dir = run(_config(decay_rate=0.1), tmp_path / "benign")
    verdict = compute_steady_state(run_dir / "events.jsonl")
    assert verdict.status == "CONVERGED", verdict.evidence
    # The loud helper must NOT raise on a converged run.
    v2 = assert_or_flag_steady_state(run_dir)
    assert v2.status == "CONVERGED"


def test_collapse_run_is_divergent(tmp_path):
    run_dir = run(_config(decay_rate=1.0), tmp_path / "collapse")
    verdict = compute_steady_state(run_dir / "events.jsonl")
    assert verdict.status == "DIVERGENT", verdict.evidence
    # The loud helper MUST raise on a divergent run (never silently trust it).
    with pytest.raises(SteadyStateError):
        assert_or_flag_steady_state(run_dir)


def test_header_carries_steady_state_block(tmp_path):
    for name, decay, expected in [("benign", 0.1, "CONVERGED"), ("collapse", 1.0, "DIVERGENT")]:
        run_dir = run(_config(decay_rate=decay), tmp_path / name)
        header = json.loads((run_dir / "header.json").read_text())
        assert "steady_state" in header, "header must carry a steady_state block"
        block = header["steady_state"]
        assert block["status"] == expected
        assert "warmup_cutoff_s" in block
        assert "evidence" in block
        assert block["evidence"]["relative_slope_tolerance"] == pytest.approx(0.02)
