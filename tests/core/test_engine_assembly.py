"""Engine unit E2 — Task 4: round assembly (decay aging + memory-access cost).

Adapted from the engine-task-4 brief per the AUTHORITATIVE reconciliation spec.
The brief's numeric assertions (decay-composed fidelity, memory retention) are
UNCHANGED. Adaptations forced by the real frozen interfaces:
  * TraceBus takes a SimClock; the ModelBundle is built explicitly with the
    real constructor signatures.
  * M0 SyndromeRound carries NO qubit_ids (the frozen WorkloadGenerator emits
    an empty list), so the engine synthesizes one memory-role QubitHandle per
    LEASE, keyed by lease_id. The brief's `ctx.qubit_handles[qubit_ids[0]]`
    lookup is therefore keyed by `lease_ids[0]` instead — the same handle, a
    different (necessarily lease-derived) key.
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
from qsim.models.memory_access import LinearMemoryAccessModel
from qsim.models.heralding import BernoulliHeraldingModel
from qsim.models.round_success import LogisticRoundSuccessModel
from qsim.models.decoder_service import ExponentialDecoderServiceModel


def test_assemble_round_composes_decay_and_memory_retention():
    first_round = make_workload().next_arrival(0.0, 1)
    epoch = make_epoch()
    object.__setattr__(epoch, "heralding_p_per_path", defaultdict(lambda: 1.0))
    object.__setattr__(epoch, "heralded_fidelity_per_path", defaultdict(lambda: 0.8))
    object.__setattr__(epoch, "memory_access_channel_s", 0.01)
    object.__setattr__(epoch, "memory_access_wear_rate", 0.1)
    config = make_config(switch_capacity_c=2)
    config = config.__class__(**{**config.__dict__, "epoch": epoch})

    models = ModelBundle(
        decay=NoDecayModel(), memory_access=LinearMemoryAccessModel(),
        heralding=BernoulliHeraldingModel(),
        round_success=LogisticRoundSuccessModel(
            logistic_midpoint=0.5, logistic_slope=10.0, slack_penalty_per_s=0.0),
        decoder_service=ExponentialDecoderServiceModel(service_rate=1000.0),
    )

    clock = SimClock()
    trace = TraceBus(run_id="test-run", clock=clock)
    engine = Engine(config=config, scheduler=S0Scheduler(), models=models,
                    workload=make_workload(), trace=trace, invariants=InvariantChecker())
    engine.run_to(first_round.arrival_time + config.reconfig_delay_s + 1e-6)

    ctx = engine._round_contexts[first_round.round_id]
    lease = ctx.leases[first_round.lease_ids[0]]
    qubit = ctx.qubit_handles[first_round.lease_ids[0]]

    lease_fidelities, memory_retentions = engine._assemble_round(ctx.round)

    decay_factor = engine._state.models.decay.retention(
        engine._state.now - lease.heralded_at, qubit.coherence_class, config.epoch,
    )
    expected_fidelity = lease.fidelity_at_herald * decay_factor
    access_cost = engine._state.models.memory_access.access_cost(qubit, config.epoch)
    expected_retention = decay_factor * access_cost.retention_factor

    assert lease_fidelities == [expected_fidelity]
    assert memory_retentions == [expected_retention]
