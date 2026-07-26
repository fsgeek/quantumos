#!/usr/bin/env python3
"""Flattening test, per docs/superpowers/specs/2026-07-26-flattening-test-prereg.md.

Computes ONLY the preregistered statistics on runs/hedged-stage1/survival.csv:
per-arm total variance of p_accepted and per-axis main-effect ranges, on the
full 1,620-cell grid (primary) and the activated 1,296 (sensitivity), for the
late/prebound/single arms. Emits JSON and the frozen verdict logic.
"""

import csv
import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSV = ROOT / "runs" / "hedged-stage1" / "survival.csv"

ARMS = ["late", "prebound", "single"]
AXES = ["param.p_c", "param.p_l", "param.q_k", "param.g", "param.a_e",
        "param.rho_k", "rho_c_rho_l"]
EPS = 0.01


def variance(xs):
    n = len(xs)
    m = sum(xs) / n
    return sum((x - m) ** 2 for x in xs) / n


def load(rows_filter=None):
    rows = []
    with CSV.open() as fh:
        for row in csv.DictReader(fh):
            row["rho_c_rho_l"] = f'{row["param.rho_c"]},{row["param.rho_l"]}'
            if rows_filter is None or rows_filter(row):
                rows.append(row)
    return rows


def stats(rows):
    out = {}
    for arm in ARMS:
        vals = [float(r[f"{arm}.p_accepted"]) for r in rows]
        per_axis = {}
        for axis in AXES:
            groups = defaultdict(list)
            for r, v in zip(rows, vals):
                groups[r[axis]].append(v)
            marginals = {lvl: sum(g) / len(g) for lvl, g in groups.items()}
            per_axis[axis] = {
                "range": max(marginals.values()) - min(marginals.values()),
                "marginals": {k: round(v, 6) for k, v in sorted(marginals.items())},
            }
        out[arm] = {"n": len(vals), "variance": variance(vals),
                    "main_effect_ranges": per_axis}
    return out


def verdict(s):
    late, pre = s["late"], s["prebound"]
    var_drop = late["variance"] < pre["variance"] - EPS ** 2
    exceed = {ax: late["main_effect_ranges"][ax]["range"]
                  - pre["main_effect_ranges"][ax]["range"]
              for ax in AXES}
    redistributed_axes = [ax for ax, d in exceed.items() if d > EPS]
    uniformly_flat = all(d <= EPS for d in exceed.values())
    if redistributed_axes:
        v = "H-REDISTRIBUTE"
    elif var_drop and uniformly_flat:
        v = "H-FLATTEN"
    else:
        v = "NEITHER"
    return {"verdict": v, "var_late": late["variance"],
            "var_prebound": pre["variance"], "var_drop": var_drop,
            "late_minus_prebound_range_by_axis": {k: round(x, 6) for k, x in exceed.items()},
            "redistributed_axes": redistributed_axes}


def main():
    full = load()
    activated = load(lambda r: r["activated"] in ("True", "true", "1"))
    result = {
        "prereg": "docs/superpowers/specs/2026-07-26-flattening-test-prereg.md",
        "primary_full_grid": {"stats": stats(full)},
        "sensitivity_activated": {"stats": stats(activated)},
    }
    result["primary_full_grid"]["verdict"] = verdict(result["primary_full_grid"]["stats"])
    result["sensitivity_activated"]["verdict"] = verdict(result["sensitivity_activated"]["stats"])
    # Secondary contrast, descriptive only per prereg.
    s = result["primary_full_grid"]["stats"]
    result["secondary_late_vs_single_descriptive"] = {
        "var_late": s["late"]["variance"], "var_single": s["single"]["variance"],
        "range_diff_by_axis": {
            ax: round(s["late"]["main_effect_ranges"][ax]["range"]
                      - s["single"]["main_effect_ranges"][ax]["range"], 6)
            for ax in AXES},
    }
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
