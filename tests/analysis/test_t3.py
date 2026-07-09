"""T3 verdicts on hand-built traces with known inversion counts and known
projected deltas (design §11; prereg T3 thresholds)."""
import json

import pytest

from qsim.analysis.t3 import analyze_t3


def _run_dir(tmp_path, rows, rate=0.1):
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
        "run_id": "r", "run_seed": 1, "git_sha": "deadbeef",
        "schema_version": 1, "filtering": {"enabled": False},
        "steady_state": {"status": "CONVERGED", "warmup_cutoff_s": 0.0,
                          "evidence": {"horizon_s": 30.0}},
        "config": {"scheduler": "S1",
                    "epoch": {"decay_rate_per_class": {"messenger": rate,
                                                        "memory": 0.001}}},
    }))
    return run_dir


def _pair(hi_f, hi_h, lo_f, lo_h, consume_at, other_terminal_at,
          other_terminal="lease.expired"):
    """Two co-pending leases; L1 consumed at `consume_at` (the decision
    point), L2 reaches `other_terminal` later."""
    return [
        (hi_h - 0.5, "lease.requested", "L1", {"round_id": "r1"}),
        (hi_h, "lease.heralded", "L1", {"round_id": "r1",
                                         "fidelity_at_herald": hi_f}),
        (lo_h - 0.4, "lease.requested", "L2", {"round_id": "r2"}),
        (lo_h, "lease.heralded", "L2", {"round_id": "r2",
                                         "fidelity_at_herald": lo_f}),
        (consume_at, "lease.consumed", "L1",
         {"round_id": "r1", "fidelity_at_consumption": 0.0}),
        (other_terminal_at, other_terminal, "L2", {"round_id": "r2"}),
    ]


def test_material_inversion_is_decision_earned(tmp_path):
    # rate 0.1: current(L1)=0.9*e^-0.5=0.546 < current(L2)=0.85*e^-0.1=0.769
    # projected(L1)=0.546 (consumed at decision) > projected(L2)=0.85*e^-1.6=0.172
    # -> inversion, delta ~0.374 > 0.01 -> FREQUENT + material.
    rows = _pair(0.9, 0.0, 0.85, 4.0, consume_at=5.0, other_terminal_at=20.0)
    report = analyze_t3(_run_dir(tmp_path, sorted(rows, key=lambda r: r[0])))
    assert report["verdict"].startswith("INVERSIONS-FREQUENT (DECISION-EARNED")
    assert report["inversion_point_rate"] == 1.0
    assert report["median_projected_delta"] > 0.01


def test_aligned_orderings_are_rare(tmp_path):
    # L2 consumed shortly after: both orderings agree -> no inversion.
    rows = _pair(0.9, 0.0, 0.85, 4.0, consume_at=5.0, other_terminal_at=5.2,
                 other_terminal="lease.consumed")
    report = analyze_t3(_run_dir(tmp_path, sorted(rows, key=lambda r: r[0])))
    assert report["verdict"] == "INVERSIONS-RARE"


def test_immaterial_inversion_demotion_stands(tmp_path):
    # rate 1e-3, near-tied fidelities: inversion with delta < 0.01.
    rows = _pair(0.9, 0.0, 0.896, 5.0, consume_at=5.0, other_terminal_at=6.0)
    report = analyze_t3(_run_dir(tmp_path, sorted(rows, key=lambda r: r[0]),
                                  rate=0.001))
    assert report["verdict"] == "INVERSIONS-FREQUENT-BUT-IMMATERIAL (demotion stands)"


def test_degenerate_dominated_is_non_field(tmp_path):
    rows = []
    for i in range(3):  # three singleton decision points, zero nondegenerate
        t = 10.0 * i
        rows += [
            (t, "lease.requested", f"L{i}", {"round_id": f"r{i}"}),
            (t + 0.5, "lease.heralded", f"L{i}", {"round_id": f"r{i}",
                                                   "fidelity_at_herald": 0.9}),
            (t + 1.0, "lease.consumed", f"L{i}",
             {"round_id": f"r{i}", "fidelity_at_consumption": 0.0}),
        ]
    report = analyze_t3(_run_dir(tmp_path, rows))
    assert report["verdict"].startswith("NON-FIELD-AT-OPERATING-POINT")
    assert report["nondegenerate_fraction"] == 0.0


def test_censored_leases_are_excluded_and_counted(tmp_path):
    rows = [
        (0.0, "lease.requested", "L1", {"round_id": "r1"}),
        (0.5, "lease.heralded", "L1", {"round_id": "r1", "fidelity_at_herald": 0.9}),
        (1.0, "lease.requested", "L2", {"round_id": "r2"}),
        (1.5, "lease.heralded", "L2", {"round_id": "r2", "fidelity_at_herald": 0.8}),
        (2.0, "lease.consumed", "L1", {"round_id": "r1", "fidelity_at_consumption": 0.0}),
        # L2 never terminates: censored -> point degenerates to size 1
    ]
    report = analyze_t3(_run_dir(tmp_path, rows))
    assert report["n_censored_leases"] == 1
    assert report["nondegenerate_fraction"] == 0.0


def test_no_decision_points_is_refusal(tmp_path):
    report = analyze_t3(_run_dir(tmp_path, [
        (1.0, "round.arrived", "r1", {"retry_ordinal": 0, "deadline": 2.0})]))
    assert report["verdict"] is None
    assert report["refusals"]
