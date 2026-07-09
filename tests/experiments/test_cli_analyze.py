"""CLI wiring for analyze (design §3 CLI)."""
import json

from qsim.cli import main


def _t3_run_dir(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    rows = [
        (0.0, "lease.requested", "L1", {"round_id": "r1"}),
        (0.5, "lease.heralded", "L1", {"round_id": "r1", "fidelity_at_herald": 0.9}),
        (1.0, "lease.requested", "L2", {"round_id": "r2"}),
        (1.5, "lease.heralded", "L2", {"round_id": "r2", "fidelity_at_herald": 0.8}),
        (2.0, "lease.consumed", "L1", {"round_id": "r1", "fidelity_at_consumption": 0.0}),
        (3.0, "lease.consumed", "L2", {"round_id": "r2", "fidelity_at_consumption": 0.0}),
    ]
    with open(run_dir / "events.jsonl", "w") as f:
        for seq, (t, event_type, entity_id, payload) in enumerate(rows):
            f.write(json.dumps({
                "run_id": "r", "seq": seq, "sim_time": t,
                "event_type": event_type, "entity_id": entity_id,
                "causal_parent_id": None, "payload": payload,
            }) + "\n")
    (run_dir / "header.json").write_text(json.dumps({
        "run_id": "r", "run_seed": 1, "git_sha": "deadbeef",
        "schema_version": 1, "filtering": {"enabled": False},
        "steady_state": {"status": "CONVERGED", "warmup_cutoff_s": 0.0,
                          "evidence": {"horizon_s": 3.0}},
        "config": {"scheduler": "S1",
                    "epoch": {"decay_rate_per_class": {"messenger": 0.01}}},
    }))
    return run_dir


def test_analyze_t3_end_to_end(tmp_path, capsys):
    run_dir = _t3_run_dir(tmp_path)
    assert main(["analyze", "t3", str(run_dir)]) == 0
    out = capsys.readouterr().out
    assert "verdict" in out.lower()
    assert (run_dir / "analysis" / "t3_report.json").exists()


def test_analyze_t1_open_without_companion_exits_nonzero(tmp_path):
    run_dir = _t3_run_dir(tmp_path)  # any run dir; refusal fires first
    assert main(["analyze", "t1", str(run_dir), "--mode", "open"]) == 1


def test_analyze_parser_rejects_bad_mode(tmp_path):
    import pytest
    with pytest.raises(SystemExit):
        main(["analyze", "t1", str(tmp_path), "--mode", "sideways"])


def test_analyze_t3_refusal_exits_nonzero(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "events.jsonl").write_text("")
    import json
    (run_dir / "header.json").write_text(json.dumps({
        "run_id": "r", "run_seed": 1, "git_sha": "deadbeef",
        "schema_version": 1, "filtering": {"enabled": False},
        "steady_state": {"status": "CONVERGED", "warmup_cutoff_s": 0.0,
                          "evidence": {"horizon_s": 1.0}},
        "config": {"scheduler": "S1",
                    "epoch": {"decay_rate_per_class": {"messenger": 0.01}}},
    }))
    assert main(["analyze", "t3", str(run_dir)]) == 1
