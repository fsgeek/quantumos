"""T3 lease-freshness rank inversion (design §6; prereg T3, thresholds
verbatim). Disclosed conventions (2026-07-09 plan findings #3, #8):

* Projection time for each co-pending lease is its OWN terminal event time
  from the trace; the fidelity at that time is ANALYTIC —
  f_herald * exp(-rate * (t_terminal - heralded_at)) — never read from an
  observed outcome event ("analytic from trace, projected never observed").
* Leases with no terminal in the trace (horizon-censored) are excluded from
  the ordering and counted in the report.
* "Degenerate batches dominate" = nondegenerate fraction < 0.5.
"""
from __future__ import annotations

import math
from itertools import combinations
from pathlib import Path

from qsim.analysis import numerics
from qsim.analysis.artifacts import ancestry, write_report
from qsim.analysis.t1 import _load_header
from qsim.observe.decision_points import t3_decision_points

INVERSION_RATE_THRESHOLD = 0.10   # prereg: "more than 10%"
MATERIALITY_THRESHOLD = 0.01      # prereg: median projected delta, absolute
DEGENERATE_DOMINANCE = 0.5        # plan finding #8, disclosed convention


def analyze_t3(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    header = _load_header(run_dir)
    rate = float(header["config"]["epoch"]["decay_rate_per_class"]["messenger"])
    report: dict = {
        "test": "t3", "verdict": None, "refusals": [],
        "operating_point": header.get("config"),
        "git_sha": header.get("git_sha"),
        "ancestry": ancestry(header.get("git_sha", "")),
        "decay_rate": rate,
        "thresholds": {
            "inversion_point_rate": INVERSION_RATE_THRESHOLD,
            "median_projected_delta": MATERIALITY_THRESHOLD,
            "degenerate_dominance": DEGENERATE_DOMINANCE,
        },
        "conventions": {
            "projection_time": "each lease's own terminal event time from the "
                                "trace; fidelity analytic, never observed",
            "censoring": "leases without a terminal are excluded and counted"
                         "; censored leases are counted per decision-point "
                         "occurrence, not per lease",
        },
    }

    points = t3_decision_points(run_dir / "events.jsonl")
    report["n_decision_points"] = len(points)
    if not points:
        report["refusals"].append("no decision points: insufficient data")
        write_report(run_dir, "t3_report", report)
        return report

    n_censored = 0
    n_nondegenerate = 0
    n_inverted_points = 0
    inverted_deltas: list[float] = []
    for dp in points:
        eligible = [l for l in dp.co_pending if l.terminal_time is not None]
        n_censored += len(dp.co_pending) - len(eligible)
        if len(eligible) < 2:
            continue
        n_nondegenerate += 1
        scored = [
            (l.fidelity_at_herald * math.exp(-rate * (dp.sim_time - l.heralded_at)),
             l.fidelity_at_herald * math.exp(-rate * (l.terminal_time - l.heralded_at)))
            for l in eligible
        ]
        point_inverted = False
        for (cur_i, proj_i), (cur_j, proj_j) in combinations(scored, 2):
            if (cur_i - cur_j) * (proj_i - proj_j) < 0:
                point_inverted = True
                inverted_deltas.append(abs(proj_i - proj_j))
        if point_inverted:
            n_inverted_points += 1

    nondeg_fraction = n_nondegenerate / len(points)
    report["n_censored_leases"] = n_censored
    report["n_nondegenerate"] = n_nondegenerate
    report["nondegenerate_fraction"] = nondeg_fraction

    if nondeg_fraction < DEGENERATE_DOMINANCE:
        report["verdict"] = ("NON-FIELD-AT-OPERATING-POINT (degenerate-dominated); "
                              "retest under higher concurrency")
        write_report(run_dir, "t3_report", report)
        return report

    rate_points = n_inverted_points / n_nondegenerate
    median_delta = numerics.percentile(inverted_deltas, 50) if inverted_deltas else 0.0
    report["inversion_point_rate"] = rate_points
    report["median_projected_delta"] = median_delta

    if rate_points > INVERSION_RATE_THRESHOLD and median_delta > MATERIALITY_THRESHOLD:
        report["verdict"] = ("INVERSIONS-FREQUENT (DECISION-EARNED, "
                              "REPRESENTATION-CHEAP): the fix is a projection from "
                              "existing scalars, NOT a field; frequent inversions do "
                              "NOT re-promote lease freshness to field")
    elif rate_points > INVERSION_RATE_THRESHOLD:
        report["verdict"] = "INVERSIONS-FREQUENT-BUT-IMMATERIAL (demotion stands)"
    else:
        report["verdict"] = "INVERSIONS-RARE"
    write_report(run_dir, "t3_report", report)
    return report
