"""Calibration bridge for the numpy numerics swap (decision doc ab5040e,
decision 2, point 4).

Re-runs the T1 control analysis with the current (numpy) numerics backend
on the SAME run directory that produced the pure-python control PASS, then
measures the instrument change: verdict, per-pool ACF deviation, surrogate
band deviation, significant-lag sets. The pre-swap report is preserved
alongside, and the comparison is written as its own artifact. The
instrument change between control and open runs is thereby MEASURED, not
assumed.

Usage: uv run python scripts/calibration_bridge_t1.py <run_dir>
Exit 0 iff every reproduction assertion holds.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy

from qsim.analysis import numerics
from qsim.analysis.artifacts import sha256_of, write_report
from qsim.analysis.t1 import analyze_t1

PRESWAP_NAME = "t1_report_preswap_pure_python.json"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True,
                          text=True).stdout.strip()


def main(run_dir: Path) -> int:
    analysis = run_dir / "analysis"
    report_path = analysis / "t1_report.json"
    preswap_path = analysis / PRESWAP_NAME
    if not preswap_path.exists():
        shutil.copy2(report_path, preswap_path)
    pre = json.loads(preswap_path.read_text())

    t0 = time.monotonic()
    post = analyze_t1(run_dir, mode="control",
                      surrogate_seed=pre["surrogate_seed"],
                      n_shuffles=pre["n_shuffles"])
    wall_s = time.monotonic() - t0

    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    check(post["verdict"] == pre["verdict"] == "PASS",
          f"verdict: pre={pre['verdict']} post={post['verdict']}")
    check(post["predicted_lags_reused"] is True,
          "predicted lags were re-derived, not reused (write-once breach)")
    check(post["predicted_lags_sha256"] == pre["predicted_lags_sha256"],
          "predicted-lags artifact hash changed")
    check(post["refusals"] == pre["refusals"] == [],
          f"refusals: pre={pre['refusals']} post={post['refusals']}")
    check(set(post["pools"]) == set(pre["pools"]),
          f"pool key sets differ: {sorted(pre['pools'])} vs {sorted(post['pools'])}")

    max_acf_dev = 0.0
    max_band_dev = 0.0
    per_pool: dict[str, dict] = {}
    for key in sorted(pre["pools"]):
        p, q = pre["pools"][key], post["pools"][key]
        acf_dev = max(abs(a - b) for a, b in zip(p["acf"], q["acf"]))
        band_dev = max(max(abs(a[0] - b[0]), abs(a[1] - b[1]))
                       for a, b in zip(p["surrogate_band"], q["surrogate_band"]))
        max_acf_dev = max(max_acf_dev, acf_dev)
        max_band_dev = max(max_band_dev, band_dev)
        check(len(p["acf"]) == len(q["acf"]),
              f"pool {key}: max_lag changed {len(p['acf'])} -> {len(q['acf'])}")
        check(p["significant_lags"] == q["significant_lags"],
              f"pool {key}: significant_lags set changed")
        check(p["significant_in_window"] == q["significant_in_window"],
              f"pool {key}: significant_in_window changed")
        check(p["negative_at_replenishment_lag"]
              == q["negative_at_replenishment_lag"] is True,
              f"pool {key}: negative_at_replenishment_lag changed")
        per_pool[key] = {
            "max_abs_acf_deviation": acf_dev,
            "max_abs_surrogate_band_deviation": band_dev,
            "lag1_acf_pre": p["acf"][0], "lag1_acf_post": q["acf"][0],
        }

    # 1e-9 is generous headroom over the 1e-12 cross-validation tolerance;
    # anything larger means the backends disagree beyond float-summation
    # reordering and the swap must not proceed to the open regime.
    check(max_acf_dev < 1e-9, f"max ACF deviation {max_acf_dev} >= 1e-9")
    check(max_band_dev < 1e-9, f"max band deviation {max_band_dev} >= 1e-9")

    bridge = {
        "purpose": ("calibration bridge for the numpy numerics swap: the "
                    "instrument change between control and open runs is "
                    "measured, not assumed (decision doc ab5040e)"),
        "run_id": pre.get("predicted_lags", {}).get("run_id"),
        "backend_post": numerics.BACKEND,
        "numpy_version": numpy.__version__,
        "git_sha_pre_swap": pre.get("git_sha"),
        "git_sha_at_bridge": _git("rev-parse", "HEAD"),
        "working_tree_dirty_at_bridge": bool(_git("status", "--porcelain",
                                                  "--untracked-files=no")),
        "preswap_report": {"path": PRESWAP_NAME,
                           "sha256": sha256_of(preswap_path)},
        "postswap_report_sha256": sha256_of(report_path),
        "verdict_pre": pre["verdict"], "verdict_post": post["verdict"],
        "predicted_lags_reused": post["predicted_lags_reused"],
        "per_pool": per_pool,
        "max_abs_acf_deviation": max_acf_dev,
        "max_abs_surrogate_band_deviation": max_band_dev,
        "analysis_wall_seconds_post_swap": wall_s,
        "reproduction": "PASS" if not failures else "FAIL",
        "failures": failures,
    }
    write_report(run_dir, "t1_calibration_bridge", bridge)

    print(f"bridge: {bridge['reproduction']}  "
          f"max ACF dev {max_acf_dev:.3e}  max band dev {max_band_dev:.3e}  "
          f"wall {wall_s:.1f}s (pure-python control analysis was ~3 min)")
    for f in failures:
        print(f"  FAIL: {f}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
