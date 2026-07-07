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


def test_best_heralding_consumes_zero_new_rng_streams(tmp_path):
    ep = run(_config(), tmp_path / "run") / "events.jsonl"
    streams = {e["payload"]["stream"] for e in iter_events(ep)
               if e["event_type"] == "draw.sampled"}
    assert streams, "the run must record draws"
    assert streams <= {"herald", "decode", "round_outcome", "retry", "pool_herald"}, (
        "B1 must not introduce a path-choice draw stream")
