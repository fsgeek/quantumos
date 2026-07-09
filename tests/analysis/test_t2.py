"""T2: identical machinery on backlog slope, decoder-side named cycles
(design §4 last para; prereg T2)."""
import json

import pytest

from qsim.analysis.t2 import INHERITANCE_NOTE, analyze_t2


def _write_run_dir(tmp_path, rows, service_rate=5.0, horizon=80.0):
    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    with open(run_dir / "events.jsonl", "w") as f:
        for seq, (t, event_type) in enumerate(rows):
            f.write(json.dumps({
                "run_id": "r", "seq": seq, "sim_time": t,
                "event_type": event_type, "entity_id": f"j{seq}",
                "causal_parent_id": None, "payload": {},
            }) + "\n")
    (run_dir / "header.json").write_text(json.dumps({
        "run_id": "r", "run_seed": 1, "git_sha": "deadbeef",
        "schema_version": 1, "filtering": {"enabled": False},
        "steady_state": {"status": "CONVERGED", "warmup_cutoff_s": 0.0,
                          "evidence": {"horizon_s": horizon}},
        "config": {"scheduler": "S1",
                    "epoch": {"decoder_service_rate": service_rate}},
    }))
    return run_dir


def test_t2_structure_attributed_at_service_lag(tmp_path):
    # mu=5 -> bin 0.2s. Enqueue in even bins, complete in odd bins:
    # slope alternates -> lag-1 structure; service lag = round(0.2/0.2) = 1.
    rows = []
    for i in range(200):
        rows.append((0.4 * i + 0.1, "decoder.enqueued"))
        rows.append((0.4 * i + 0.3, "decoder.completed"))
    run_dir = _write_run_dir(tmp_path, sorted(rows, key=lambda r: r[0]))
    report = analyze_t2(run_dir)
    assert report["verdict"] == "T2-STRUCTURE-ATTRIBUTED"
    assert report["inheritance_note"] == INHERITANCE_NOTE
    assert (run_dir / "analysis" / "predicted_lags_t2.json").exists()
    assert (run_dir / "analysis" / "t2_report.json").exists()


def test_t2_no_structure_on_constant_slope(tmp_path):
    # One enqueue per bin, never completed: constant slope -> zero variance
    # -> refusal -> T2-NO-STRUCTURE is NOT declared; verdict withheld.
    rows = [(0.2 * i + 0.1, "decoder.enqueued") for i in range(400)]
    run_dir = _write_run_dir(tmp_path, rows)
    report = analyze_t2(run_dir)
    assert report["verdict"] is None
    assert report["refusals"]


def test_t2_empty_series_is_refusal_not_verdict(tmp_path):
    run_dir = _write_run_dir(tmp_path, [(1.0, "round.arrived")])
    report = analyze_t2(run_dir)
    assert report["verdict"] is None
    assert any("insufficient" in r or "empty" in r for r in report["refusals"])


def test_t2_busy_period_refusal_recorded_when_saturated(tmp_path):
    # lambda ~ 10/s vs mu=5 -> utilization >= 1: relaxation cycle refused.
    rows = [(0.1 * i, "decoder.enqueued") for i in range(800)]
    rows += [(0.1 * i + 0.05, "decoder.completed") for i in range(400)]
    run_dir = _write_run_dir(tmp_path, sorted(rows, key=lambda r: r[0]))
    report = analyze_t2(run_dir)
    assert any("utilization" in r for r in report["refusals"])
