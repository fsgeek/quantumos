"""Q4 protocol-asymmetry confirmation sweep (Gemini disposition 2026-07-16;
the pre-§4 drafting gate).

Re-runs the S1 anchor (examples/t1-open.toml — the rr/delta=0/calm arm of
runs/sweep-s1) at pool_herald_attempts in {1, 2, 4, 8}: the retain-and-retry
replenishment arm. The question on record: is the maintenance-amplification
figure (76% of fabric actuations are maintenance, 3.22:1) an artifact of the
release-and-reacquire replenishment choice (each generation trigger burns a
full reservation for ONE herald attempt) rather than a property of the
operating point?

N=1 is the regression control and must reproduce the committed anchor's
accounting exactly (same seed, same CRN streams, the knob is dormant):
foreground 145 vs replenish 467 reservations, 334 deposited / 85 expired.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qsim.cli import load_config
from qsim.experiments.run import run
from qsim.observe.views import deadline_compliance

ATTEMPTS = (1, 2, 4, 8)
BASE_CONFIG = REPO_ROOT / "examples" / "t1-open.toml"
OUT_ROOT = REPO_ROOT / "runs" / "sweep-pool-retry"


def _arm_metrics(events_path: Path) -> dict:
    foreground = 0
    replenish = 0
    pool_draws = 0
    pool = Counter()
    abandoned = Counter()
    with events_path.open() as f:
        for line in f:
            e = json.loads(line)
            t = e["event_type"]
            if t == "reservation.acquired":
                if e["payload"].get("round_id") is None:
                    replenish += 1
                else:
                    foreground += 1
            elif t == "draw.sampled" and e["payload"].get("stream") == "pool_herald":
                pool_draws += 1
            elif t.startswith("pool."):
                pool[t] += 1
                if t == "pool.replenish_abandoned":
                    abandoned[e["payload"]["reason"]] += 1
    total = foreground + replenish
    return {
        "reservations": {
            "foreground": foreground,
            "replenish": replenish,
            "maintenance_share": replenish / total if total else None,
            "replenish_to_foreground_ratio": replenish / foreground if foreground else None,
        },
        "pool_herald_draws": pool_draws,
        "pool_events": dict(sorted(pool.items())),
        "replenish_abandoned_by_reason": dict(sorted(abandoned.items())),
        "deadline_compliance": deadline_compliance(events_path),
    }


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    base = load_config(BASE_CONFIG)
    arms = []
    for n in ATTEMPTS:
        config = dataclasses.replace(base, pool_herald_attempts=n)
        run_dir = run(config, OUT_ROOT)
        header = json.loads((run_dir / "header.json").read_text())
        metrics = _arm_metrics(run_dir / "events.jsonl")
        arms.append({
            "pool_herald_attempts": n,
            "run_id": header["run_id"],
            "run_dir": str(run_dir.relative_to(REPO_ROOT)),
            "steady_state_status": (header.get("steady_state") or {}).get("status"),
            **metrics,
        })
        r = arms[-1]["reservations"]
        print(f"N={n}: foreground={r['foreground']} replenish={r['replenish']} "
              f"share={r['maintenance_share']:.3f} draws={arms[-1]['pool_herald_draws']} "
              f"steady={arms[-1]['steady_state_status']}", flush=True)

    manifest = {
        "purpose": "Q4 protocol-asymmetry confirmation sweep (pre-§4 gate)",
        "base_config": str(BASE_CONFIG.relative_to(REPO_ROOT)),
        "knob": "pool_herald_attempts",
        "regression_control_expectation": {
            "arm": 1, "foreground": 145, "replenish": 467,
            "note": "must reproduce the committed sweep-s1 delta=0 anchor",
        },
        "arms": arms,
    }
    (OUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"manifest: {OUT_ROOT / 'manifest.json'}")


if __name__ == "__main__":
    main()
