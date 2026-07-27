#!/usr/bin/env python3
"""Quality-channel flattening test, per
docs/superpowers/specs/2026-07-26-flattening-test-quality-prereg.md.

Computes ONLY the preregistered statistics on runs/hedged-stage1/quality.csv:
per-arm mean, population variance, CV, and per-axis main-effect ranges of
{arm}.q_mean_given_materialized over the quality axes, on all 540 cells
(primary) and the activated 270 (sensitivity). Emits JSON with P1/P2 verdicts.
"""

import csv
import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSV = ROOT / "runs" / "hedged-stage1" / "quality.csv"

ARMS = ["late", "prebound", "single"]
AXES = ["param.rho_q", "param.a_1", "param.delta_clone", "param.a_e"]
EXACT_TOL = 1e-9
EPS = 0.005
EPS_CV = 0.005

# P1's frozen table: axis -> {arm: 'exact-flat' | 'structured' | None}
P1_TABLE = {
    "param.rho_q": {"single": "exact-flat", "prebound": "exact-flat", "late": "structured"},
    "param.a_1": {"single": "exact-flat", "prebound": "exact-flat", "late": "structured"},
    "param.delta_clone": {"single": "exact-flat", "prebound": "structured", "late": "structured"},
    "param.a_e": {},  # unspecified
}


def variance(xs):
    n = len(xs)
    m = sum(xs) / n
    return sum((x - m) ** 2 for x in xs) / n


def load(rows_filter=None):
    rows = []
    with CSV.open() as fh:
        for row in csv.DictReader(fh):
            if rows_filter is None or rows_filter(row):
                rows.append(row)
    return rows


def stats(rows):
    out = {}
    for arm in ARMS:
        vals = [float(r[f"{arm}.q_mean_given_materialized"]) for r in rows]
        mean = sum(vals) / len(vals)
        var = variance(vals)
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
        out[arm] = {"n": len(vals), "mean": mean, "variance": var,
                    "cv": (var ** 0.5) / mean if mean else None,
                    "main_effect_ranges": per_axis}
    return out


def p1_verdict(s):
    cells = {}
    all_hold = True
    for axis, preds in P1_TABLE.items():
        for arm, pred in preds.items():
            rng = s[arm]["main_effect_ranges"][axis]["range"]
            if pred == "exact-flat":
                ok = rng < EXACT_TOL
            else:
                ok = rng > EPS
            cells[f"{arm}/{axis}"] = {"predicted": pred, "range": rng, "holds": ok}
            all_hold = all_hold and ok
    return {"all_hold": all_hold, "cells": cells}


def p2_verdict(s):
    cv = {arm: s[arm]["cv"] for arm in ARMS}
    rescue = (cv["late"] < cv["prebound"] - EPS_CV
              and cv["late"] < cv["single"] - EPS_CV)
    rival = cv["late"] > cv["single"] + EPS_CV
    return {"cv": cv, "P2_rescue_holds": rescue, "P2_rival_holds": rival,
            "tie_zone": not rescue and not rival}


def main():
    full = load()
    activated = load(lambda r: r["activated"] in ("True", "true", "1"))
    result = {"prereg": "docs/superpowers/specs/2026-07-26-flattening-test-quality-prereg.md"}
    for name, rows in (("primary_full_540", full), ("sensitivity_activated", activated)):
        s = stats(rows)
        result[name] = {"stats": s, "P1": p1_verdict(s), "P2": p2_verdict(s)}
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
