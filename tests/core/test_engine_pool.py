"""Engine B3: pregen pool replenish servicing, withdrawal, and the bounded
drain (design spec §8.2; prereg 2026-07-06 build B3).

The engine services POOL_REPLENISH requests as §8.2 generation attempts —
switch-path reservation (holder_id = request_id, never a round id) + exactly
ONE keyed Bernoulli herald attempt on the "pool_herald" CRN stream — and
satisfies ROUND lease demand from EngineState.pool (the authoritative side of
R3) before the §7 capacity/endpoint checks. All pool.* events are annotations.
"""
from collections import defaultdict
from dataclasses import replace

from qsim.core.clock import SimClock
from qsim.core.engine import Engine, synthesized_path_universe
from qsim.core.invariants import InvariantChecker
from qsim.core.trace import TraceBus
from qsim.entities import (
    CoherenceClass,
    EntanglementLease,
    LeaseState,
    PortId,
    make_path_id,
)
from qsim.policies.pregen import PregenMixin
from qsim.policies.protocol import ProjectableLease
from qsim.policies.s0 import S0Scheduler
from qsim.models.decay import ExponentialDecayModel
from qsim.core.state import ModelBundle
from qsim.models.memory_access import ZeroCostMemoryAccessModel
from qsim.models.heralding import BernoulliHeraldingModel
from qsim.models.round_success import LogisticRoundSuccessModel
from qsim.models.decoder_service import ExponentialDecoderServiceModel

from qsim.workload.generator import WorkloadGenerator

from tests.core.test_engine import (
    ARRIVAL_RATE_HZ, DEADLINE_SLACK_S, RUN_SEED,
    make_config, make_epoch, make_models, make_workload,
)

_P01 = make_path_id(PortId("M0", 0), PortId("M1", 0))
_P23 = make_path_id(PortId("M2", 0), PortId("M3", 0))
_MSG = CoherenceClass.MESSENGER


class _PoolingS0(PregenMixin, S0Scheduler):
    pass


def _epoch_all_paths_herald(p=1.0, fidelity=0.9):
    epoch = make_epoch()
    object.__setattr__(epoch, "heralding_p_per_path", defaultdict(lambda: p))
    object.__setattr__(epoch, "heralded_fidelity_per_path", defaultdict(lambda: fidelity))
    return epoch


def _config(**over):
    base = make_config(switch_capacity_c=over.pop("switch_capacity_c", 2))
    return replace(base, epoch=_epoch_all_paths_herald(), **over)


def _build_engine(config, scheduler, models=None, workload=None):
    events = []
    clock = SimClock()
    trace = TraceBus(run_id="test-run", clock=clock)
    trace.subscribe(events.append)
    engine = Engine(config=config, scheduler=scheduler,
                    models=models if models is not None else make_models(),
                    workload=workload if workload is not None else make_workload(),
                    trace=trace,
                    invariants=InvariantChecker())
    return engine, events


def _run_engine(config, scheduler, run_to_s):
    engine, events = _build_engine(config, scheduler)
    engine.run_to(run_to_s)
    return engine, events


def _decaying_models():
    # Real exponential decay + a round-success curve that (midpoint -10)
    # succeeds with p ~= 1, so consumption happens and its fidelity is
    # assertable against the decay law.
    return ModelBundle(
        decay=ExponentialDecayModel(),
        memory_access=ZeroCostMemoryAccessModel(),
        heralding=BernoulliHeraldingModel(),
        round_success=LogisticRoundSuccessModel(
            logistic_midpoint=-10.0, logistic_slope=10.0, slack_penalty_per_s=0.0),
        decoder_service=ExponentialDecoderServiceModel(service_rate=1000.0),
    )


def _seed_pool(engine, scheduler, key, lease_id, heralded_at, fidelity,
               freshness_bound_s):
    """Deposit one already-heralded lease into BOTH pool sides (the paired
    R3 mutation the engine performs at replenish/round-return time)."""
    path_id, coherence = key
    lease = EntanglementLease(
        lease_id=lease_id, endpoints=path_id, path_id=path_id,
        created_at=heralded_at, freshness_bound_s=freshness_bound_s,
        fidelity_at_herald=fidelity, heralded_at=heralded_at,
        state=LeaseState.HERALDED,
    )
    engine._state.pool.setdefault(key, []).append(lease)
    scheduler.deposit_to_pool(ProjectableLease(
        path_id=path_id, coherence_class=coherence, is_held=True,
        is_consumed=False, state_held_since=heralded_at,
        freshness_bound_s=freshness_bound_s, heralded_fidelity_estimate=fidelity))


