"""S1 sweep: pinned grid, infeasible-arm refusal, dose-response artifact
(design §8; prereg S1 + plan finding #2)."""
import json

import pytest

from qsim.cli import load_config
from qsim.experiments.sweep import (
    InfeasibleArm,
    S1_DELTAS,
    build_arm_config,
    heralding_spread,
    run_sweep,
)


def test_heralding_spread_matches_prereg_example():
    assert heralding_spread(0.7, 0.2) == pytest.approx((0.5, 0.6333333333333333,
                                                         0.7666666666666666, 0.9))
    assert heralding_spread(0.7, 0.0) == pytest.approx((0.7, 0.7, 0.7, 0.7))


def test_heralding_spread_delta_04_is_infeasible():
    with pytest.raises(InfeasibleArm):
        heralding_spread(0.7, 0.4)  # 1.1 > 1 (plan finding #2)


def test_build_arm_config_keeps_mean_and_reassigns_paths():
    base = load_config("examples/t1-open.toml")
    arm = build_arm_config(base, 0.2)
    ps = sorted(arm.epoch.heralding_p_per_path.values())
    assert ps == pytest.approx([0.5, 0.6333333333333333, 0.7666666666666666, 0.9])
    assert sum(ps) / 4 == pytest.approx(0.7)
    assert arm.run_seed == base.run_seed  # everything else untouched
    assert arm.epoch.heralded_fidelity_per_path == base.epoch.heralded_fidelity_per_path


def test_run_sweep_records_infeasible_arm_and_runs_feasible(tmp_path):
    manifest = run_sweep("examples/t1-open.toml", tmp_path,
                         deltas=(0.0, 0.4), max_sim_time_s=5.0)
    arms = {arm["delta"]: arm for arm in manifest["arms"]}
    assert arms[0.4]["status"] == "infeasible"
    assert "amendment" in arms[0.4]["recommend"]
    assert arms[0.0]["status"] == "ran"
    assert (tmp_path / "sweep_manifest.json").exists()
    dose = json.loads((tmp_path / "dose_response.json").read_text())
    (row,) = [r for r in dose["rows"] if r["delta"] == 0.0]
    assert "deadline_compliance" in row
    assert "fidelity_at_outcome" in row
    assert "monotonicity" in dose


def test_default_grid_is_the_prereg_grid():
    assert S1_DELTAS == (0.0, 0.1, 0.2, 0.4)
