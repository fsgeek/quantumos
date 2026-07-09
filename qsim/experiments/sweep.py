"""S1 sweep runner — minimal and battery-specific (design §8; grid-sweep
proper stays M1 work). Four pinned heralding-spread arms over the T1-open
physics; delta=0 is the homogeneity anchor (any effect there is a bug, not
a curve). Non-monotonicity is reported, not failed (prereg: it triggers a
mechanism audit under the attribution rule).

Plan finding #2: the prereg's delta=0.4 arm is infeasible at p_bar=0.7
(heralding_p 1.1 > 1, by the prereg's own delta=0.2 example fixing delta as
half-spread). The arm is recorded in the manifest as an in-artifact refusal
with a recommended amendment; feasible arms still run.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

from qsim.experiments.config import RunConfig
from qsim.experiments.run import run
from qsim.observe.run_dir import _json_safe
from qsim.observe.views import (
    deadline_compliance,
    fidelity_at_outcome,
    resource_utilization,
)

S1_DELTAS = (0.0, 0.1, 0.2, 0.4)
HOMOGENEITY_UTILIZATION_TOLERANCE = 0.1  # disclosed convention (delta=0 anchor)


class InfeasibleArm(ValueError):
    """A spread arm whose heralding_p leaves [0, 1]."""


def heralding_spread(p_bar: float, delta: float) -> tuple[float, ...]:
    """Four evenly spaced heralding_p values on [p_bar-delta, p_bar+delta]
    (prereg example: delta=0.2 -> {0.5, 0.633, 0.767, 0.9})."""
    if delta == 0.0:
        values = (p_bar,) * 4
    else:
        values = tuple(p_bar - delta + i * (2 * delta / 3) for i in range(4))
    for v in values:
        if not 0.0 <= v <= 1.0:
            raise InfeasibleArm(
                f"delta={delta} at p_bar={p_bar} yields heralding_p={v:.3f} "
                f"outside [0, 1]")
    return values


def build_arm_config(base: RunConfig, delta: float) -> RunConfig:
    ps = set(base.epoch.heralding_p_per_path.values())
    if len(ps) != 1:
        raise ValueError("sweep base config must have homogeneous heralding_p")
    (p_bar,) = ps
    spread = heralding_spread(p_bar, delta)
    paths = sorted(base.epoch.heralding_p_per_path, key=str)
    epoch = dataclasses.replace(
        base.epoch,
        heralding_p_per_path={path: spread[i] for i, path in enumerate(paths)},
    )
    return dataclasses.replace(base, epoch=epoch)


def config_sha256(config: RunConfig) -> str:
    payload = json.dumps(_json_safe(config), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def run_sweep(base_config_path: Path, out_root: Path,
              deltas: tuple[float, ...] = S1_DELTAS,
              max_sim_time_s: float | None = None) -> dict:
    from qsim.cli import load_config  # local import: cli imports analysis

    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    base = load_config(base_config_path)
    if max_sim_time_s is not None:
        # EXPLICIT override only — never a silent test-convenience default
        # (the swept-mechanism-silencing lesson).
        base = dataclasses.replace(base, max_sim_time_s=max_sim_time_s)

    arms = []
    rows = []
    for delta in deltas:
        try:
            config = build_arm_config(base, delta)
        except InfeasibleArm as exc:
            (p_bar,) = set(base.epoch.heralding_p_per_path.values())
            max_delta = min(p_bar, 1.0 - p_bar)
            arms.append({
                "delta": delta, "status": "infeasible", "reason": str(exc),
                "recommend": (
                    f"prereg amendment: delta={delta} is infeasible at "
                    f"p_bar={p_bar:.10g} ({exc}); widest feasible half-spread "
                    f"is delta={max_delta:.10g}"),
            })
            continue
        run_dir = run(config, out_root)
        events = run_dir / "events.jsonl"
        header = json.loads((run_dir / "header.json").read_text())
        arms.append({
            "delta": delta, "status": "ran",
            "run_id": header["run_id"], "run_dir": str(run_dir),
            "config_sha256": config_sha256(config),
            "steady_state": header.get("steady_state"),
        })
        utilization = resource_utilization(events)
        row = {
            "delta": delta,
            "deadline_compliance": deadline_compliance(events),
            "fidelity_at_outcome": {
                f"{outcome}|{cause}": {"n": len(vals),
                                        "mean": sum(vals) / len(vals)}
                for (outcome, cause), vals in sorted(
                    fidelity_at_outcome(events).items())
            },
            "resource_utilization": utilization,
        }
        if delta == 0.0 and utilization:
            spread_u = max(utilization.values()) - min(utilization.values())
            if spread_u > HOMOGENEITY_UTILIZATION_TOLERANCE:
                row["homogeneity_warning"] = (
                    f"per-path utilization spread {spread_u:.3f} > "
                    f"{HOMOGENEITY_UTILIZATION_TOLERANCE} at delta=0: "
                    "any effect at the anchor is a bug, not a curve")
        rows.append(row)

    # Dose-response is a function of delta, not of request order: sort rows
    # so the monotonicity reading is order-independent.
    rows.sort(key=lambda r: r["delta"])

    values = [r["deadline_compliance"]["completed_in_deadline"] for r in rows]
    dose = {
        "rows": rows,
        "monotonicity": {
            "metric": "completed_in_deadline",
            "values": values,
            "monotone_nonincreasing": all(a >= b for a, b in zip(values, values[1:])),
            "note": "non-monotonicity triggers a mechanism audit under the "
                    "attribution rule, not automatic failure (prereg S1)",
        },
    }
    manifest = {"base_config": str(base_config_path), "arms": arms}
    (out_root / "sweep_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True))
    (out_root / "dose_response.json").write_text(
        json.dumps(dose, indent=2, sort_keys=True))
    return manifest