def _first_arrival_time():
    return make_workload().next_arrival(0.0, 1).arrival_time


def test_synthesized_path_universe_is_the_engines_adjacent_pair_set():
    # capacity 2 -> 4 ports M0..M3 -> the four round-robin-adjacent pairs.
    assert synthesized_path_universe(2) == [
        _P01,
        make_path_id(PortId("M1", 0), PortId("M2", 0)),
        _P23,
        make_path_id(PortId("M3", 0), PortId("M0", 0)),
    ]
    # capacity 0/1 -> the max(2, 2C) floor: 2 ports, ONE deduplicated path
    # ((M0,M1) and (M1,M0) canonicalize identically).
    assert synthesized_path_universe(1) == [_P01]
    assert synthesized_path_universe(0) == [_P01]


def test_replenish_success_reserves_heralds_once_deposits_and_releases():
    key = (_P23, _MSG)
    scheduler = _PoolingS0(low_water_mark=1, tracked_keys=[key])
    engine, events = _run_engine(_config(), scheduler, _first_arrival_time() + 1e-6)

    # The replenish reservation ran the §7 lifecycle on the tracked path with
    # NO round identity: holder is the request, not a round.
    res = [e for e in events if e.event_type.startswith("reservation.")
           and e.entity_id == "M2:0->M3:0"]
    assert [e.event_type for e in res] == [
        "reservation.acquired", "reservation.configuring",
        "reservation.active", "reservation.released"]
    assert all(e.payload["round_id"] is None for e in res)
    assert res[0].payload["request_id"].startswith("pool-")

    # Exactly ONE keyed Bernoulli attempt on the new named stream.
    draws = [e for e in events if e.event_type == "draw.sampled"
             and e.payload["stream"] == "pool_herald"]
    assert len(draws) == 1
    assert draws[0].payload["key"] == [
        "pool_herald", (("M2", 0), ("M3", 0)), "messenger", 1]

    # Success deposits: annotation published, BOTH pools grew in lockstep.
    deposits = [e for e in events if e.event_type == "pool.deposited"]
    assert len(deposits) == 1
    assert deposits[0].payload["source"] == "replenish"
    assert deposits[0].payload["round_id"] is None
    assert deposits[0].payload["depth"] == 1
    assert deposits[0].payload["key"] == [[["M2", 0], ["M3", 0]], "messenger"]
    assert len(engine._state.pool[key]) == 1
    assert scheduler.pool_depth(key) == 1
    assert engine._state.pool[key][0].state is LeaseState.HERALDED
    assert engine._state.pool[key][0].fidelity_at_herald == 0.9
    # In-flight slot released on resolution.
    assert scheduler._in_flight[key] == 0
    # No lease.* lifecycle events for the pooled lease: its identity opens at
    # withdrawal time, on the consuming round's own lease_id.
    pooled_lease_id = deposits[0].payload["lease_id"]
    assert not any(e.event_type.startswith("lease.") and e.entity_id == pooled_lease_id
                   for e in events)


def test_replenish_reservation_released_even_under_hold_until_consumption():
    key = (_P23, _MSG)
    scheduler = _PoolingS0(low_water_mark=1, tracked_keys=[key])
    engine, events = _run_engine(_config(hold_until_consumption=True), scheduler,
                                 _first_arrival_time() + 1e-6)

    # §8.2: the generation attempt's scope ENDS at herald resolution — holding
    # a path for a pooled lease would couple pool residency to fabric occupancy.
    released = [e for e in events if e.event_type == "reservation.released"
                and e.entity_id == "M2:0->M3:0"]
    assert len(released) == 1
    assert _P23 not in engine._state.active_reservations


