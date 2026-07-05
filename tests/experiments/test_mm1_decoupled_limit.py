"""§16.2 decoupled-limit acceptance check: with a single path, one qubit,
decay disabled, memory cost disabled, and certain heralding, the decoder
subsystem alone degenerates to a plain M/M/1 queue. This test drives a full
`run()` in that regime and checks the simulated backlog/sojourn statistics
against the M/M/1 closed-form limit within tolerance.

Named as a DECOUPLED-limit check, NOT a validation of the coupled regime
(§16.2) — every other subsystem is deliberately neutralized so only the
decoder queue's stochastic behavior is exercised.
"""
import json
from pathlib import Path

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.experiments.run import run
from qsim.observe.views import decoder_backlog_series

TOLERANCE = 0.15  # relative-error tolerance for stochastic M/M/1 comparisons


def _decoder_sojourn_times(events: list[dict]) -> list[float]:
    enqueued_at: dict[str, float] = {}
    sojourns: list[float] = []
    for event in events:
        if event["event_type"] == "decoder.enqueued":
            enqueued_at[event["entity_id"]] = event["sim_time"]
        elif event["event_type"] == "decoder.completed":
            start = enqueued_at.get(event["entity_id"])
            if start is not None:
                sojourns.append(event["sim_time"] - start)
    return sojourns


def _time_average_backlog(series: list[tuple[float, int]], warmup_s: float) -> float:
    windowed = [(t, backlog) for t, backlog in series if t >= warmup_s]
    if len(windowed) < 2:
        return 0.0
    area = 0.0
    for (t0, b0), (t1, _b1) in zip(windowed, windowed[1:]):
        area += b0 * (t1 - t0)
    duration = windowed[-1][0] - windowed[0][0]
    return area / duration if duration > 0 else 0.0


def _load_events(events_path: Path) -> list[dict]:
    return [json.loads(line) for line in events_path.read_text().strip().splitlines()]


def _mm1_config(run_seed: int, lam: float, mu: float, max_sim_time_s: float) -> RunConfig:
    # NOTE: core/engine.py's `_synthesize_ports` (a documented "contract gap" —
    # RunConfig carries no port/module topology field) deterministically
    # synthesizes `count = max(2, switch_capacity_c * 2)` ports named
    # "M0", "M1", ... regardless of what module ids a caller's CalibrationEpoch
    # happens to key its per-path tables with. With switch_capacity_c=1 below,
    # that is exactly {M0, M1}, and `_endpoints_for` always pairs them into the
    # SAME canonical PathId (make_path_id sorts endpoints, so acquisition
    # order doesn't matter) — a single fixed path, matching this test's
    # single-path M/M/1 premise. The epoch's heralding tables MUST be keyed by
    # that synthesized path, not an arbitrary caller-chosen one: an
    # unrecognized path guards to success_probability/heralded_fidelity = 0.0
    # (per run.py's `_UncalibratedPathGuardedHeralding`), which would make
    # every herald attempt fail forever and every round retry without bound.
    a = PortId(module_id="M0", port_index=0)
    b = PortId(module_id="M1", port_index=0)
    path = make_path_id(a, b)
    epoch = CalibrationEpoch(
        epoch_id="mm1-decoupled-limit",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.0, CoherenceClass.MEMORY: 0.0},
        memory_access_channel_s=0.0,
        memory_access_wear_rate=0.0,
        heralding_p_per_path={path: 1.0},
        heralded_fidelity_per_path={path: 1.0},
        round_success_logistic_midpoint=-10.0,
        round_success_logistic_slope=1.0,
        round_success_slack_penalty_per_s=0.0,
        decoder_service_rate=mu,
    )
    return RunConfig(
        run_seed=run_seed,
        scheduler="S0",  # no admission control (§8: S0 is the un-augmented baseline)
        epoch=epoch,
        arrival_rate_hz=lam,
        leases_per_round=1,  # one qubit interaction per round (RunConfig has no
                             # separate qubit-count field; qubit topology is
                             # provisioned outside experiments/ scope)
        deadline_slack_s=10_000.0,  # deadlines never bind, so failures never retry
        switch_capacity_c=1,  # single path
        reconfig_delay_s=0.0,
        max_sim_time_s=max_sim_time_s,
        decay_control_enabled=False,  # NoDecayModel: no decay
        memory_cost_control_enabled=False,
    )


def test_mm1_decoder_queue_matches_analytic_wait_in_decoupled_limit(tmp_path):
    """§16.2 decoupled-limit check — named as such, NOT validation of the
    coupled regime: single path, one qubit, decay disabled, memory cost
    disabled, certain heralding. The decoder subsystem alone degenerates to a
    plain M/M/1 queue; its mean sojourn time must match the closed-form
    W = 1/(mu-lambda)."""
    lam, mu = 0.5, 1.0
    config = _mm1_config(run_seed=999, lam=lam, mu=mu, max_sim_time_s=20_000.0)
    run_dir = run(config, tmp_path)
    events = _load_events(run_dir / "events.jsonl")

    sojourns = _decoder_sojourn_times(events)
    assert len(sojourns) > 500, "need enough completed decoder jobs for a stable estimate"

    empirical_w = sum(sojourns) / len(sojourns)
    analytic_w = 1.0 / (mu - lam)
    relative_error = abs(empirical_w - analytic_w) / analytic_w

    assert relative_error < TOLERANCE, (
        f"empirical mean decoder sojourn time {empirical_w:.4f}s deviates from "
        f"M/M/1 analytic W={analytic_w:.4f}s by {relative_error:.2%}"
    )


def test_mm1_decoder_queue_matches_littles_law_in_decoupled_limit(tmp_path):
    """§16.2 decoupled-limit check: Little's Law L = lambda*W, checked against
    this same decoupled M/M/1 run's own measurements, and against the
    closed-form L = rho/(1-rho)."""
    lam, mu = 0.5, 1.0
    max_sim_time_s = 20_000.0
    warmup_s = 2_000.0
    config = _mm1_config(run_seed=999, lam=lam, mu=mu, max_sim_time_s=max_sim_time_s)
    run_dir = run(config, tmp_path)
    events_path = run_dir / "events.jsonl"
    events = _load_events(events_path)

    sojourns = _decoder_sojourn_times(events)
    assert len(sojourns) > 500
    empirical_w = sum(sojourns) / len(sojourns)

    series = decoder_backlog_series(events_path)
    empirical_l = _time_average_backlog(series, warmup_s)

    predicted_l = lam * empirical_w
    analytic_l = lam / (mu - lam)

    relative_error_littles_law = abs(empirical_l - predicted_l) / predicted_l
    relative_error_analytic = abs(empirical_l - analytic_l) / analytic_l

    assert relative_error_littles_law < TOLERANCE, (
        f"L={empirical_l:.4f} vs lambda*W={predicted_l:.4f}: Little's Law "
        f"violated by {relative_error_littles_law:.2%}"
    )
    assert relative_error_analytic < TOLERANCE, (
        f"L={empirical_l:.4f} vs analytic M/M/1 L={analytic_l:.4f}: deviates "
        f"by {relative_error_analytic:.2%}"
    )
