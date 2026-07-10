"""Engine unit E1 — Task 1: DES loop, reconciled admission, arrival dispatch.

Written against the AUTHORITATIVE reconciliation spec
(.superpowers/sdd/engine-reconciliation-spec.md), which OVERRIDES the
engine-task-1 brief wherever they conflict. In particular the spec's
SEMANTIC DECISION: at capacity exhaustion S0 CHURNS (admit -> fail ->
retry), it does NOT defer. So the brief's
`test_first_arrival_deferred_and_dropped_when_capacity_is_zero`
(expecting round.deferred at capacity 0) is WRONG for the real S0 semantics
and is rewritten here as `test_capacity_zero_churns_admit_fail_retry`.
"""

import math
from dataclasses import dataclass

from qsim.core.clock import SimClock
from qsim.core.rng import draw_uniform
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
from qsim.entities import CalibrationEpoch, CoherenceClass

RUN_SEED = 42
ARRIVAL_RATE_HZ = 1.0
LEASES_PER_ROUND = 1
DEADLINE_SLACK_S = 10.0


# The flagged stand-in RunConfig that lived here (pre-experiments/config.py)
# is replaced by the real class per its own flag (executed 2026-07-10, after
# the herald_retry_interval_s field exposed the stand-in's drift risk).
from qsim.experiments.config import RunConfig  # noqa: E402


def make_epoch():
    return CalibrationEpoch(
        epoch_id="e0",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.0, CoherenceClass.MEMORY: 0.0},
        memory_access_channel_s=0.0,
        memory_access_wear_rate=0.0,
        heralding_p_per_path={},
        heralded_fidelity_per_path={},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=10.0,
        round_success_slack_penalty_per_s=0.0,
        decoder_service_rate=1000.0,
    )


def make_models():
    return ModelBundle(
        decay=NoDecayModel(),
        memory_access=ZeroCostMemoryAccessModel(),
        heralding=BernoulliHeraldingModel(),
        round_success=LogisticRoundSuccessModel(
            logistic_midpoint=0.5, logistic_slope=10.0, slack_penalty_per_s=0.0),
        decoder_service=ExponentialDecoderServiceModel(service_rate=1000.0),
    )


def make_workload():
    return WorkloadGenerator(run_seed=RUN_SEED, arrival_rate_hz=ARRIVAL_RATE_HZ,
                             leases_per_round=LEASES_PER_ROUND,
                             deadline_slack_s=DEADLINE_SLACK_S)


def make_config(switch_capacity_c):
    return RunConfig(
        run_seed=RUN_SEED, scheduler="S0", epoch=make_epoch(),
        arrival_rate_hz=ARRIVAL_RATE_HZ, leases_per_round=LEASES_PER_ROUND,
        deadline_slack_s=DEADLINE_SLACK_S, switch_capacity_c=switch_capacity_c,
        reconfig_delay_s=0.0, max_sim_time_s=100.0,
    )


def _make_engine(config, events):
    clock = SimClock()
    trace = TraceBus(run_id="test-run", clock=clock)
    trace.subscribe(events.append)
    return Engine(
        config=config, scheduler=S0Scheduler(),
        models=make_models(), workload=make_workload(),
        trace=trace, invariants=InvariantChecker(),
    )


def test_capacity_zero_churns_admit_fail_retry():
    # SEMANTIC DECISION (reconciliation spec): S0 does NOT defer on capacity
    # exhaustion. decide_admission only checks the deadline (now < deadline =>
    # ADMIT), path allocation then finds no capacity => round.failed => the
    # workload retries. So a fresh arrival at capacity 0 produces the churn
    # sequence round.arrived -> round.admitted -> round.failed -> round.arrived
    # (retry), never round.deferred.
    first_round = make_workload().next_arrival(0.0, 1)

    # Peek: retries re-inject after a keyed `retry`-stream interarrival delay
    # (the engine draws it deterministically), so we can bound the run window
    # to capture exactly the first retry re-arrival. Immediate (zero-delay)
    # retry would non-terminate under permanent contention; the positive
    # reinjection delay is what lets max_sim_time_s bound the churn.
    u_retry = draw_uniform(RUN_SEED, "retry", (first_round.round_id, 1))
    retry_delay = -math.log(1.0 - u_retry) / ARRIVAL_RATE_HZ
    window_end = first_round.arrival_time + retry_delay + 1e-6

    events = []
    engine = _make_engine(make_config(switch_capacity_c=0), events)
    engine.run_to(window_end)

    # Global first two events are this round's arrival and admission.
    assert events[0].event_type == "round.arrived"
    assert events[0].entity_id == first_round.round_id
    assert events[1].event_type == "round.admitted"
    # Emphatically NOT a deferral.
    assert all(e.event_type != "round.deferred" for e in events)

    # The round-1 lifecycle subsequence (robust to interleaved fresh arrivals
    # and draw.sampled events).
    r1 = [e for e in events
          if e.entity_id == first_round.round_id and e.event_type.startswith("round.")]
    types1 = [e.event_type for e in r1]
    assert types1[:4] == ["round.arrived", "round.admitted", "round.failed", "round.arrived"]

    # Causal chain: admitted <- arrived, failed <- admitted, retry-arrived <- failed.
    arrived, admitted, failed, retry_arrived = r1[0], r1[1], r1[2], r1[3]
    assert admitted.causal_parent_id == (arrived.run_id, arrived.seq)
    assert failed.causal_parent_id == (admitted.run_id, admitted.seq)
    assert retry_arrived.causal_parent_id == (failed.run_id, failed.seq)

    # The 4th round-1 event is the retry (retry_ordinal 1), same round identity.
    assert retry_arrived.payload.get("retry_ordinal") == 1
    assert retry_arrived.entity_id == first_round.round_id


def test_positive_capacity_admits_first_arrival():
    first_round = make_workload().next_arrival(0.0, 1)
    events = []
    engine = _make_engine(make_config(switch_capacity_c=2), events)
    engine.run_to(first_round.arrival_time + 1e-6)

    types = [e.event_type for e in events]
    assert types[0] == "round.arrived"
    assert types[1] == "round.admitted"
    assert events[0].entity_id == first_round.round_id
    assert events[1].causal_parent_id == (events[0].run_id, events[0].seq)
    assert "round.deferred" not in types
    assert "round.failed" not in types
