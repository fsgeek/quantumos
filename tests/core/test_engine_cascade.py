"""Engine unit E3 — Task 7: §5 failure-cleanup cascade.

Written against the AUTHORITATIVE reconciliation spec
(.superpowers/sdd/engine-reconciliation-spec.md). On round failure the engine
runs the §5 cascade BEFORE publishing round.failed: cancel a pending decoder
job, ask the scheduler how to dispose held leases (on_round_terminal), cancel
any still-unheralded round-bound lease, and release every still-active
reservation the round holds. For S0 (no pregen) the disposition is round-bound
cancellation — never a pool return or expiry.

Adapted from the engine-task-7 brief for the RECONCILED engine: the round
deadline is set by the WorkloadGenerator, not by RunConfig.deadline_slack_s, so
this test builds a workload with a small deadline slack (rather than relying on
config.deadline_slack_s) to make heralding — which always fails, p=0.0 — exceed
the deadline inside the run window. The brief's model constructors take their
real config-parameterized args, and TraceBus takes the shared SimClock. The
brief's assertions about trace event types and their ordering relative to
round.failed are unchanged.
"""

from collections import defaultdict

from qsim.core.clock import SimClock
from qsim.core.trace import TraceBus
from qsim.core.invariants import InvariantChecker
from qsim.core.state import ModelBundle
from qsim.core.engine import Engine
from qsim.policies.s0 import S0Scheduler
from qsim.workload.generator import WorkloadGenerator
from qsim.models.decay import NoDecayModel
from qsim.models.memory_access import ZeroCostMemoryAccessModel
from qsim.models.heralding import BernoulliHeraldingModel
from qsim.models.round_success import LogisticRoundSuccessModel
from qsim.models.decoder_service import ExponentialDecoderServiceModel

from tests.core.test_engine import (
    make_config, make_models, make_epoch, make_workload, RUN_SEED, ARRIVAL_RATE_HZ,
)

# Small enough that heralding (p=0.0, retried every HERALD_RETRY_INTERVAL_S)
# exceeds the round deadline well inside the run window; the round deadline is
# WorkloadGenerator-set, so the workload — not RunConfig — carries this slack.
_SMALL_DEADLINE_SLACK_S = 0.01


def _epoch_heralding_always_fails():
    epoch = make_epoch()
    object.__setattr__(epoch, "heralding_p_per_path", defaultdict(lambda: 0.0))
    object.__setattr__(epoch, "heralded_fidelity_per_path", defaultdict(lambda: 0.9))
    return epoch


def _models():
    # Heralding never succeeds, so round_success / decoder_service are never
    # reached; they still need valid (config-parameterized) constructors.
    return ModelBundle(
        decay=NoDecayModel(),
        memory_access=ZeroCostMemoryAccessModel(),
        heralding=BernoulliHeraldingModel(),
        round_success=LogisticRoundSuccessModel(
            logistic_midpoint=0.5, logistic_slope=10.0, slack_penalty_per_s=0.0),
        decoder_service=ExponentialDecoderServiceModel(service_rate=1000.0),
    )


def _small_slack_workload():
    return WorkloadGenerator(run_seed=RUN_SEED, arrival_rate_hz=ARRIVAL_RATE_HZ,
                             leases_per_round=1, deadline_slack_s=_SMALL_DEADLINE_SLACK_S)


def test_round_bound_cascade_cancels_reservation_when_heralding_never_succeeds():
    first_round = _small_slack_workload().next_arrival(0.0, 1)
    config = make_config(switch_capacity_c=2)
    config = config.__class__(**{**config.__dict__, "epoch": _epoch_heralding_always_fails(),
                                 "deadline_slack_s": _SMALL_DEADLINE_SLACK_S})

    events = []
    clock = SimClock()
    trace = TraceBus(run_id="test-run", clock=clock)
    trace.subscribe(events.append)
    engine = Engine(config=config, scheduler=S0Scheduler(), models=_models(),
                    workload=_small_slack_workload(), trace=trace,
                    invariants=InvariantChecker())
    engine.run_to(first_round.arrival_time + config.reconfig_delay_s + 1.0)

    types = [e.event_type for e in events]
    assert "round.failed" in types
    assert "reservation.released" in types
    # S0 is round-bound (no pregen configured): the leftover unheralded lease
    # is cancelled outright, not returned to a pool or expired.
    assert any(e.event_type == "lease.cancelled" for e in events)
    assert not any(e.event_type in ("lease.pool_returned", "lease.expired") for e in events)

    failed_idx = types.index("round.failed")
    cascade_types_before_failed = types[:failed_idx]
    assert "reservation.released" in cascade_types_before_failed
    assert "lease.cancelled" in cascade_types_before_failed


def test_cascade_releases_only_the_failing_rounds_reservation_not_a_peers():
    # Two capacity-1 rounds contend for the single path. r1 acquires it and —
    # make_models's empty heralding epoch yields p=0.0, so r1 never heralds —
    # holds the reservation across the (default 10 s) deadline; r2 is admitted
    # then fails on capacity. r2's cascade must release NOTHING it does not own:
    # r1's reservation survives, and no lease.cancelled is emitted for r2 (its
    # lease.requested was never published — the capacity check precedes it — so
    # cancelling it would be an illegal None->cancelled transition the invariant
    # would reject). Uses the default-deadline workload so r1 keeps the path long
    # enough for the contention to actually occur.
    config = make_config(switch_capacity_c=1)

    events = []
    clock = SimClock()
    trace = TraceBus(run_id="test-run", clock=clock)
    trace.subscribe(events.append)
    engine = Engine(config=config, scheduler=S0Scheduler(), models=make_models(),
                    workload=make_workload(), trace=trace,
                    invariants=InvariantChecker())

    wl = make_workload()
    r1 = wl.next_arrival(0.0, 1)
    r2 = wl.next_arrival(r1.arrival_time, 2)
    engine.run_to(r2.arrival_time + 1e-9)

    failed = [e for e in events if e.event_type == "round.failed"]
    assert failed and failed[0].entity_id == r2.round_id
    # r1 still holds its live reservation; r2 owns none.
    from qsim.entities import ReservationState
    live = [r for r in engine._state.active_reservations.values()
            if r.state != ReservationState.RELEASED]
    assert len(live) == 1 and live[0].holder_id == r1.round_id
    # No phantom cancellation for r2's never-requested lease.
    r2_lease_cancels = [e for e in events
                        if e.event_type == "lease.cancelled"
                        and e.payload.get("round_id") == r2.round_id]
    assert r2_lease_cancels == []
