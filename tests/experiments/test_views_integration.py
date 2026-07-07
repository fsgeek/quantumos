"""Integration gate: run the full pipeline, then exercise EVERY observe view
against the REAL events.jsonl a run produces.

This is the gate that was missing. Per-layer TDD tested each consumer against
its own hand-built fixtures, so producer/consumer payload-key drift was
invisible: the engine emits `fidelity_at_herald` / reservation `{round_id,
lease_id}` / `round.failed {reason}`, while the consumers read `fidelity` /
`path_id` / `success_probability`. Nothing ever ran the real producer's output
through the real consumers. This test makes that drift a hard failure.
"""
from pathlib import Path

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.observe import views
from qsim.observe.work_accounting import iter_events
from qsim.experiments.run import run

_PA = make_path_id(PortId("M0", 0), PortId("M1", 0))


def _epoch(**over):
    base = dict(
        epoch_id="e",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.0, CoherenceClass.MEMORY: 0.0},
        memory_access_channel_s=0.0, memory_access_wear_rate=0.0,
        heralding_p_per_path={_PA: 1.0}, heralded_fidelity_per_path={_PA: 0.9},
        round_success_logistic_midpoint=-10.0, round_success_logistic_slope=10.0,
        round_success_slack_penalty_per_s=0.0, decoder_service_rate=1000.0,
    )
    base.update(over)
    return CalibrationEpoch(**base)


def _config(**over):
    base = dict(
        run_seed=7, scheduler="S0", epoch=_epoch(), arrival_rate_hz=1.0,
        leases_per_round=1, deadline_slack_s=100.0, switch_capacity_c=1,
        reconfig_delay_s=0.0, max_sim_time_s=40.0,
    )
    base.update(over)
    return RunConfig(**base)


def _all_views_run(ep: Path) -> None:
    """None of the view functions may raise on a real trace."""
    views.goodput(ep)
    views.freshness_at_consumption(ep)
    views.decoder_backlog_series(ep)
    views.deadline_compliance(ep)
    views.resource_utilization(ep)
    views.logical_error_proxy(ep)
    views.pool_depth_series(ep)


def test_successful_round_consumes_its_leases(tmp_path):
    ep = run(_config(), tmp_path / "run") / "events.jsonl"
    types = [e["event_type"] for e in iter_events(ep)]
    assert "round.completed_in_deadline" in types
    assert types.count("lease.consumed") > 0, (
        "a successful round must CONSUME its leases, not cancel them"
    )
    fresh = views.freshness_at_consumption(ep)
    assert fresh, "freshness_at_consumption must have data once consumption is emitted"
    assert all(0.0 <= f <= 1.0 for f in fresh)


def test_every_view_runs_on_a_real_success_trace(tmp_path):
    ep = run(_config(), tmp_path / "run") / "events.jsonl"
    _all_views_run(ep)


def _pool_gate_config():
    """An S1 run engineered to exercise the FULL pool taxonomy (B3): all four
    paths calibrated with certain heralding so replenishes deposit; scoring
    that always fails (logistic midpoint 10 dwarfs any achievable aggregate
    fidelity) so every round's fresh held lease is RETURNED_TO_POOL; a tight
    freshness bound (deadline_slack_s=2.0 against a multi-second pool-residency
    cycle) so some pooled leases expire at withdrawal; and a capacity-2 fabric
    the replenish attempts contend with, so some are abandoned."""
    ports = [PortId(f"M{i}", 0) for i in range(4)]
    paths = [make_path_id(ports[i], ports[(i + 1) % 4]) for i in range(4)]
    epoch = _epoch(
        heralding_p_per_path={p: 1.0 for p in paths},
        heralded_fidelity_per_path={p: 0.9 for p in paths},
        round_success_logistic_midpoint=10.0,
    )
    return _config(
        scheduler="S1", epoch=epoch, deadline_slack_s=2.0, switch_capacity_c=2,
        admission_theta=0.0, pregen_low_water_mark=2, retry_cap=2,
    )


def test_s1_pool_run_emits_full_pool_taxonomy_and_depth_series_is_consistent(tmp_path):
    ep = run(_pool_gate_config(), tmp_path / "run") / "events.jsonl"

    types = [e["event_type"] for e in iter_events(ep)]
    for pool_type in ("pool.deposited", "pool.withdrawn", "pool.expired",
                      "pool.replenish_abandoned"):
        assert pool_type in types, f"gate run must exercise {pool_type}"
    deposit_sources = {e["payload"]["source"] for e in iter_events(ep)
                       if e["event_type"] == "pool.deposited"}
    assert deposit_sources == {"replenish", "round_return"}

    # Every view (including the new one) consumes the real trace.
    _all_views_run(ep)

    # The depth series reconstructed from the trace ALONE (prereg T1) must be
    # internally consistent: the view's delta-derived running depth equals each
    # event's independently-written payload depth, per key, and never dips
    # below zero.
    series = views.pool_depth_series(ep)
    assert series, "the pool run must produce a non-empty depth series"
    payload_depths: dict[tuple, list[int]] = {}
    for record in iter_events(ep):
        if record["event_type"] not in ("pool.deposited", "pool.withdrawn", "pool.expired"):
            continue
        key = tuple(
            tuple(tuple(p) for p in part) if isinstance(part, list) else part
            for part in record["payload"]["key"]
        )
        payload_depths.setdefault(key, []).append(record["payload"]["depth"])
    assert set(series) == set(payload_depths)
    for key, per_key in series.items():
        depths = [depth for _, depth in per_key]
        assert depths == payload_depths[key]
        assert all(depth >= 0 for depth in depths)


def test_every_view_runs_on_a_real_failure_trace(tmp_path):
    # Capacity contention (fast arrivals, one path held through a reconfig delay)
    # forces round.failed from the pre-scoring _fail_round path, whose payload
    # must still be consumable by logical_error_proxy.
    ep = run(
        _config(arrival_rate_hz=10.0, reconfig_delay_s=0.5, max_sim_time_s=20.0),
        tmp_path / "run",
    ) / "events.jsonl"
    types = [e["event_type"] for e in iter_events(ep)]
    assert "round.failed" in types
    _all_views_run(ep)
