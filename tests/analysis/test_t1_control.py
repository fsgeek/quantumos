"""T1 control pipeline on synthetic run dirs with engineered ACF ground
truth (design §4, §6, §11)."""
import json

import pytest

from qsim.analysis.t1 import AnalysisRefusal, analyze_t1, choose_bin_s, lag_window

KEY_A = [[["M0", 0], ["M1", 0]], "messenger"]
PATH_A = [["M0", 0], ["M1", 0]]


def _write_run_dir(tmp_path, rows, steady_status="CONVERGED", warmup=0.0):
    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    with open(run_dir / "events.jsonl", "w") as f:
        for seq, (t, event_type, entity_id, payload) in enumerate(rows):
            f.write(json.dumps({
                "run_id": "r", "seq": seq, "sim_time": t,
                "event_type": event_type, "entity_id": entity_id,
                "causal_parent_id": None, "payload": payload,
            }) + "\n")
    (run_dir / "header.json").write_text(json.dumps({
        "run_id": "r", "run_seed": 7, "git_sha": "deadbeef",
        "schema_version": 1, "filtering": {"enabled": False},
        "steady_state": {"status": steady_status, "warmup_cutoff_s": warmup,
                          "evidence": {"horizon_s": 80.0}},
        "config": {"pregen_low_water_mark": 2, "arrival_rate_hz": 5.0,
                    "scheduler": "S1", "epoch": {"decoder_service_rate": 1000.0,
                                                  "decay_rate_per_class": {"messenger": 0.0}}},
    }))
    return run_dir


def _loud_rows(n=100):
    """Deposit in even 0.4s bins, withdraw in odd bins: flux alternates
    +/-, lag-1 ACF ~ -1, replenishment latency exactly 0.4 -> bin 0.4,
    replenishment predicted lag 1, in window, negative. Control PASS."""
    rows = []
    for i in range(n):
        base = 0.8 * i
        rows.append((base - 0.2 if i else 0.0, "reservation.acquired", f"res{i}",
                     {"round_id": None, "lease_id": f"R{i}:L",
                      "request_id": f"R{i}", "path_id": PATH_A}))
        rows.append((base + 0.2, "pool.deposited", f"R{i}:L",
                     {"key": KEY_A, "depth": 1, "lease_id": f"R{i}:L",
                      "round_id": None, "source": "replenish"}))
        rows.append((base + 0.6, "pool.withdrawn", f"R{i}:L",
                     {"key": KEY_A, "depth": 0, "pooled_lease_id": f"R{i}:L",
                      "lease_id": f"L{i}", "round_id": f"r{i}"}))
    return sorted(rows, key=lambda r: r[0])


def test_choose_bin_s_one_significant_figure():
    assert choose_bin_s([0.09, 0.11, 0.12]) == pytest.approx(0.1)
    assert choose_bin_s([2.0, 2.6]) == pytest.approx(2.0)
    assert choose_bin_s([0.5], override=0.25) == 0.25


def test_lag_window_covers_p25_p75_min_three_bins():
    assert lag_window([0.4] * 10, bin_s=0.4) == (1, 3)      # widened to 3
    assert lag_window([1.0, 2.0, 3.0, 4.0], bin_s=0.5) == (3, 7)


def test_divergent_run_is_transient_and_unread(tmp_path):
    run_dir = _write_run_dir(tmp_path, _loud_rows(), steady_status="DIVERGENT")
    report = analyze_t1(run_dir, mode="control")
    assert report["verdict"] == "TRANSIENT"
    assert "pools" not in report  # a transient is not read


def test_control_pass_on_loud_structure(tmp_path):
    run_dir = _write_run_dir(tmp_path, _loud_rows())
    report = analyze_t1(run_dir, mode="control")
    assert report["verdict"] == "PASS"
    assert (run_dir / "analysis" / "predicted_lags_t1.json").exists()
    assert (run_dir / "analysis" / "t1_report.json").exists()
    (pool_stats,) = report["pools"].values()
    assert 1 in pool_stats["significant_in_window"]
    assert pool_stats["acf"][0] < 0


def test_control_insensitive_on_flat_series(tmp_path):
    """Deposits only, perfectly regular: constant flux -> zero variance ->
    per-pool refusal -> INSENSITIVE (refusals are data, design §10)."""
    rows = []
    for i in range(200):
        # deposit at bin CENTER (i*0.4 + 0.2): exactly one deposit per 0.4s
        # bin, so the flux series is truly constant (zero variance) — a
        # deposit on a bin EDGE would leave an empty first bin and give the
        # series spurious variance.
        rows.append((max(0.0, i * 0.4 - 0.2), "reservation.acquired", f"res{i}",
                     {"round_id": None, "lease_id": f"R{i}:L",
                      "request_id": f"R{i}", "path_id": PATH_A}))
        rows.append((i * 0.4 + 0.2, "pool.deposited", f"R{i}:L",
                     {"key": KEY_A, "depth": i, "lease_id": f"R{i}:L",
                      "round_id": None, "source": "replenish"}))
    run_dir = _write_run_dir(tmp_path, sorted(rows, key=lambda r: r[0]))
    report = analyze_t1(run_dir, mode="control")
    assert report["verdict"] == "INSENSITIVE"
    assert report["directive"] == "do not run the open regime"
    assert report["refusals"]


def test_no_replenishment_samples_is_hard_refusal(tmp_path):
    rows = [(0.5, "pool.deposited", "X", {"key": KEY_A, "depth": 1,
             "lease_id": "X", "round_id": "r0", "source": "round_return"})]
    run_dir = _write_run_dir(tmp_path, rows)
    with pytest.raises(AnalysisRefusal):
        analyze_t1(run_dir, mode="control")
    report = json.loads((run_dir / "analysis" / "t1_report.json").read_text())
    assert report["verdict"] is None
    assert report["refusals"]  # recorded in the artifact, not just stderr


def test_write_once_predictions_survive_rerun(tmp_path):
    run_dir = _write_run_dir(tmp_path, _loud_rows())
    analyze_t1(run_dir, mode="control")
    first = (run_dir / "analysis" / "predicted_lags_t1.json").read_text()
    report = analyze_t1(run_dir, mode="control")
    assert (run_dir / "analysis" / "predicted_lags_t1.json").read_text() == first
    assert report["predicted_lags_reused"] is True