def test_saturated_capacity_denies_replenish_ends_drain_and_terminates():
    # The run.py:24-30 hazard: non-empty tracked_keys over a fabric with zero
    # capacity. Every admission's drain pass mints at most one replenish, which
    # is denied and ENDS the pass — run_to() must terminate (this test
    # finishing IS the assertion) instead of drain-looping forever on a
    # perpetually empty pool.
    key = (_P01, _MSG)
    scheduler = _PoolingS0(low_water_mark=1, tracked_keys=[key])
    _, events = _run_engine(_config(switch_capacity_c=0), scheduler,
                            _first_arrival_time() + 2.0)

    abandoned = [e for e in events if e.event_type == "pool.replenish_abandoned"]
    assert abandoned, "denied replenishes must leave a trace"
    assert all(e.payload["reason"] == "switch_capacity_exhausted" for e in abandoned)
    assert not any(e.event_type == "pool.deposited" for e in events)
    # Bounded: one drain pass per admission, at most one denial per pass.
    admitted = [e for e in events if e.event_type == "round.admitted"]
    assert len(abandoned) <= len(admitted)
    assert scheduler._in_flight[key] == 0


def test_p_zero_path_replenish_is_bounded_by_in_flight_accounting():
    # p=0 variant: attempts reserve, herald-fail, and re-arm — but never more
    # than L in flight per key, so the draw count is bounded by the number of
    # drain passes (admissions), not by the pool's perpetual emptiness.
    key = (_P23, _MSG)  # disjoint from the first round's P01, so attempts reserve
    scheduler = _PoolingS0(low_water_mark=1, tracked_keys=[key])
    config = make_config(switch_capacity_c=2)  # uncalibrated epoch: p=0 everywhere
    _, events = _run_engine(config, scheduler, _first_arrival_time() + 2.0)

    pool_draws = [e for e in events if e.event_type == "draw.sampled"
                  and e.payload["stream"] == "pool_herald"]
    admitted = [e for e in events if e.event_type == "round.admitted"]
    assert pool_draws, "the p=0 attempts must actually reach the draw"
    assert len(pool_draws) <= len(admitted)
    herald_failures = [e for e in events if e.event_type == "pool.replenish_abandoned"
                       and e.payload["reason"] == "herald_failed"]
    assert len(herald_failures) == len(pool_draws)
    assert scheduler._in_flight[key] == 0


def test_replenish_herald_failure_abandons_and_re_arms():
    key = (_P23, _MSG)
    scheduler = _PoolingS0(low_water_mark=1, tracked_keys=[key])
    # make_epoch calibrates NO paths: the engine's p=0.0 uncalibrated-path
    # guard applies to the pool herald draw exactly as to round heralds.
    config = make_config(switch_capacity_c=2)
    engine, events = _run_engine(config, scheduler, _first_arrival_time() + 1e-6)

    abandoned = [e for e in events if e.event_type == "pool.replenish_abandoned"]
    assert len(abandoned) == 1
    assert abandoned[0].payload["reason"] == "herald_failed"
    assert abandoned[0].payload["depth"] == 0
    assert not any(e.event_type == "pool.deposited" for e in events)
    assert engine._state.pool.get(key, []) == []
    assert scheduler.pool_depth(key) == 0
    assert scheduler._in_flight[key] == 0
    # Reservation released at resolution despite the failure.
    released = [e for e in events if e.event_type == "reservation.released"
                and e.entity_id == "M2:0->M3:0"]
    assert len(released) == 1


