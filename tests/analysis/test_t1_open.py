"""T1 open regime: attribution-gated verdicts + knob-motion companion
(design §6-§7)."""
import json

import pytest

from qsim.analysis.t1 import AnalysisRefusal, analyze_t1

KEY_A = [[["M0", 0], ["M1", 0]], "messenger"]
PATH_A = [["M0", 0], ["M1", 0]]


def _write_run_dir(tmp_path, name, rows, warmup=0.0):
    run_dir = tmp_path / name
    run_dir.mkdir(exist_ok=True)
    with open(run_dir / "events.jsonl", "w") as f:
        for seq, (t, event_type, entity_id, payload) in enumerate(rows):
            f.write(json.dumps({
                "run_id": name, "seq": seq, "sim_time": t,
                "event_type": event_type, "entity_id": entity_id,
                "causal_parent_id": None, "payload": payload,
            }) + "\n")
    (run_dir / "header.json").write_text(json.dumps({
        "run_id": name, "run_seed": 11, "git_sha": "deadbeef",
        "schema_version": 1, "filtering": {"enabled": False},
        "steady_state": {"status": "CONVERGED", "warmup_cutoff_s": warmup,
                          "evidence": {"horizon_s": 80.0}},
        "config": {"pregen_low_water_mark": 2, "arrival_rate_hz": 1.0,
                    "scheduler": "S1", "epoch": {"decoder_service_rate": 5.0,
                                                  "decay_rate_per_class": {"messenger": 0.01}}},
    }))
    return run_dir


def _periodic_rows(n, period_s, deposit_offset, withdraw_offset, latency=0.4):
    rows = []
    for i in range(n):
        base = period_s * i
        rows.append((max(0.0, base + deposit_offset - latency),
                     "reservation.acquired", f"res{i}",
                     {"round_id": None, "lease_id": f"R{i}:L",
                      "request_id": f"R{i}", "path_id": PATH_A}))
        rows.append((base + deposit_offset, "pool.deposited", f"R{i}:L",
                     {"key": KEY_A, "depth": 1, "lease_id": f"R{i}:L",
                      "round_id": None, "source": "replenish"}))
        rows.append((base + withdraw_offset, "pool.withdrawn", f"R{i}:L",
                     {"key": KEY_A, "depth": 0, "pooled_lease_id": f"R{i}:L",
                      "lease_id": f"L{i}", "round_id": f"r{i}"}))
    return sorted(rows, key=lambda r: r[0])


def test_open_requires_companion(tmp_path):
    primary = _write_run_dir(tmp_path, "primary",
                             _periodic_rows(100, 0.8, 0.2, 0.6))
    with pytest.raises(AnalysisRefusal):
        analyze_t1(primary, mode="open")
    report = json.loads((primary / "analysis" / "t1_report.json").read_text())
    assert any("companion" in r for r in report["refusals"])


def test_open_field_earned_when_all_lags_attributed(tmp_path):
    # lag-1 structure; replenishment cycle 0.4s / bin 0.4 -> predicted lag 1.
    primary = _write_run_dir(tmp_path, "primary",
                             _periodic_rows(100, 0.8, 0.2, 0.6))
    companion = _write_run_dir(tmp_path, "companion",
                               _periodic_rows(50, 1.6, 0.2, 0.6))
    report = analyze_t1(primary, mode="open", companion_dir=companion)
    assert report["verdict"] == "FIELD-EARNED"
    assert "field-earned at this operating point" in report["caveat"]
    assert "knob_motion" in report
    km = report["knob_motion"]
    assert set(km) == {"primary", "companion"}
    (primary_stats,) = km["primary"].values()
    assert {"mean_depth", "flux_variance", "n_depth_events"} <= set(primary_stats)


def test_open_attribution_failed_on_unpredicted_lag(tmp_path):
    # Period 6 bins (2.4s): significant lag 3 in window [1,3]; predicted
    # cycles: replenishment=1, low-water = mean gap 2.4 x 2 = 4.8s -> lag 12.
    # Lag 3 is >1 bin from both -> ATTRIBUTION-FAILED.
    primary = _write_run_dir(tmp_path, "primary",
                             _periodic_rows(100, 2.4, 0.2, 1.4))
    companion = _write_run_dir(tmp_path, "companion",
                               _periodic_rows(50, 2.4, 0.2, 1.4))
    report = analyze_t1(primary, mode="open", companion_dir=companion)
    assert report["verdict"] == "ATTRIBUTION-FAILED"
    assert "mechanism probe" in report["caveat"]
    assert report["unattributed_lags"]


def test_open_field_blocked_carries_flat_sweep_caveat(tmp_path):
    """No temporal structure: deposits at seeded-uniform times (white flux).
    If this seed flukes a significant in-window lag, bump the seed and note
    it here — the test needs a WHITE series, the seed is test data.

    Seed bumped from the brief's suggested 5: seed 5 flukes a significant
    in-window lag (verdict FIELD-EARNED, verified by sweeping seeds 0-49),
    which is exactly the failure mode this docstring warns about. Seed 0
    is genuinely white (FIELD-BLOCKED) and was checked against the same
    sweep."""
    import random
    rng = random.Random(0)
    rows = []
    for i, t in enumerate(sorted(rng.uniform(0.5, 80.0) for _ in range(120))):
        rows.append((t - 0.4, "reservation.acquired", f"res{i}",
                     {"round_id": None, "lease_id": f"R{i}:L",
                      "request_id": f"R{i}", "path_id": PATH_A}))
        rows.append((t, "pool.deposited", f"R{i}:L",
                     {"key": KEY_A, "depth": 1, "lease_id": f"R{i}:L",
                      "round_id": None, "source": "replenish"}))
    primary = _write_run_dir(tmp_path, "primary", sorted(rows, key=lambda r: r[0]))
    companion = _write_run_dir(tmp_path, "companion", sorted(rows, key=lambda r: r[0]))
    report = analyze_t1(primary, mode="open", companion_dir=companion)
    assert report["verdict"] == "FIELD-BLOCKED"
    assert "flat" in report["caveat"].lower()


def test_companion_config_differs_only_in_arrival_rate():
    from dataclasses import fields
    from qsim.cli import load_config
    open_cfg = load_config("examples/t1-open.toml")
    companion_cfg = load_config("examples/t1-open-companion.toml")
    assert companion_cfg.arrival_rate_hz == 0.5
    for f in fields(open_cfg):
        if f.name == "arrival_rate_hz":
            continue
        assert getattr(open_cfg, f.name) == getattr(companion_cfg, f.name), f.name
