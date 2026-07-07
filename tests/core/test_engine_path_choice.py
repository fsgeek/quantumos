"""Engine <-> PathChoice seam (B1): the injected strategy is invoked at the
exact pre-B1 call site — per lease, at arrival, in lease_ids order, BEFORE
admission, for every arrival kind (admitted, deferred, retry) — and the
engine builds the lease exactly as it did from _endpoints_for's return.
Bit-identity of the default is proven separately by the pinned golden hashes
in tests/determinism/test_b1_path_seam_preserves_trace.py."""
import math
from dataclasses import dataclass, field

from qsim.core.clock import SimClock
from qsim.core.engine import Engine
from qsim.core.invariants import InvariantChecker
from qsim.core.rng import draw_uniform
from qsim.core.state import ModelBundle
from qsim.core.trace import TraceBus
from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.models.decay import NoDecayModel
from qsim.models.decoder_service import ExponentialDecoderServiceModel
from qsim.models.heralding import BernoulliHeraldingModel
from qsim.models.memory_access import ZeroCostMemoryAccessModel
from qsim.models.round_success import LogisticRoundSuccessModel
from qsim.policies.path_choice import RoundRobinPathChoice
from qsim.policies.s0 import S0Scheduler
from qsim.workload.generator import WorkloadGenerator

RUN_SEED = 42
ARRIVAL_RATE_HZ = 1.0