def test_pool_hit_satisfies_round_demand_without_reservation_and_ages_continuously():
    key = (_P01, _MSG)
    scheduler = _PoolingS0(low_water_mark=0, tracked_keys=[key])
    epoch = _epoch_all_paths_herald()
    object.__setattr__(epoch, "decay_rate_per_class",
                       {_MSG: 0.05, CoherenceClass.MEMORY: 0.02})
    config = replace(make_config(switch_capacity_c=2), epoch=epoch)
    engine, events = _build_engine(config, scheduler, models=_decaying_models())
    _seed_pool(engine, scheduler, key, "pooled-1", heralded_at=0.0,
               fidelity=0.9, freshness_bound_s=100.0)

    # Window ends before the SECOND arrival (~0.47s later), whose ordinary
    # reservation+herald acquisition would muddy the no-reservation assertion.
    engine.run_to(_first_arrival_time() + 0.3)

    round_id = [e for e in events if e.event_type == "round.arrived"][0].entity_id
    # The legal chain None -> requested -> heralded on the CONSUMING round's own
    # lease_id, with the pool annotation between: no resurrection of pooled-1.
    types = [e.event_type for e in events]
    i_req = types.index("lease.requested")
    i_wd = types.index("pool.withdrawn")
    i_her = types.index("lease.heralded")
    assert i_req < i_wd < i_her
    requested = events[i_req]
    withdrawn = events[i_wd]
    heralded = events[i_her]
    assert requested.entity_id != "pooled-1"  # the round's own lease id
    assert heralded.entity_id == requested.entity_id
    assert heralded.payload["source"] == "pool"
    assert heralded.payload["pooled_lease_id"] == "pooled-1"
    assert heralded.payload["fidelity_at_herald"] == 0.9
    assert withdrawn.payload["pooled_lease_id"] == "pooled-1"
    assert withdrawn.payload["lease_id"] == requested.entity_id
    assert withdrawn.payload["round_id"] == round_id
    assert withdrawn.payload["depth"] == 0

    # A pool hit reserves NOTHING: the §7 lifecycle never runs.
    assert not any(t.startswith("reservation.") for t in types)

    # Assembly proceeded to the decoder off the pooled state.
    assert "decoder.enqueued" in types

    # Decay continuity: the round's lease adopted the ORIGINAL heralded_at
    # (t=0.0), so fidelity at consumption ages across pool residency — zero
    # new physics, the existing lazy decay law evaluated over the full span.
    consumed = [e for e in events if e.event_type == "lease.consumed"]
    assert len(consumed) == 1
    expected = 0.9 * ExponentialDecayModel().retention(
        consumed[0].sim_time - 0.0, CoherenceClass.MEMORY, epoch)
    assert consumed[0].payload["fidelity_at_consumption"] == expected

    # Depth agreement (R3) after the withdrawal.
    assert len(engine._state.pool[key]) == 0
    assert scheduler.pool_depth(key) == 0


def test_pool_hit_relieves_a_capacity_exhausted_fabric():
    # At capacity 0 S0 churns (admit -> fail -> retry); a pooled lease on the
    # demanded key satisfies the round with no reservation, so it SUCCEEDS.
    key = (_P01, _MSG)
    scheduler = _PoolingS0(low_water_mark=0, tracked_keys=[key])
    config = _config(switch_capacity_c=0)
    engine, events = _build_engine(config, scheduler, models=_decaying_models())
    _seed_pool(engine, scheduler, key, "pooled-1", heralded_at=0.0,
               fidelity=0.9, freshness_bound_s=100.0)

    engine.run_to(_first_arrival_time() + 1e-3)

    round_id = [e for e in events if e.event_type == "round.arrived"][0].entity_id
    assert not any(e.event_type == "round.failed" and e.entity_id == round_id
                   for e in events)
    assert any(e.event_type == "pool.withdrawn" for e in events)
    assert "decoder.enqueued" in [e.event_type for e in events]


def test_stale_pooled_lease_expires_at_withdrawal_and_falls_through_to_heralding():
    key = (_P01, _MSG)
    scheduler = _PoolingS0(low_water_mark=0, tracked_keys=[key])
    engine, events = _build_engine(_config(), scheduler)
    # Stale by arrival time (~0.29s > 0.01s bound).
    _seed_pool(engine, scheduler, key, "stale-1", heralded_at=0.0,
               fidelity=0.9, freshness_bound_s=0.01)

    engine.run_to(_first_arrival_time() + 1e-6)

    expired = [e for e in events if e.event_type == "pool.expired"]
    assert len(expired) == 1
    assert expired[0].payload["lease_id"] == "stale-1"
    assert expired[0].payload["depth"] == 0
    # Both pool sides shrank in lockstep.
    assert len(engine._state.pool[key]) == 0
    assert scheduler.pool_depth(key) == 0
    # The stale lease was never reused...
    assert not any(e.event_type == "pool.withdrawn" for e in events)
    # ...and the round fell through to the normal §7 reservation + herald path.
    types = [e.event_type for e in events]
    assert "reservation.acquired" in types
    heralded = [e for e in events if e.event_type == "lease.heralded"]
    assert len(heralded) == 1
    assert "source" not in heralded[0].payload


