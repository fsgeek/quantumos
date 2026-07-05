"""Engine unit E4 — Task 8: end-to-end integration test.

Pure verification of the fully wired `Engine` (units E1–E3) driving a REAL
`S0Scheduler` and the REAL v1 models through `run_to()`. No new engine code.

Written against the AUTHORITATIVE reconciliation spec
(.superpowers/sdd/engine-reconciliation-spec.md), which OVERRIDES the
engine-task-8 brief wherever they conflict.

Two mechanical adaptations of the brief's scaffolding were required for the
test to run against the REAL code (neither changes what is being asserted):

  * The brief constructs `LogisticRoundSuccessModel()` /
    `ExponentialDecoderServiceModel()` with no arguments; the real v1 models
    take config-parameterized constructor args (spec §6), so they are built
    from the guaranteed-success epoch's parameters (same as E3's
    tests/core/test_engine_outcome.py).
  * The brief's `TraceBus(run_id=...)` omits the shared `SimClock`; the real
    TraceBus signature is `(run_id, clock)`, and the Engine adopts that clock,
    so a clock is passed here.

The SUBSTANTIVE assertion — the causal chain from the round's terminal event
back to its arrival — is asserted against the REAL built engine's causal
threading. See `expected_order` below for why it differs from the brief's
naive linear list (the difference is intended, separately-tested engine
behavior, not an engine bug).
"""

from collections import defaultdict

from tests.core.test_engine import make_config, make_workload, make_epoch
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


class CountingInvariantChecker(InvariantChecker):
    """Subclassed ONLY to count observe() calls — never to fake its logic; it
    still runs the real InvariantChecker.observe after counting."""

    def __init__(self):
        super().__init__()
        self.observed = 0

    def observe(self, event, state):
        self.observed += 1
        super().observe(event, state)


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
    # against midpoint 0.0 / slope 50.0 gives p ≈ 1.0, so every keyed
    # round_outcome draw (u in [0,1)) falls below p and the round succeeds.
    return ModelBundle(
        decay=NoDecayModel(),
        memory_access=ZeroCostMemoryAccessModel(),
        heralding=BernoulliHeraldingModel(),
        round_success=LogisticRoundSuccessModel(
            logistic_midpoint=0.0, logistic_slope=50.0, slack_penalty_per_s=0.0),
        decoder_service=ExponentialDecoderServiceModel(service_rate=10000.0),
    )


def test_single_round_single_path_full_causal_chain_with_fixed_seed():
    run_seed = 7
    workload = make_workload()
    first_round = workload.next_arrival(0.0, 1)
    config = make_config(switch_capacity_c=1)
    config = config.__class__(**{**config.__dict__, "run_seed": run_seed,
                                 "epoch": _epoch_guaranteed_success(),
                                 "deadline_slack_s": 1000.0, "reconfig_delay_s": 0.25})

    events = []
    clock = SimClock()
    trace = TraceBus(run_id="integration-run", clock=clock)
    trace.subscribe(events.append)
    invariants = CountingInvariantChecker()
    engine = Engine(config=config, scheduler=S0Scheduler(),
                    models=_guaranteed_success_models(),
                    workload=make_workload(), trace=trace, invariants=invariants)

    engine.run_to(first_round.arrival_time + config.reconfig_delay_s + 5.0)

    # The causal thread through the REAL built engine (units E1–E3). This
    # differs from the engine-task-8 brief's naive linear list in three places,
    # all of which are intended, separately-tested engine behavior — NOT bugs:
    #
    #   * reservation.released is NOT on this chain. It branches off
    #     lease.heralded as a SIBLING of decoder.enqueued (both are caused by
    #     the herald: the herald both frees the path and readies the round for
    #     decoding). The thread to completion follows decoder.enqueued.
    #   * the decode-stream draw.sampled is NOT on this chain. It is a SIBLING
    #     of decoder.completed off decoder.enqueued (enqueue causes both the
    #     service-time draw and, via the scheduled completion event, the
    #     completion). The thread follows decoder.completed.
    #   * lease.consumed IS on this chain, between the round_outcome draw and
    #     the terminal event: a SUCCESSFUL round USES (consumes) its held lease,
    #     and consumption runs BEFORE the round.* terminal event so the terminal
    #     chains off it (reconciliation spec §4). Cancellation is reserved for
    #     failed/unused leases; a successful round consumes, it does not cancel.
    expected_order = [
        "round.arrived", "round.admitted", "reservation.acquired", "reservation.configuring",
        "reservation.active", "draw.sampled", "lease.heralded",
        "decoder.enqueued", "decoder.completed", "draw.sampled", "lease.consumed",
        "round.completed_in_deadline",
    ]
    # Filter to this round's own causal thread by walking parent links (entity_id
    # differs per stage: round / path / lease / job), starting from the first
    # round's terminal event and following causal_parent_id back to its arrival.
    by_id = {(e.run_id, e.seq): e for e in events}
    chain = []
    cursor = events[[e.event_type for e in events].index("round.completed_in_deadline")]
    while cursor is not None:
        chain.append(cursor.event_type)
        parent = cursor.causal_parent_id
        cursor = by_id.get(parent) if parent is not None else None
    chain.reverse()
    assert chain == expected_order

    assert invariants.observed == len(events)

    ctx_gone = first_round.round_id not in engine._round_contexts
    assert ctx_gone
