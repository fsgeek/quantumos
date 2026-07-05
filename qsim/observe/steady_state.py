"""Steady-state / convergence gate for a run's trace (design spec §13).

WHY THIS EXISTS
---------------
The simulator is a CLOSED-LOOP queue: a failed or deferred round is ALWAYS
re-offered (there is no retry cap — see `qsim/workload/generator.py.on_outcome`
and `qsim/core/engine.py._retry_or_drop`). At high load / high decay the offered
work exceeds the service capacity and the in-flight backlog DIVERGES: it grows
toward ~100% of offered by the sim horizon, and horizon-normalized metrics like
goodput drift toward 0 as the horizon grows. Those metrics then measure a
transient snapshot, not a system property. A metric reported off a non-converged
run is a lie of precision. This module lets a caller detect that case and flag
it LOUDLY instead of silently trusting the number.

WHAT IT MEASURES
----------------
The in-flight backlog over sim time, reconstructed from the trace alone:

    in_flight(t) = (#`round.arrived` with sim_time <= t)
                 - (#terminal-round events with sim_time <= t)

A `round.arrived` is an ENTRY into the system (retries get a fresh
`round.arrived` with an incremented `retry_ordinal`, so they count as entries
too). A terminal-round event is an EXIT. Terminal types are exactly those a
round's lifecycle can end (or bounce back into the retry loop) on:

    round.completed_in_deadline, round.completed_late,
    round.failed, round.dropped, round.deferred

`round.deferred` is treated as terminal because a deferred round LEAVES the
in-flight set and re-enters later as a fresh retry `round.arrived` — so counting
the deferral as an exit and its retry as a new entry keeps the accounting
balanced. (Consumes only these existing event types; invents no producer change.)

CONVERGENCE HEURISTIC (conservative, M0)
----------------------------------------
Manual steady-state detection per spec §13. We split sim time [0, T] into
quartiles and compare the TIME-WEIGHTED-MEAN in-flight backlog of the final
quartile [0.75T, T] against the third quartile [0.5T, 0.75T]. The backlog is
normalized by the offered count (retry_ordinal == 0 arrivals) so the statistic
is a dimensionless RELATIVE backlog and the threshold is scale-free:

    relative_slope = mean_rel_backlog(Q4) - mean_rel_backlog(Q3)

If the backlog is STILL CLIMBING at end-of-run beyond a small tolerance the run
is DIVERGENT; if it has PLATEAUED (slope within tolerance) it is CONVERGED.

    DIVERGENT  iff  relative_slope > RELATIVE_SLOPE_TOLERANCE
    CONVERGED  otherwise

RELATIVE_SLOPE_TOLERANCE = 0.02 (i.e. the mean in-flight backlog grew by more
than 2% of offered work between the third and final quartile). This is chosen
conservatively from measured runs: a benign steady-state run
(decay_rate=0.1) holds in_flight/offered near 0 with quartile-to-quartile
noise well under 0.01, while a collapse run (decay_rate=1.0) climbs by ~0.07
of offered per quartile. 0.02 sits an order of magnitude above the benign
noise floor and comfortably below the divergent signal, so it separates the
two without flagging benign jitter. The test is deliberately one-sided
(only *climbing* is divergent): a backlog that has plateaued at a high-but-
bounded level is a legitimate steady state, not a divergence.

The warmup cutoff (spec §13: recorded in the header) is the transient boundary
before which steady-state statistics should be discarded. For M0 we set it to
the midpoint 0.5*T — the classifier measures steady-state behavior in the
second half of the run — and record it so downstream metric consumers can trim
the transient consistently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from qsim.observe.work_accounting import iter_events

# In-flight EXIT events: a round's lifecycle terminates (or bounces back into
# the retry loop) on exactly one of these. Kept local to this module — payload
# shapes are not relied upon, only the event_type is counted.
_TERMINAL_ROUND_EVENTS = frozenset(
    {
        "round.completed_in_deadline",
        "round.completed_late",
        "round.failed",
        "round.dropped",
        "round.deferred",
    }
)

# See module docstring for the derivation of this threshold.
RELATIVE_SLOPE_TOLERANCE = 0.02


@dataclass
class SteadyStateVerdict:
    status: str  # "CONVERGED" | "DIVERGENT"
    warmup_cutoff_s: float
    evidence: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "warmup_cutoff_s": self.warmup_cutoff_s,
            "evidence": self.evidence,
        }


def _window_mean_backlog(deltas: list[tuple[float, int]], a: float, b: float) -> float:
    """Time-weighted mean of the in-flight step function over [a, b].

    `deltas` is a time-sorted list of (sim_time, +1|-1) transitions. The
    in-flight backlog is the running cumulative sum; we integrate that step
    function exactly across [a, b] and divide by the window width.
    """
    if b <= a:
        return 0.0
    running = 0
    integral = 0.0
    prev_t = a
    # Advance `running` up to the window start, then integrate within [a, b].
    for t, d in deltas:
        if t <= a:
            running += d
            continue
        seg_end = min(t, b)
        if seg_end > prev_t:
            integral += running * (seg_end - prev_t)
            prev_t = seg_end
        if t >= b:
            # remaining transitions are beyond the window
            running += d
            break
        running += d
    if prev_t < b:
        integral += running * (b - prev_t)
    return integral / (b - a)


def compute_steady_state(events_path: Path) -> SteadyStateVerdict:
    """Scan a run's events.jsonl and classify it CONVERGED or DIVERGENT.

    Verify against a REAL run's trace (see tests/observe/test_steady_state.py);
    this reader consumes only pre-existing event types.
    """
    deltas: list[tuple[float, int]] = []
    offered = 0
    horizon = 0.0
    for record in iter_events(events_path):
        t = float(record["sim_time"])
        if t > horizon:
            horizon = t
        et = record["event_type"]
        if et == "round.arrived":
            deltas.append((t, +1))
            if record["payload"].get("retry_ordinal", 0) == 0:
                offered += 1
        elif et in _TERMINAL_ROUND_EVENTS:
            deltas.append((t, -1))
    deltas.sort(key=lambda x: x[0])

    warmup_cutoff_s = 0.5 * horizon

    # Degenerate traces (no work / zero horizon) are trivially converged: there
    # is no backlog to diverge. Report explicitly rather than dividing by zero.
    if horizon <= 0.0 or offered == 0 or not deltas:
        return SteadyStateVerdict(
            status="CONVERGED",
            warmup_cutoff_s=warmup_cutoff_s,
            evidence={
                "reason": "empty_or_trivial_trace",
                "horizon_s": horizon,
                "offered": offered,
                "relative_slope_tolerance": RELATIVE_SLOPE_TOLERANCE,
            },
        )

    q3_lo, q3_hi = 0.5 * horizon, 0.75 * horizon
    q4_lo, q4_hi = 0.75 * horizon, horizon
    q3_backlog = _window_mean_backlog(deltas, q3_lo, q3_hi)
    q4_backlog = _window_mean_backlog(deltas, q4_lo, q4_hi)

    q3_rel = q3_backlog / offered
    q4_rel = q4_backlog / offered
    relative_slope = q4_rel - q3_rel

    # Final in-flight backlog at the horizon (raw, for context).
    final_in_flight = sum(d for _, d in deltas)

    status = "DIVERGENT" if relative_slope > RELATIVE_SLOPE_TOLERANCE else "CONVERGED"

    return SteadyStateVerdict(
        status=status,
        warmup_cutoff_s=warmup_cutoff_s,
        evidence={
            "horizon_s": horizon,
            "offered": offered,
            "q3_window_s": [q3_lo, q3_hi],
            "q4_window_s": [q4_lo, q4_hi],
            "q3_mean_backlog": q3_backlog,
            "q4_mean_backlog": q4_backlog,
            "q3_mean_relative_backlog": q3_rel,
            "q4_mean_relative_backlog": q4_rel,
            "relative_slope": relative_slope,
            "relative_slope_tolerance": RELATIVE_SLOPE_TOLERANCE,
            "final_in_flight": final_in_flight,
            "final_relative_backlog": final_in_flight / offered,
        },
    )


class SteadyStateError(AssertionError):
    """Raised by `assert_or_flag_steady_state` on a DIVERGENT run."""


def assert_or_flag_steady_state(run_dir: Path, *, raise_on_divergent: bool = True):
    """LOUD flag: surface an explicit signal when a run is DIVERGENT.

    Capture-norm: never silently report metrics off a non-converged run. A
    caller invokes this before trusting any horizon-normalized metric; on a
    DIVERGENT run it raises `SteadyStateError` (or, with
    `raise_on_divergent=False`, prints a prominent warning and returns the
    verdict) so the divergence cannot be missed.

    Returns the `SteadyStateVerdict` (also for CONVERGED runs).
    """
    run_dir = Path(run_dir)
    verdict = compute_steady_state(run_dir / "events.jsonl")
    if verdict.status == "DIVERGENT":
        ev = verdict.evidence
        banner = (
            "\n"
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
            "!!  DIVERGENT RUN — in-flight backlog is NOT at steady state  !!\n"
            "!!  Horizon-normalized metrics (goodput, error proxy, ...) are !!\n"
            "!!  a TRANSIENT SNAPSHOT and MUST NOT be trusted as a system    !!\n"
            "!!  property. Reduce load/decay or extend the horizon.          !!\n"
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
            f"  run_dir: {run_dir}\n"
            f"  relative_slope: {ev.get('relative_slope')!r} "
            f"(tolerance {ev.get('relative_slope_tolerance')!r})\n"
            f"  final_relative_backlog: {ev.get('final_relative_backlog')!r} "
            f"of offered={ev.get('offered')!r}\n"
        )
        if raise_on_divergent:
            raise SteadyStateError(banner)
        import sys

        print(banner, file=sys.stderr)
    return verdict
