"""Single-run driver for the M0 simulator (design spec §4, §12).

`run(config, out_dir)` builds the DES `Engine`, wires the model surfaces and
scheduler named by the config, subscribes the run-directory writer to the
`TraceBus` so the FULL trace is captured to events.jsonl, stamps a header
(with git provenance and the §R5 no-silent-omission filtering declaration),
executes to `max_sim_time_s` or event exhaustion, and returns the run
directory path.

Wiring notes (reconciled against the BUILT collaborators, which differ from
the placeholder signatures sketched in the frozen contract):

* `TraceBus.__init__(run_id, clock)` — the bus stamps every event's sim_time
  from the SimClock it is constructed with, and `Engine` adopts THAT clock
  (`trace._clock`). So the driver constructs one `SimClock`, hands it to the
  bus, and both engine and bus share it. (The contract's bare `TraceBus()`
  was a placeholder.)
* Two model surfaces are epoch-parameterized: `LogisticRoundSuccessModel`
  takes the epoch's logistic midpoint/slope/slack-penalty, and
  `ExponentialDecoderServiceModel` takes the epoch's decoder service rate.
* `S1Scheduler(PregenMixin, AdmissionMixin, S0Scheduler)` is constructed
  through its cooperative-MRO __init__: `theta_admit` and the five model
  surfaces feed `AdmissionMixin` (§8.1); `low_water_mark`/`tracked_keys`
  feed `PregenMixin` (§8.2). `tracked_keys` is empty in M0: the engine
  synthesizes its own fabric paths and never deposits to the pregen pool, so
  a non-empty tracked-key set would make `next_lease_request` emit unbounded
  POOL_REPLENISH requests for perpetually-empty pools (the engine's
  acquisition drain loop would not terminate). Pregen is therefore inert in
  M0 by construction — flagged; wiring the pool deposit/withdraw path is
  future work.
"""
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from qsim.core.clock import SimClock
from qsim.core.engine import Engine
from qsim.core.invariants import InvariantChecker
from qsim.core.state import ModelBundle
from qsim.core.trace import TraceBus
from qsim.experiments.config import RunConfig
from qsim.models.decay import ExponentialDecayModel, NoDecayModel
from qsim.models.decoder_service import ExponentialDecoderServiceModel
from qsim.models.heralding import BernoulliHeraldingModel
from qsim.models.memory_access import LinearMemoryAccessModel, ZeroCostMemoryAccessModel
from qsim.models.round_success import LogisticRoundSuccessModel
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.steady_state import compute_steady_state
from qsim.policies.s0 import S0Scheduler
from qsim.policies.s1 import S1Scheduler
from qsim.workload.generator import WorkloadGenerator

# §R5 reconciliation: the no-silent-omission declaration. The WorkloadGenerator
# draws interarrival times on the keyed `workload` stream (spec §9's exponential
# process, §10's CRN keying), but its FROZEN signature carries no TraceBus, so
# those draws are the one class of stochastic draw NOT recorded in events.jsonl.
# They are fully regenerable from `run_seed` via `draw_uniform(run_seed,
# "workload", ("arrival", arrival_index))`, so this is a declared, recoverable
# omission — not a silent one. Stamped into header.json's `filtering` block.
_WORKLOAD_DRAW_FILTERING = {
    "enabled": True,
    "declared_omissions": [
        {
            "kind": "workload_interarrival_draws",
            "stream": "workload",
            "reason": (
                "WorkloadGenerator's frozen __init__ signature has no TraceBus, "
                "so its §9 exponential interarrival draws are not emitted to "
                "events.jsonl."
            ),
            "recovery": (
                "Regenerable from run_seed via draw_uniform(run_seed, 'workload', "
                "('arrival', arrival_index)) for arrival_index = 1, 2, ..."
            ),
        }
    ],
    # Discharges the progress-ledger DEFERRED FLAG (b): the p=0-on-uncalibrated-
    # path heralding guard is declared here rather than left a silent omission.
    "model_guards": [
        {
            "kind": "uncalibrated_path_heralding",
            "stream": "heralding",
            "reason": (
                "core/engine.py synthesizes fabric PathIds (_synthesize_ports/"
                "_endpoints_for) that a CalibrationEpoch need not enumerate. Both "
                "the engine's §5 heralding attempt and the §8.1 S1 admission "
                "projection may look up such a path in the epoch's per-path "
                "heralding tables."
            ),
            "guard": (
                "heralding.success_probability / heralded_fidelity return 0.0 for "
                "any path absent from the epoch (never heralds, zero projected "
                "fidelity), mirroring core/engine.py's own documented p=0.0 "
                "KeyError guard so engine physics and admission projection agree."
            ),
        }
    ],
}


class _UncalibratedPathGuardedHeralding:
    """Wraps a HeraldingModel so lookups on engine-synthesized paths the
    calibration epoch does not enumerate return 0.0 instead of raising KeyError.

    `core/engine.py._on_herald_attempt` already applies exactly this p=0.0
    guard around its own `success_probability` lookup, but the §8.1 admission
    projection in `policies/admission.py` reads `heralded_fidelity` un-guarded,
    so an S1 run crashes on the first arrival whose synthesized path is not in
    the epoch's per-path tables (the progress-ledger DEFERRED FLAG (b) gap).
    Wiring the guard at the single point where the ModelBundle is built — and
    shared by BOTH the engine and S1 admission — makes the guard uniform: a
    path the engine can never herald (p=0) also projects zero admission
    fidelity, so admission defers rather than the run aborting. The guard is
    declared in header.json's filtering block, so it is visible, not silent.
    """

    def __init__(self, inner) -> None:
        self._inner = inner

    def success_probability(self, path, epoch) -> float:
        try:
            return self._inner.success_probability(path, epoch)
        except KeyError:
            return 0.0

    def heralded_fidelity(self, path, epoch) -> float:
        try:
            return self._inner.heralded_fidelity(path, epoch)
        except KeyError:
            return 0.0


