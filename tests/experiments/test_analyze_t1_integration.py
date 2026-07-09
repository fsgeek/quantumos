"""Integration gate: stamped T1-control config -> real run -> full analyze
t1 pipeline (design §11). The gate covers the CONSUMER side of the trace
contract: every event type the pipeline reads must occur in the gate run."""
import json
from dataclasses import replace

from qsim.analysis.artifacts import sha256_of
from qsim.analysis.t1 import analyze_t1
from qsim.cli import load_config
from qsim.experiments.run import run

# Event types the T1 pipeline consumes (views: flux, latency, withdrawals,
# retry cadence; steady state is read from the header, which the run stamps).
_CONSUMED = {
    "pool.deposited",
    "pool.withdrawn",
    "reservation.acquired",
    "round.arrived",
}


def test_t1_control_gate(tmp_path):
    config = replace(load_config("examples/t1-control.toml"), max_sim_time_s=40.0)
    run_dir = run(config, tmp_path)

    report = analyze_t1(run_dir, mode="control")

    # Verdict: the prereg's declared-loss smoke run at this horizon/seed was
    # loud (lag-1 ACF -0.25..-0.35 vs ±0.098 band) — the control must PASS.
    assert report["verdict"] == "PASS"

    # Artifact chain (design §9).
    lags_path = run_dir / "analysis" / "predicted_lags_t1.json"
    report_path = run_dir / "analysis" / "t1_report.json"
    assert lags_path.exists() and report_path.exists()
    assert report["predicted_lags_sha256"] == sha256_of(lags_path)
    on_disk = json.loads(report_path.read_text())
    assert on_disk["verdict"] == "PASS"
    assert on_disk["ancestry"]["stamped_commit"]

    # Consumer-side taxonomy: every consumed type occurs in the gate run.
    present = {json.loads(line)["event_type"]
               for line in (run_dir / "events.jsonl").read_text().splitlines()}
    missing = _CONSUMED - present
    assert not missing, f"gate run never emits consumed types: {missing}"

    # Write-once survives a re-run of the analysis.
    before = lags_path.read_text()
    rerun = analyze_t1(run_dir, mode="control")
    assert lags_path.read_text() == before
    assert rerun["predicted_lags_reused"] is True
