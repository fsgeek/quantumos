"""Engine unit E2 — Task 5: decoder job lifecycle.

Adapted from the engine-task-5 brief per the AUTHORITATIVE reconciliation spec.
The brief's assertions about decoder trace events, ordering, causal parents,
and entity identity are UNCHANGED. Adaptations forced by the real frozen
interfaces: TraceBus takes a SimClock, and the ModelBundle is built via
test_engine.make_models() (real constructor signatures). Reconciliation spec
§3: decoder enqueue is triggered by the engine's own all-leases-heralded check
in _RoundContext, not by any scheduler herald callback.
"""

from collections import defaultdict

from tests.core.test_engine import make_config, make_workload, make_epoch, make_models
from qsim.core.clock import SimClock
from qsim.core.trace import TraceBus
from qsim.core.invariants import InvariantChecker
from qsim.core.engine import Engine
from qsim.policies.s0 import S0Scheduler


def _full_success_epoch():
    epoch = make_epoch()
    object.__setattr__(epoch, "heralding_p_per_path", defaultdict(lambda: 1.0))
    object.__setattr__(epoch, "heralded_fidelity_per_path", defaultdict(lambda: 0.95))
    object.__setattr__(epoch, "decoder_service_rate", 1000.0)
    return epoch


def test_decoder_job_enqueued_and_completes_after_all_leases_herald():
    first_round = make_workload().next_arrival(0.0, 1)
    config = make_config(switch_capacity_c=2)
    config = config.__class__(**{**config.__dict__, "epoch": _full_success_epoch()})

    events = []
    clock = SimClock()
    trace = TraceBus(run_id="test-run", clock=clock)
    trace.subscribe(events.append)
    engine = Engine(config=config, scheduler=S0Scheduler(), models=make_models(),
                    workload=make_workload(), trace=trace, invariants=InvariantChecker())
    engine.run_to(first_round.arrival_time + config.reconfig_delay_s + 10.0)

    types = [e.event_type for e in events]
    assert "decoder.enqueued" in types
    assert "decoder.completed" in types
    enqueued = events[types.index("decoder.enqueued")]
    completed = events[types.index("decoder.completed")]
    assert completed.sim_time > enqueued.sim_time
    assert completed.causal_parent_id is not None

    # The decoder job's entity id is stable across enqueue and completion (the
    # first enqueued job is the first to complete under the deterministic
    # service-time draw), so both events name the same decoder job.
    assert enqueued.entity_id == completed.entity_id