def _two_lease_workload():
    # Same arrival stream as make_workload (identical seed/rate: leases_per_round
    # does not enter the arrival draw, so _first_arrival_time() stays valid),
    # but each round demands TWO leases. At switch_capacity_c=1 (2 ports) the
    # ordinals get endpoint pairs (M0,M1) and (M1,M0), which canonicalize to
    # ONE PathId — the within-round path-collision regime.
    return WorkloadGenerator(run_seed=RUN_SEED, arrival_rate_hz=ARRIVAL_RATE_HZ,
                             leases_per_round=2, deadline_slack_s=DEADLINE_SLACK_S)


def test_within_round_path_collision_after_pool_hit_fails_round_not_the_run():
    # B3 review must-fix: with both of a round's leases collapsed onto one
    # canonical path, ctx.path_to_lease resolves BOTH requests to a single
    # lease_id. Pre-B3 the §7 checks always failed such a round — the first
    # request's live reservation blocked the second before it published
    # anything. A pool hit holds NO reservation, so without the explicit
    # collision guard the second request re-publishes lease.requested for an
    # already-HERALDED lease_id: an illegal transition that fail-stops the
    # WHOLE run. The guard must fail the ROUND instead, exactly as §7 would.
    key = (_P01, _MSG)
    scheduler = _PoolingS0(low_water_mark=0, tracked_keys=[key])
    engine, events = _build_engine(_config(switch_capacity_c=1), scheduler,
                                   models=_decaying_models(),
                                   workload=_two_lease_workload())
    _seed_pool(engine, scheduler, key, "pooled-1", heralded_at=0.0,
               fidelity=0.9, freshness_bound_s=100.0)

    # Completing without an InvariantViolation is itself half the assertion.
    engine.run_to(_first_arrival_time() + 1e-6)

    # The first request was satisfied from the pool...
    assert len([e for e in events if e.event_type == "pool.withdrawn"]) == 1
    # ...and the colliding second request failed the ROUND: exactly one
    # lease.requested ever published for the shared lease_id.
    requested = [e for e in events if e.event_type == "lease.requested"]
    assert len(requested) == 1
    failed = [e for e in events if e.event_type == "round.failed"]
    assert len(failed) == 1
    assert failed[0].payload["reason"] == "endpoint_conflict"


def test_within_round_path_collision_at_pool_depth_two_withdraws_only_once():
    # Depth >= 2 variant of the same must-fix: the colliding second request
    # must not re-enter withdrawal and pop a SECOND pooled lease for the same
    # already-HERALDED lease_id (that publish crashes inside
    # _try_pool_withdrawal instead of the fall-through path).
    key = (_P01, _MSG)
    scheduler = _PoolingS0(low_water_mark=0, tracked_keys=[key])
    engine, events = _build_engine(_config(switch_capacity_c=1), scheduler,
                                   models=_decaying_models(),
                                   workload=_two_lease_workload())
    _seed_pool(engine, scheduler, key, "pooled-1", heralded_at=0.0,
               fidelity=0.9, freshness_bound_s=100.0)
    _seed_pool(engine, scheduler, key, "pooled-2", heralded_at=0.0,
               fidelity=0.9, freshness_bound_s=100.0)

    engine.run_to(_first_arrival_time() + 1e-6)

    withdrawn = [e for e in events if e.event_type == "pool.withdrawn"]
    assert [e.payload["pooled_lease_id"] for e in withdrawn] == ["pooled-1"]
    failed = [e for e in events if e.event_type == "round.failed"]
    assert len(failed) == 1
    assert failed[0].payload["reason"] == "endpoint_conflict"
    # pooled-2 never left the pool (both mirror sides agree).
    assert "pooled-2" in [lease.lease_id for lease in engine._state.pool[key]]


