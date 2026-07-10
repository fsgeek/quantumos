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
    assert "0.3" in arms[0.4]["recommend"]  # derived from p_bar=0.7, not hardcoded
    assert arms[0.0]["status"] == "ran"
    assert (tmp_path / "sweep_manifest.json").exists()
    dose = json.loads((tmp_path / "dose_response.json").read_text())
    (row,) = [r for r in dose["rows"] if r["delta"] == 0.0]
    assert "deadline_compliance" in row
    assert "fidelity_at_outcome" in row
    assert "monotonicity" in dose


def test_default_grid_is_the_prereg_grid():
    # As amended 2026-07-10 (pre-run): delta=0.3 is the widest feasible
    # half-spread at p_bar=0.7; delta=0.4 stays so the refusal is recorded.
    assert S1_DELTAS == (0.0, 0.1, 0.2, 0.3, 0.4)


def test_dose_response_rows_sorted_by_delta_regardless_of_request_order(tmp_path):
    """Monotonicity is a function of delta, not request order."""
    run_sweep("examples/t1-open.toml", tmp_path,
              deltas=(0.2, 0.0), max_sim_time_s=5.0)
    dose = json.loads((tmp_path / "dose_response.json").read_text())
    assert [r["delta"] for r in dose["rows"]] == [0.0, 0.2]


def test_dose_response_monotonicity_reports_both_directions(tmp_path):
    """Direction-blind monotonicity misleads when the swept policy expects an
    INCREASING dose (argmax policies improve with spread at fixed mean) —
    review round 3, 2026-07-10. The artifact reports both directions and
    leaves expectation to the reader/prereg."""
    run_sweep("examples/t1-open.toml", tmp_path,
              deltas=(0.0, 0.2), max_sim_time_s=5.0)
    dose = json.loads((tmp_path / "dose_response.json").read_text())
    mono = dose["monotonicity"]
    assert "monotone_nonincreasing" in mono
    assert "monotone_nondecreasing" in mono
    assert "direction" in mono["note"]
