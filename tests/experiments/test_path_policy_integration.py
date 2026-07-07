"""B1 integration gate: the best_heralding path policy through the REAL
pipeline (qsim.experiments.run.run), consumed from events.jsonl alone.

(a) ORDERING — the S2 spatial-ordering evidence: per round, the acquired
    paths reconstructed from reservation.acquired payloads are exactly the
    top-k epoch-enumerated paths in descending heralding_p order.
(b) GATE — every observe view runs over the real best_heralding trace (the
    standing lesson: payload shapes are only protected end-to-end).
(c) CHURN PRESERVED — a contended best_heralding run still emits pre-scoring
    round.failed (capacity/endpoint reasons): the comparative chooser is
    occupancy-blind and did NOT become covert admission control.
(d) ZERO NEW DRAWS — every draw.sampled rides an existing stream; B1 adds no
    path-choice randomness.
"""
from pathlib import Path

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.experiments.run import run
from qsim.observe import views
from qsim.observe.work_accounting import iter_events

_PORTS = [PortId(f"M{i}", 0) for i in range(4)]
_P_BY_PATH = {
    # Three of the four synthesized paths at switch_capacity_c=2, STRICTLY
    # distinct p. Descending: (M0,M1) 0.95, then (M2,M3) 0.85 — endpoint-
    # disjoint, so one round's two leases can hold both concurrently — with
    # (M1,M2) 0.6 the never-picked loser at leases_per_round=2.
    make_path_id(_PORTS[0], _PORTS[1]): 0.95,
    make_path_id(_PORTS[1], _PORTS[2]): 0.6,
    make_path_id(_PORTS[2], _PORTS[3]): 0.85,
}


def _epoch(**over):
    base = dict(
        epoch_id="b1-path-policy-epoch",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.0, CoherenceClass.MEMORY: 0.0},
        memory_access_channel_s=0.0, memory_access_wear_rate=0.0,
        heralding_p_per_path=dict(_P_BY_PATH),
        heralded_fidelity_per_path={p: 0.9 for p in _P_BY_PATH},
        round_success_logistic_midpoint=-10.0, round_success_logistic_slope=10.0,
        round_success_slack_penalty_per_s=0.0, decoder_service_rate=1000.0,
    )
    base.update(over)
    return CalibrationEpoch(**base)


def _config(**over):
    base = dict(
        run_seed=11, scheduler="S0", epoch=_epoch(), arrival_rate_hz=1.0,
        leases_per_round=2, deadline_slack_s=100.0, switch_capacity_c=2,
        reconfig_delay_s=0.0, max_sim_time_s=40.0,
        path_policy="best_heralding",
    )
    base.update(over)
    return RunConfig(**base)


def _acquired_paths_by_round(ep: Path) -> dict[str, list[tuple]]:
    """Chosen paths per round, reconstructed from the trace ALONE: the
    reservation.acquired payload's structured path_id, in acquisition order."""
    by_round: dict[str, list[tuple]] = {}
    for record in iter_events(ep):
        if record["event_type"] != "reservation.acquired":
            continue
        round_id = record["payload"]["round_id"]
        if round_id is None:
            continue  # pool-replenish acquisition (B3), not a round choice
        path = tuple(tuple(part) for part in record["payload"]["path_id"])
        by_round.setdefault(round_id, []).append(path)
    return by_round


def _all_views_run(ep: Path) -> None:
    views.goodput(ep)
    views.freshness_at_consumption(ep)
    views.decoder_backlog_series(ep)
    views.deadline_compliance(ep)
    views.resource_utilization(ep)
    views.logical_error_proxy(ep)
    views.pool_depth_series(ep)


