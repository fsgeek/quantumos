"""§16.2 decoupled-limit acceptance checks: heralding attempts vs Bernoulli,
and workload arrivals vs Poisson.

Named as DECOUPLED-limit checks, NOT validation of the coupled regime — every
other subsystem is deliberately neutralized (decay off, memory cost off, huge
decoder rate, huge deadline slack) so only the targeted stochastic process is
exercised.

NOTE on topology (mirrors tests/experiments/test_mm1_decoupled_limit.py's
documented contract gap): `core/engine.py`'s `_synthesize_ports` deterministically
synthesizes `count = max(2, switch_capacity_c * 2)` ports named "M0", "M1", ...
regardless of what module ids a caller's `CalibrationEpoch` happens to key its
per-path tables with — RunConfig carries no port/module topology field. With
switch_capacity_c=1, that synthesizes exactly {M0, M1}, and `_endpoints_for`'s
round-robin counter always pairs them into the SAME canonical PathId (single
path, single reservation slot). The epoch's heralding table MUST be keyed by
that synthesized path: an unrecognized path guards to
success_probability/heralded_fidelity = 0.0 (`_UncalibratedPathGuardedHeralding`
in experiments/run.py), which would make every herald attempt on that path
fail forever. A larger switch_capacity_c (e.g. 4, as one might reach for to
"minimize switch contention") would round-robin attempts across up to 8
distinct synthesized paths, only one of which the epoch calibrates — so it is
NOT used here; switch_capacity_c=1 with both synthesized ports calibrated is
what actually isolates heralding as the single stochastic mechanism under
test, with negligible switch-contention confound given how much faster
heralding+decoding resolves here than the arrival process.
"""
import json
import statistics
from pathlib import Path

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.experiments.run import run

BERNOULLI_TOLERANCE_SIGMAS = 4.0  # generous normal-approximation CI multiplier
POISSON_RELATIVE_TOLERANCE = 0.15


def _load_events(events_path: Path) -> list[dict]:
    return [json.loads(line) for line in events_path.read_text().strip().splitlines()]


def _bernoulli_success_stats(events: list[dict]) -> tuple[int, int]:
    n_attempts = sum(
        1
        for e in events
        if e["event_type"] == "draw.sampled" and e["payload"]["stream"] == "herald"
    )
    n_successes = sum(1 for e in events if e["event_type"] == "lease.heralded")
    return n_attempts, n_successes


def _arrival_interarrival_times(events: list[dict]) -> list[float]:
    arrival_times = sorted(
        e["sim_time"] for e in events if e["event_type"] == "round.arrived"
    )
    return [t1 - t0 for t0, t1 in zip(arrival_times, arrival_times[1:])]


def _decoupled_config(
    run_seed: int, arrival_rate_hz: float, herald_p: float, max_sim_time_s: float
) -> RunConfig:
    # switch_capacity_c=1 synthesizes exactly the two ports below (see module
    # docstring): a single, always-calibrated path.
    a = PortId(module_id="M0", port_index=0)
    b = PortId(module_id="M1", port_index=0)
    path = make_path_id(a, b)
    epoch = CalibrationEpoch(
        epoch_id="herald-decoupled-limit",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.0, CoherenceClass.MEMORY: 0.0},
        memory_access_channel_s=0.0,
        memory_access_wear_rate=0.0,
        heralding_p_per_path={path: herald_p},
        heralded_fidelity_per_path={path: 1.0},
        round_success_logistic_midpoint=-10.0,
        round_success_logistic_slope=1.0,
        round_success_slack_penalty_per_s=0.0,
        decoder_service_rate=1000.0,  # decoder never bottlenecks: isolates heralding
    )
    return RunConfig(
        run_seed=run_seed,
        scheduler="S0",  # no admission control (§8)
        epoch=epoch,
        arrival_rate_hz=arrival_rate_hz,
        leases_per_round=1,
        deadline_slack_s=10_000.0,
        switch_capacity_c=1,  # single synthesized path: no switch-contention confound
        reconfig_delay_s=0.0,
        max_sim_time_s=max_sim_time_s,
        decay_control_enabled=False,
        memory_cost_control_enabled=False,
    )


def test_heralding_attempts_match_bernoulli_success_rate_in_decoupled_limit(tmp_path):
    """§16.2 decoupled-limit check — NOT coupled-regime validation: per-attempt
    heralding success is a Bernoulli(p) trial by construction (§10: the engine
    thresholds a keyed uniform against the model's probability). The measured
    success rate over many attempts must match the configured p regardless of
    switch/decoder timing, since success-given-an-attempt does not depend on
    when attempts happen to occur."""
    p = 0.3
    config = _decoupled_config(
        run_seed=555, arrival_rate_hz=0.5, herald_p=p, max_sim_time_s=20_000.0
    )
    run_dir = run(config, tmp_path)
    events = _load_events(run_dir / "events.jsonl")

    n_attempts, n_successes = _bernoulli_success_stats(events)
    assert n_attempts > 1000, "need enough herald attempts for a stable estimate"

    phat = n_successes / n_attempts
    stderr = (p * (1 - p) / n_attempts) ** 0.5
    assert abs(phat - p) < BERNOULLI_TOLERANCE_SIGMAS * stderr, (
        f"empirical heralding success rate {phat:.4f} over {n_attempts} attempts "
        f"deviates from configured p={p} by more than "
        f"{BERNOULLI_TOLERANCE_SIGMAS} standard errors ({stderr:.4f})"
    )


def test_workload_arrivals_match_poisson_process_theory_in_decoupled_limit(tmp_path):
    """§16.2 decoupled-limit check: the closed-loop workload's arrival process
    is, per §9, a Poisson process (exponential interarrival times). Its sample
    mean must match 1/arrival_rate_hz, and its coefficient of variation must be
    close to 1 — the defining signature of the exponential interarrival
    distribution."""
    arrival_rate_hz = 2.0
    config = _decoupled_config(
        run_seed=555, arrival_rate_hz=arrival_rate_hz, herald_p=0.3, max_sim_time_s=5_000.0
    )
    run_dir = run(config, tmp_path)
    events = _load_events(run_dir / "events.jsonl")

    interarrivals = _arrival_interarrival_times(events)
    assert len(interarrivals) > 1000, "need enough arrivals for a stable estimate"

    empirical_mean = statistics.mean(interarrivals)
    analytic_mean = 1.0 / arrival_rate_hz
    relative_error = abs(empirical_mean - analytic_mean) / analytic_mean
    assert relative_error < POISSON_RELATIVE_TOLERANCE, (
        f"empirical mean interarrival time {empirical_mean:.4f}s deviates from "
        f"1/lambda={analytic_mean:.4f}s by {relative_error:.2%}"
    )

    coefficient_of_variation = statistics.stdev(interarrivals) / empirical_mean
    assert abs(coefficient_of_variation - 1.0) < POISSON_RELATIVE_TOLERANCE, (
        f"interarrival coefficient of variation {coefficient_of_variation:.4f} "
        f"deviates from the exponential distribution's CV=1 by more than "
        f"{POISSON_RELATIVE_TOLERANCE:.2%} - arrivals may not be a Poisson process"
    )