def test_c1_reservation_release_is_a_drain_opportunity_that_fills_the_pool():
    # B3 review finding: replenishes minted ONLY inside the admission drain
    # always lose to the admitting round's own reservation at C=1 — every
    # attempt abandons switch_capacity_exhausted and the pool NEVER fills
    # under healthy operation (the shipped examples/s1-admission.toml regime).
    # Releasing a reservation must be a drain opportunity so the freed slot
    # can immediately host the §8.2 generation attempt.
    key = (_P01, _MSG)
    scheduler = _PoolingS0(low_water_mark=1, tracked_keys=[key])
    engine, events = _run_engine(_config(switch_capacity_c=1), scheduler,
                                 _first_arrival_time() + 0.2)

    deposits = [e for e in events if e.event_type == "pool.deposited"]
    assert deposits, "the C=1 pool must fill under healthy (non-churn) operation"
    assert deposits[0].payload["source"] == "replenish"


def test_stale_head_is_skipped_and_the_fresh_next_lease_is_withdrawn():
    key = (_P01, _MSG)
    scheduler = _PoolingS0(low_water_mark=0, tracked_keys=[key])
    engine, events = _build_engine(_config(), scheduler, models=_decaying_models())
    _seed_pool(engine, scheduler, key, "stale-1", heralded_at=0.0,
               fidelity=0.9, freshness_bound_s=0.01)
    fresh_heralded_at = _first_arrival_time() - 0.001
    _seed_pool(engine, scheduler, key, "fresh-2", heralded_at=fresh_heralded_at,
               fidelity=0.9, freshness_bound_s=100.0)

    engine.run_to(_first_arrival_time() + 1e-6)

    expired = [e for e in events if e.event_type == "pool.expired"]
    withdrawn = [e for e in events if e.event_type == "pool.withdrawn"]
    assert [e.payload["lease_id"] for e in expired] == ["stale-1"]
    assert expired[0].payload["depth"] == 1
    assert [e.payload["pooled_lease_id"] for e in withdrawn] == ["fresh-2"]
    assert withdrawn[0].payload["depth"] == 0
    assert len(engine._state.pool[key]) == 0
    assert scheduler.pool_depth(key) == 0


def test_pool_herald_attempts_retries_on_one_reservation_then_abandons():
    # Retain-and-retry replenishment arm (the Q4 protocol asymmetry; Gemini
    # disposition 2026-07-16): pool_herald_attempts=3 on an uncalibrated
    # (p=0) tracked path takes THREE bounded draws on ONE reservation —
    # acquired/configuring/active/released exactly once — publishes ONE
    # herald_failed abandonment at the final draw, and releases at resolution.
    key = (_P23, _MSG)
    scheduler = _PoolingS0(low_water_mark=1, tracked_keys=[key])
    config = replace(make_config(switch_capacity_c=2), pool_herald_attempts=3)
    engine, events = _run_engine(config, scheduler, _first_arrival_time() + 1e-3)

    res = [e for e in events if e.event_type.startswith("reservation.")
           and e.entity_id == "M2:0->M3:0"]
    assert [e.event_type for e in res] == [
        "reservation.acquired", "reservation.configuring",
        "reservation.active", "reservation.released"]

    draws = [e for e in events if e.event_type == "draw.sampled"
             and e.payload["stream"] == "pool_herald"]
    assert len(draws) == 3
    assert [d.payload["key"][3] for d in draws] == [1, 2, 3]

    abandoned = [e for e in events if e.event_type == "pool.replenish_abandoned"]
    assert len(abandoned) == 1
    assert abandoned[0].payload["reason"] == "herald_failed"
    assert scheduler._in_flight[key] == 0
    assert _P23 not in engine._state.active_reservations


def test_pool_herald_attempts_stops_at_first_success():
    # N > 1 must not change the success path: one draw, one deposit, release
    # at resolution, no abandonment.
    key = (_P23, _MSG)
    scheduler = _PoolingS0(low_water_mark=1, tracked_keys=[key])
    engine, events = _run_engine(_config(pool_herald_attempts=3), scheduler,
                                 _first_arrival_time() + 1e-6)

    draws = [e for e in events if e.event_type == "draw.sampled"
             and e.payload["stream"] == "pool_herald"]
    assert len(draws) == 1
    deposits = [e for e in events if e.event_type == "pool.deposited"]
    assert len(deposits) == 1
    assert not any(e.event_type == "pool.replenish_abandoned" for e in events)
    released = [e for e in events if e.event_type == "reservation.released"
                and e.entity_id == "M2:0->M3:0"]
    assert len(released) == 1
    assert _P23 not in engine._state.active_reservations