def test_best_heralding_rounds_acquire_top_k_paths_in_descending_p_order(tmp_path):
    ep = run(_config(), tmp_path / "run") / "events.jsonl"

    expected = [
        tuple((p.module_id, p.port_index) for p in path)
        for path in sorted(
            _P_BY_PATH,
            key=lambda path: (-_P_BY_PATH[path],
                              tuple((p.module_id, p.port_index) for p in path)))
    ]
    by_round = _acquired_paths_by_round(ep)
    assert by_round, "the run must acquire reservations"
    # Every round's acquisitions follow the descending-p ranking from the
    # start (a conflicted/failed round may stop early, hence prefix).
    for round_id, paths in by_round.items():
        assert paths == expected[:len(paths)], (
            f"round {round_id} acquired {paths}, not a descending-p prefix")
    # The ordering evidence is only evidence if full top-k rounds exist.
    assert any(len(paths) == 2 for paths in by_round.values()), (
        "no round exercised the full top-k choice")


def test_every_view_runs_on_a_real_best_heralding_trace(tmp_path):
    ep = run(_config(), tmp_path / "run") / "events.jsonl"
    _all_views_run(ep)


def test_contended_best_heralding_still_churns_not_covert_admission_control(tmp_path):
    # Fast arrivals against a held fabric (nonzero reconfig delay): the
    # chooser keeps naming the SAME best paths regardless of occupancy, so §7
    # denies them engine-side and the round churns — exactly S0 semantics.
    ep = run(
        _config(arrival_rate_hz=10.0, reconfig_delay_s=0.5, max_sim_time_s=20.0,
                retry_cap=2),
        tmp_path / "run",
    ) / "events.jsonl"
    reasons = {e["payload"]["reason"] for e in iter_events(ep)
               if e["event_type"] == "round.failed"
               and e["payload"]["success_probability"] is None}
    assert reasons, "the contended run must fail rounds pre-scoring"
    assert reasons <= {"switch_capacity_exhausted", "endpoint_conflict"}
    _all_views_run(ep)


def test_s1_pools_track_the_best_heralding_demanded_keys_not_the_adjacent_ring(tmp_path):
    # B1 review should-fix regression probe: BestHeraldingPathChoice demands
    # the argmax-p EPOCH-ENUMERATED path — here the non-adjacent (M0, M2) at
    # switch_capacity_c=2 — but tracked_keys used to be derived from the
    # round-robin-adjacent synthesized_path_universe, so the ONE key every
    # round demanded had no pool (0 pool.withdrawn; unconsumed leases fell to
    # round-bound disposal) while POOL_REPLENISH kept four never-demanded
    # adjacent pools at depth L, burning §7 reservation slots against round
    # demand. The pool must serve the demanded key, and mint NOTHING outside
    # the policy's demandable set.
    ports = [PortId(f"M{i}", 0) for i in range(4)]
    demanded = make_path_id(ports[0], ports[2])
    epoch = _epoch(heralding_p_per_path={demanded: 0.95},
                   heralded_fidelity_per_path={demanded: 0.9})
    config = _config(scheduler="S1", epoch=epoch, leases_per_round=1,
                     admission_theta=0.0, pregen_low_water_mark=2)
    ep = run(config, tmp_path / "run") / "events.jsonl"

    demanded_path_payload = [["M0", 0], ["M2", 0]]
    pool_events = [e for e in iter_events(ep)
                   if e["event_type"].startswith("pool.")]
    assert any(e["payload"]["key"][0] == demanded_path_payload
               for e in pool_events if e["event_type"] == "pool.withdrawn"), (
        "the demanded (M0, M2) key was never served from its pool — pooling "
        "is silently disabled for exactly the path best_heralding demands")
    # No pool activity outside the demandable set: an undemandable pool can
    # never relieve round demand, only contend with it for §7 capacity.
    off_universe = [e["payload"]["key"][0] for e in pool_events
                    if e["payload"]["key"][0] != demanded_path_payload]
    assert not off_universe, (
        f"pool activity on undemandable keys: {off_universe}")
    _all_views_run(ep)


def test_best_heralding_consumes_zero_new_rng_streams(tmp_path):
    ep = run(_config(), tmp_path / "run") / "events.jsonl"
    streams = {e["payload"]["stream"] for e in iter_events(ep)
               if e["event_type"] == "draw.sampled"}
    assert streams, "the run must record draws"
    assert streams <= {"herald", "decode", "round_outcome", "retry", "pool_herald"}, (
        "B1 must not introduce a path-choice draw stream")
