"""Engine unit E2 — Task 3: heralding attempt loop.

Adapted from the engine-task-3 brief per the AUTHORITATIVE reconciliation spec
(.superpowers/sdd/engine-reconciliation-spec.md). The brief's assertions about
trace event types, entity state, timing, and causal parents are UNCHANGED. The
adaptations are mechanical, forced by the real (frozen) interfaces:
  * TraceBus's real signature requires a SimClock, so one is constructed and
    passed (the brief's `TraceBus(run_id=...)` omitted it).
  * The ModelBundle is built via test_engine.make_models(), whose
    LogisticRoundSuccessModel / ExponentialDecoderServiceModel take the
    constructor arguments the real classes require (the brief called them with
    no args).
  * Reconciliation spec §3: there is NO scheduler herald callback — the engine
    tracks heralding in _RoundContext itself. This test asserts that engine
    bookkeeping, not any scheduler side effect.
"""

from collections import defaultdict

from tests.core.test_engine import make_config, make_workload, make_epoch, make_models
from qsim.core.clock import SimClock
from qsim.core.trace import TraceBus
from qsim.core.invariants import InvariantChecker
from qsim.core.engine import Engine
from qsim.policies.s0 import S0Scheduler
from qsim.entities import LeaseState


def _epoch_with_full_heralding():
    epoch = make_epoch()
    # The path is chosen by the engine at arrival time; BernoulliHeraldingModel
    # reads epoch.heralding_p_per_path[path], so a defaultdict supplies a p=1.0
    # / fidelity=0.9 default for whatever concrete path the engine picks,
    # without guessing its exact key.
    object.__setattr__(epoch, "heralding_p_per_path", defaultdict(lambda: 1.0))
    object.__setattr__(epoch, "heralded_fidelity_per_path", defaultdict(lambda: 0.9))
    return epoch


def test_heralding_succeeds_on_first_attempt_when_probability_is_one():
    first_round = make_workload().next_arrival(0.0, 1)
    config = make_config(switch_capacity_c=2)
    config = config.__class__(**{**config.__dict__, "epoch": _epoch_with_full_heralding()})

    events = []
    clock = SimClock()
    trace = TraceBus(run_id="test-run", clock=clock)
    trace.subscribe(events.append)
    engine = Engine(config=config, scheduler=S0Scheduler(), models=make_models(),
                    workload=make_workload(), trace=trace, invariants=InvariantChecker())

    engine.run_to(first_round.arrival_time + config.reconfig_delay_s + 1e-6)

    types = [e.event_type for e in events]
    assert "draw.sampled" in types
    assert "lease.heralded" in types
    assert "reservation.released" in types

    lease_id = first_round.lease_ids[0]
    lease = engine._round_contexts[first_round.round_id].leases[lease_id]
    assert lease.state == LeaseState.HERALDED
    assert lease.fidelity_at_herald == 0.9

    heralded_evt = events[types.index("lease.heralded")]
    assert heralded_evt.causal_parent_id is not None
    released_evt = events[types.index("reservation.released")]
    assert released_evt.sim_time == heralded_evt.sim_time