def _epoch(**over):
    base = dict(
        epoch_id="path-choice-epoch",
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
    base.update(over)
    return CalibrationEpoch(**base)


def _config(**over):
    base = dict(
        run_seed=RUN_SEED, scheduler="S0", epoch=_epoch(),
        arrival_rate_hz=ARRIVAL_RATE_HZ, leases_per_round=1,
        deadline_slack_s=10.0, switch_capacity_c=2,
        reconfig_delay_s=0.0, max_sim_time_s=100.0,
    )
    base.update(over)
    return RunConfig(**base)


def _models():
    return ModelBundle(
        decay=NoDecayModel(),
        memory_access=ZeroCostMemoryAccessModel(),
        heralding=BernoulliHeraldingModel(),
        round_success=LogisticRoundSuccessModel(
            logistic_midpoint=0.5, logistic_slope=10.0, slack_penalty_per_s=0.0),
        decoder_service=ExponentialDecoderServiceModel(service_rate=1000.0),
    )


def _workload(config):
    return WorkloadGenerator(
        run_seed=config.run_seed, arrival_rate_hz=config.arrival_rate_hz,
        leases_per_round=config.leases_per_round,
        deadline_slack_s=config.deadline_slack_s)


def _make_engine(config, events, path_choice=None):
    clock = SimClock()
    trace = TraceBus(run_id="test-run", clock=clock)
    trace.subscribe(events.append)
    kwargs = {} if path_choice is None else {"path_choice": path_choice}
    return Engine(
        config=config, scheduler=S0Scheduler(), models=_models(),
        workload=_workload(config), trace=trace,
        invariants=InvariantChecker(), **kwargs,
    )


def _first_arrival(config):
    return _workload(config).next_arrival(0.0, 1)


@dataclass
class _Call:
    round_id: str
    lease_ordinal: int
    ports: tuple
    taken_path_ids: frozenset
    heralding_p_by_path: dict


@dataclass
class _RecordingChooser:
    """Spy that records every invocation, then delegates to the default
    round-robin so the engine's downstream machinery stays on real paths."""
    calls: list = field(default_factory=list)
    _inner: RoundRobinPathChoice = field(default_factory=RoundRobinPathChoice)

    def choose_endpoints(self, *, round_id, lease_ordinal, ports,
                         taken_path_ids, heralding_p_by_path):
        self.calls.append(_Call(
            round_id=round_id, lease_ordinal=lease_ordinal, ports=tuple(ports),
            taken_path_ids=frozenset(taken_path_ids),
            heralding_p_by_path=dict(heralding_p_by_path)))
        return self._inner.choose_endpoints(
            round_id=round_id, lease_ordinal=lease_ordinal, ports=ports,
            taken_path_ids=taken_path_ids, heralding_p_by_path=heralding_p_by_path)


class _ScriptedChooser:
    """Returns a fixed endpoint pair, raw order preserved."""

    def __init__(self, pair):
        self._pair = pair

    def choose_endpoints(self, *, round_id, lease_ordinal, ports,
                         taken_path_ids, heralding_p_by_path):
        return self._pair


def test_chooser_called_once_per_lease_in_lease_ids_order_with_accumulating_taken_set():
    path = make_path_id(PortId("M0", 0), PortId("M1", 0))
    config = _config(leases_per_round=2,
                     epoch=_epoch(heralding_p_per_path={path: 0.5},
                                  heralded_fidelity_per_path={path: 0.9}))
    first_round = _first_arrival(config)
    spy = _RecordingChooser()
    events = []
    engine = _make_engine(config, events, path_choice=spy)

    engine.run_to(first_round.arrival_time + 1e-9)

    assert len(spy.calls) == 2, "one chooser call per lease_id of the round"
    ports = tuple(PortId(f"M{i}", 0) for i in range(4))
    first, second = spy.calls
    assert first.round_id == first_round.round_id
    assert second.round_id == first_round.round_id
    assert [first.lease_ordinal, second.lease_ordinal] == [0, 1]
    assert first.ports == ports, "chooser receives the synthesized port universe"
    assert second.ports == ports
    assert first.taken_path_ids == frozenset()
    assert second.taken_path_ids == frozenset({make_path_id(ports[0], ports[1])}), (
        "the second lease's call must see the first lease's chosen PathId as taken")
    # The chooser sees the epoch's per-path table as a plain mapping.
    assert first.heralding_p_by_path == {path: 0.5}


def test_chooser_is_called_for_deferred_rounds_and_retry_arrivals():
    # Capacity 0: every admitted round churns (admit -> fail -> retry) and,
    # once its deadline lapses, its retries are DEFERRED. Both arrival kinds
    # must still advance the chooser — that is the pre-B1 counter discipline.
    config = _config(switch_capacity_c=0, deadline_slack_s=0.5)
    spy = _RecordingChooser()
    events = []
    engine = _make_engine(config, events, path_choice=spy)

    engine.run_to(10.0)

    types = [e.event_type for e in events]
    arrivals = [e for e in events if e.event_type == "round.arrived"]
    assert "round.deferred" in types, "the window must exercise deferred arrivals"
    assert any(e.payload["retry_ordinal"] > 0 for e in arrivals), (
        "the window must exercise retry arrivals")
    assert len(spy.calls) == len(arrivals) * config.leases_per_round, (
        "EVERY arrival — admitted, deferred, retry — invokes the chooser per lease")


def test_engine_without_path_choice_defaults_to_round_robin():
    config = _config()
    first_round = _first_arrival(config)
    events = []
    engine = _make_engine(config, events)

    assert isinstance(engine._path_choice, RoundRobinPathChoice)

    engine.run_to(first_round.arrival_time + 1e-9)
    acquired = [e for e in events if e.event_type == "reservation.acquired"]
    assert acquired[0].payload["path_id"] == [["M0", 0], ["M1", 0]], (
        "default engine reproduces the first round-robin pair")


def test_engine_builds_lease_from_the_choosers_return_exactly_as_before():
    # A scripted REVERSED pair (M1, M0): raw order must flow into the herald
    # draw key and the qubit handle's module (endpoint a), while the
    # reservation payload carries the canonical PathId — same as pre-B1.
    m0, m1 = PortId("M0", 0), PortId("M1", 0)
    config = _config()  # uncalibrated epoch: p=0, round stays live for inspection
    first_round = _first_arrival(config)
    events = []
    engine = _make_engine(config, events, path_choice=_ScriptedChooser((m1, m0)))

    engine.run_to(first_round.arrival_time + 1e-9)

    acquired = [e for e in events if e.event_type == "reservation.acquired"]
    assert acquired[0].payload["path_id"] == [["M0", 0], ["M1", 0]], (
        "reservation payload uses the canonical PathId")

    draws = [e for e in events if e.event_type == "draw.sampled"
             and e.payload["stream"] == "herald"]
    assert draws, "the herald attempt must have fired inside the window"
    key = draws[0].payload["key"]
    assert key[2] == (m1, m0), "herald draw key embeds endpoints in RAW order"
    assert draws[0].payload["uniform"] == draw_uniform(
        RUN_SEED, "herald", ("herald", first_round.round_id, (m1, m0), 1))

    ctx = engine._round_contexts[first_round.round_id]
    lease_id = first_round.lease_ids[0]
    assert ctx.leases[lease_id].endpoints == (m1, m0)
    assert ctx.leases[lease_id].path_id == make_path_id(m0, m1)
    assert ctx.qubit_handles[lease_id].module_id == "M1", (
        "qubit handle module comes from endpoint a of the RAW pair")