def build_model_bundle(config: RunConfig) -> ModelBundle:
    """Wires the §6/§15 control flags to concrete model-surface implementations.

    `decay_control_enabled == False` selects the `NoDecayModel` negative
    control (retention ≡ 1); `memory_cost_control_enabled == False` selects
    the `ZeroCostMemoryAccessModel` control (free reads). The logistic
    round-success and exponential decoder-service surfaces are parameterized
    from the config's calibration epoch.
    """
    epoch = config.epoch
    decay = ExponentialDecayModel() if config.decay_control_enabled else NoDecayModel()
    memory_access = (
        LinearMemoryAccessModel()
        if config.memory_cost_control_enabled
        else ZeroCostMemoryAccessModel()
    )
    return ModelBundle(
        decay=decay,
        memory_access=memory_access,
        heralding=_UncalibratedPathGuardedHeralding(BernoulliHeraldingModel()),
        round_success=LogisticRoundSuccessModel(
            logistic_midpoint=epoch.round_success_logistic_midpoint,
            logistic_slope=epoch.round_success_logistic_slope,
            slack_penalty_per_s=epoch.round_success_slack_penalty_per_s,
        ),
        decoder_service=ExponentialDecoderServiceModel(
            service_rate=epoch.decoder_service_rate
        ),
    )


def build_scheduler(config: RunConfig, models: ModelBundle | None = None):
    """Constructs the Scheduler named by config.scheduler (§8's ablation ladder).

    S0 is the parameter-free competent baseline. S1 composes AdmissionMixin
    (§8.1) and PregenMixin (§8.2) over S0 via cooperative MRO, so its __init__
    consumes `theta_admit`, the five model surfaces, and the pregen
    low-water-mark/tracked-keys as keyword arguments threaded down the chain.
    The model surfaces are shared with the engine's ModelBundle so admission
    projects against the same physics the engine simulates.
    """
    if config.scheduler == "S0":
        return S0Scheduler()
    if config.scheduler == "S1":
        bundle = models if models is not None else build_model_bundle(config)
        return S1Scheduler(
            theta_admit=config.admission_theta,
            decay_model=bundle.decay,
            heralding_model=bundle.heralding,
            memory_access_model=bundle.memory_access,
            round_success_model=bundle.round_success,
            decoder_service_model=bundle.decoder_service,
            low_water_mark=config.pregen_low_water_mark,
            tracked_keys=(),
        )
    raise ValueError(f"unknown scheduler tag: {config.scheduler!r}")


def git_sha() -> str:
    """Best-effort current commit SHA for header.json provenance (§12)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def run(config: RunConfig, out_dir: Path) -> Path:
    """Builds the engine, wires models/policies/workload/observe per config,
    executes to max_sim_time_s or exhaustion, returns the run directory path.

    Single-run driver only for M0 (grid-sweep is M1)."""
    run_id = str(uuid.uuid4())

    clock = SimClock()
    trace = TraceBus(run_id=run_id, clock=clock)
    invariants = InvariantChecker()

    run_dir_writer = RunDirWriter(root=Path(out_dir), run_id=run_id)
    # Subscribe the writer BEFORE the engine runs so the FULL trace is captured
    # to events.jsonl — every published transition, not a post-hoc aggregate.
    trace.subscribe(run_dir_writer.append_event)

    models = build_model_bundle(config)
    scheduler = build_scheduler(config, models)
    workload = WorkloadGenerator(
        run_seed=config.run_seed,
        arrival_rate_hz=config.arrival_rate_hz,
        leases_per_round=config.leases_per_round,
        deadline_slack_s=config.deadline_slack_s,
    )

    engine = Engine(
        config=config,
        scheduler=scheduler,
        models=models,
        workload=workload,
        trace=trace,
        invariants=invariants,
    )

    run_dir_writer.write_header(
        config=config,
        run_seed=config.run_seed,
        git_sha=git_sha(),
        filtering_declared=_WORKLOAD_DRAW_FILTERING,
    )

    engine.run_to(config.max_sim_time_s)

    # Steady-state / convergence gate (spec §13). Computed AFTER the run from
    # the captured trace, then stamped into the already-written header so a
    # non-converged (divergent-queue) run is flagged, not silently trusted.
    # Localized additive patch of header.json (does not touch RunDirWriter).
    _stamp_steady_state(run_dir_writer.header_path, run_dir_writer.events_path)

    return run_dir_writer.run_dir


def _stamp_steady_state(header_path: Path, events_path: Path) -> None:
    """Add a `steady_state` block to an already-written header.json (§13)."""
    import json

    verdict = compute_steady_state(events_path)
    header = json.loads(header_path.read_text())
    header["steady_state"] = verdict.as_dict()
    header_path.write_text(json.dumps(header, indent=2, sort_keys=True))
