"""Engine unit E3 — Task 6: round-success scoring and terminal outcomes.

Written against the AUTHORITATIVE reconciliation spec
(.superpowers/sdd/engine-reconciliation-spec.md). At round terminal (success
or fail) the engine calls `scheduler.on_round_terminal(proj, succeeded, now_s)`
and applies the returned LeaseDispositions, then releases still-active
reservations the round holds, BEFORE publishing the round.* terminal event.

Adapted from the engine-task-6 brief for the REAL model constructors: the
brief's zero-arg `LogisticRoundSuccessModel()` / `ExponentialDecoderServiceModel()`
do not exist (both take config-parameterized args, spec §6), so they are
constructed here from the guaranteed-success epoch's parameters. The brief's
`TraceBus(run_id=...)` likewise takes the shared SimClock. The brief's
assertions about trace event types, entity identity, and context release are
unchanged.
"""

from collections import defaultdict

from qsim.core.clock import SimClock
from qsim.core.trace import TraceBus
from qsim.core.invariants import InvariantChecker
from qsim.core.state import ModelBundle
from qsim.core.engine import Engine
from qsim.policies.s0 import S0Scheduler
from qsim.models.decay import NoDecayModel
from qsim.models.memory_access import ZeroCostMemoryAccessModel
from qsim.models.heralding import BernoulliHeraldingModel
from qsim.models.round_success import LogisticRoundSuccessModel
from qsim.models.decoder_service import ExponentialDecoderServiceModel

from tests.core.test_engine import make_config, make_workload, make_epoch


def _epoch_guaranteed_success():
    epoch = make_epoch()
    object.__setattr__(epoch, "heralding_p_per_path", defaultdict(lambda: 1.0))
    object.__setattr__(epoch, "heralded_fidelity_per_path", defaultdict(lambda: 1.0))
    object.__setattr__(epoch, "decoder_service_rate", 10000.0)
    object.__setattr__(epoch, "round_success_logistic_midpoint", 0.0)
    object.__setattr__(epoch, "round_success_logistic_slope", 50.0)
    object.__setattr__(epoch, "round_success_slack_penalty_per_s", 0.0)
    return epoch


def _guaranteed_success_models():
    # Model params mirror the guaranteed-success epoch: aggregate fidelity 1.0
    # against midpoint 0.0 / slope 50.0 gives p ≈ 1.0, so the keyed round_outcome
    # draw (u in [0,1)) is below p and the round succeeds.
    return ModelBundle(
        decay=NoDecayModel(),
        memory_access=ZeroCostMemoryAccessModel(),
        heralding=BernoulliHeraldingModel(),
        round_success=LogisticRoundSuccessModel(
            logistic_midpoint=0.0, logistic_slope=50.0, slack_penalty_per_s=0.0),
        decoder_service=ExponentialDecoderServiceModel(service_rate=10000.0),
    )


def test_round_completes_in_deadline_and_no_retry_is_scheduled():
    workload = make_workload()
    first_round = workload.next_arrival(0.0, 1)
    config = make_config(switch_capacity_c=2)
    config = config.__class__(**{**config.__dict__, "epoch": _epoch_guaranteed_success(),
                                 "deadline_slack_s": 1000.0})

    events = []
    clock = SimClock()
    trace = TraceBus(run_id="test-run", clock=clock)
    trace.subscribe(events.append)
    engine = Engine(config=config, scheduler=S0Scheduler(),
                    models=_guaranteed_success_models(),
                    workload=make_workload(), trace=trace, invariants=InvariantChecker())
    engine.run_to(first_round.arrival_time + config.reconfig_delay_s + 10.0)

    types = [e.event_type for e in events]
    assert "decoder.completed" in types
    outcome_types = {"round.completed_in_deadline", "round.completed_late", "round.failed"}
    assert len(outcome_types & set(types)) == 1
    assert "round.completed_in_deadline" in types
    completed = events[types.index("round.completed_in_deadline")]
    assert completed.entity_id == first_round.round_id
    assert first_round.round_id not in engine._round_contexts  # context released on terminal state


def test_scoring_draw_and_outcome_are_causally_chained_from_decoder_completion():
    # The round-outcome draw hangs off decoder.completed, and the terminal
    # round event hangs off (transitively) that draw — the §5 disposition
    # cascade runs in between but preserves the causal thread.
    workload = make_workload()
    first_round = workload.next_arrival(0.0, 1)
    config = make_config(switch_capacity_c=2)
    config = config.__class__(**{**config.__dict__, "epoch": _epoch_guaranteed_success(),
                                 "deadline_slack_s": 1000.0})

    events = []
    clock = SimClock()
    trace = TraceBus(run_id="test-run", clock=clock)
    trace.subscribe(events.append)
    engine = Engine(config=config, scheduler=S0Scheduler(),
                    models=_guaranteed_success_models(),
                    workload=make_workload(), trace=trace, invariants=InvariantChecker())
    engine.run_to(first_round.arrival_time + config.reconfig_delay_s + 10.0)

    by_id = {(e.run_id, e.seq): e for e in events}
    # First round's decoder.completed, round_outcome draw, and terminal outcome.
    completed = next(e for e in events
                     if e.event_type == "decoder.completed"
                     and e.payload.get("round_id") == first_round.round_id)
    draw = next(e for e in events
                if e.event_type == "draw.sampled"
                and e.payload.get("stream") == "round_outcome"
                and e.entity_id == first_round.round_id)
    outcome = events[[e.event_type for e in events].index("round.completed_in_deadline")]

    assert draw.causal_parent_id == (completed.run_id, completed.seq)
    # Walk the outcome's causal ancestry back to the round_outcome draw.
    node = outcome
    seen_draw = False
    while node.causal_parent_id is not None:
        parent = by_id.get(node.causal_parent_id)
        if parent is None:
            break
        if (parent.run_id, parent.seq) == (draw.run_id, draw.seq):
            seen_draw = True
            break
        node = parent
    assert seen_draw, "round terminal outcome must chain back to the round_outcome draw"
