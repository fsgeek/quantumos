# QuantumOS Simulator M0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the M0 acceptance milestone of the QuantumOS simulator (design spec
`docs/superpowers/specs/2026-07-04-quantum-os-simulator-design.md`): a bespoke
discrete-event simulator core, the entity model, the five v1 physics-model
surfaces with their required controls, both scheduler policies (S0, S1), the
closed-loop workload generator, full trace-based observability, and the
single-run experiment driver — with determinism tests and decoupled-limit
checks proving the trace contract before M1 adds the ablation ladder,
checkpointing, and metamorphic checks.

**Architecture:** Single top-level package `qsim/`, seven sub-packages with
strictly downward-only dependencies: `experiments/ → workload/ → policies/ →
models/ → entities/ → core/`, plus `observe/` (depended on by `experiments/`
only, for run-directory writing). `core/` owns the DES engine (event heap,
keyed RNG, trace bus, invariants, and the `Engine` run loop that implements
the design spec's §4 data flow end to end). Entities are inert dataclasses
with lifecycle-transition methods and no embedded decisions. Models are
Protocols with one analytic v1 implementation each. Policies compose S0 with
two mixins (admission, pre-generation) via cooperative multiple inheritance
so S1 is literally `S0 + AdmissionMixin + PregenMixin`, zero new code.

**Tech Stack:** Python ≥3.14 (repository toolchain floor, not a design
requirement), stdlib only for M0 — `dataclasses`, `enum`, `typing.Protocol`,
`heapq`, `hashlib`, `json`, `pathlib`. No simulation framework dependency
(design spec §3.5). Test runner: `pytest`.

## Global Constraints

The following apply to every task below; they are not repeated per-task.

- **Toolchain floor:** Python ≥3.14. No 3.14-only language features are used
  or required (design spec §3.6).
- **No new external dependencies** beyond `pytest` for the test runner. All
  production code uses only the Python standard library.
- **Package root:** every source file lives under `qsim/`, imported as
  `qsim.<subpackage>.<module>` (e.g. `qsim.core.rng`, `qsim.entities.lease`).
  Tests live under `tests/<subpackage>/test_*.py` (no `qsim.` prefix on the
  test tree). A single root `conftest.py` (created in core/ Task 1) ensures
  the repo root is importable regardless of pytest invocation style.
- **Randomness:** every stochastic draw goes through `qsim.core.rng.draw_uniform`,
  which hashes `(run_seed, stream, key)` via SHA-256 — never Python's builtin
  `hash()` (design spec §10). Semantic keys (round ids, job ids, attempt
  numbers) are assigned from arrival index / retry ordinal, never from
  event-heap or call order.
- **Observability:** every entity state transition publishes to the
  `TraceBus` before continuing (design spec §12); the trace is authoritative
  — metrics in `observe/views.py` are post-hoc computations over
  `events.jsonl`, never a substitute source of truth.
- **Fail-stop invariants:** `core/invariants.py`'s `InvariantChecker` proves
  bookkeeping legality only (design spec §14) — it is not evidence of
  physics correctness. Passing invariants must never be cited as validating
  a result.
- **Primary metrics are offered-work-normalized** (design spec §11): goodput
  and the logical-error proxy divide by *offered* rounds, never by admitted
  or attempted, so an admission controller cannot trivially improve them by
  rejecting work.
- **TDD throughout:** every task writes a failing test first, confirms the
  specific failure reason, then writes the minimal implementation, confirms
  the test passes, then commits. No task skips a step.

## Shared Interface Contract (frozen for all tasks below)

Every package section was drafted against this exact set of names, fields,
and signatures. Where the design spec gives a signature verbatim (all of
§6's model Protocols), it is reproduced unchanged below; everything else is
a systems/implementation decision made to unblock this plan — treat it as
binding, not a suggestion, when a task's code references a type or method
by name.

```python
# ============================================================
# core/rng.py
# ============================================================
def draw_uniform(run_seed: int, stream: str, key: tuple) -> float:
    """Deterministic uniform in [0,1). Seeds from SHA-256 over a canonical
    serialization of (run_seed, stream, key). Never uses builtin hash()."""

@dataclass(frozen=True)
class Draw:
    u: float  # the keyed uniform sample, already drawn by the engine

# ============================================================
# core/clock.py
# ============================================================
class SimClock:
    def now(self) -> float: ...
    def advance_to(self, t: float) -> None: ...  # raises if t < now() (monotonicity)

# ============================================================
# core/event_heap.py
# ============================================================
@dataclass(order=True)
class HeapEntry:
    time: float
    seq: int
    payload: object = field(compare=False)

class EventHeap:
    def push(self, time: float, payload: object) -> int: ...  # returns assigned seq
    def pop(self) -> HeapEntry | None: ...
    def __len__(self) -> int: ...

# ============================================================
# core/trace.py
# ============================================================
EventId = tuple[str, int]  # (run_id, seq)

@dataclass(frozen=True)
class Event:
    run_id: str
    seq: int
    sim_time: float
    event_type: str            # see EVENT_TYPES below
    entity_id: str
    causal_parent_id: EventId | None
    payload: dict

EVENT_TYPES = [
    # lease lifecycle (§5)
    "lease.requested", "lease.heralded", "lease.consumed", "lease.expired", "lease.cancelled",
    "lease.pool_returned",  # pregen return path, accounted separately per §5/§11
    # round lifecycle (§5, §11)
    "round.arrived", "round.admitted", "round.deferred", "round.dropped",
    "round.completed_in_deadline", "round.completed_late", "round.failed", "round.retried",
    # switch reservation lifecycle (§7)
    "reservation.acquired", "reservation.configuring", "reservation.active", "reservation.released",
    # decoder job lifecycle (§5)
    "decoder.enqueued", "decoder.dequeued", "decoder.completed", "decoder.cancelled",
    # randomness (§10) — every draw is itself a trace event
    "draw.sampled",  # payload: {stream, key, uniform}
]

class TraceBus:
    def publish(self, event_type: str, entity_id: str,
                causal_parent_id: EventId | None, payload: dict) -> EventId: ...
    def subscribe(self, fn: Callable[[Event], None]) -> None: ...

# ============================================================
# core/invariants.py
# ============================================================
class InvariantViolation(Exception):
    """Raised with the causal chain of the offending event (§14)."""

class InvariantChecker:
    def observe(self, event: Event, state: "EngineState") -> None:
        """Called after every TraceBus.publish. Raises InvariantViolation on:
        event-time non-monotonicity, illegal lease transition, double consumption,
        fidelity outside [0,1], conservation violation (lease/queue/work-accounting
        imbalance), or a SwitchPathReservation outliving its holding attempt/round."""

# ============================================================
# core/state.py — owned by core/, imported by policies/ (downward-only, §4)
# ============================================================
@dataclass(frozen=True)
class ModelBundle:
    decay: "DecayModel"
    memory_access: "MemoryAccessModel"
    heralding: "HeraldingModel"
    round_success: "RoundSuccessModel"
    decoder_service: "DecoderServiceModel"

@dataclass
class EngineState:
    """Read-only view passed into Scheduler calls. The engine constructs and
    mutates the underlying state; policies must not mutate it directly."""
    now: float
    epoch: "CalibrationEpoch"
    models: ModelBundle
    decoder_backlog: int
    active_reservations: dict["PathId", "SwitchPathReservation"]
    pool: dict[tuple["PathId", "CoherenceClass"], list["EntanglementLease"]]  # pregen (§8.2)
    switch_capacity_c: int
    hold_until_consumption: bool

# ============================================================
# entities/*.py
# ============================================================
@dataclass(frozen=True)
class PortId:
    module_id: str
    port_index: int

@dataclass
class Module:
    module_id: str
    ports: tuple[PortId, ...]

class CoherenceClass(Enum):
    MESSENGER = "messenger"
    MEMORY = "memory"

# PathId is the pair of endpoints a crossbar path connects, canonically ordered
# so (a,b) and (b,a) hash identically — ties directly to §7's endpoint model.
PathId = tuple[PortId, PortId]
def make_path_id(a: PortId, b: PortId) -> PathId:
    return tuple(sorted((a, b), key=lambda p: (p.module_id, p.port_index)))

@dataclass
class QubitHandle:
    qubit_id: str
    module_id: str
    coherence_class: CoherenceClass
    calibration_epoch: "CalibrationEpoch"
    state_held_since: float | None = None
    fidelity_at_hold_start: float | None = None
    access_count: int = 0  # drives MemoryAccessModel's linear wear (§6.2)

class LeaseState(Enum):
    REQUESTED = "requested"
    HERALDED = "heralded"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

@dataclass
class EntanglementLease:
    lease_id: str
    endpoints: tuple[PortId, PortId]
    path_id: PathId
    created_at: float
    freshness_bound_s: float
    fidelity_at_herald: float | None = None
    heralded_at: float | None = None
    state: LeaseState = LeaseState.REQUESTED
    retry_count: int = 0

class RoundState(Enum):
    PENDING = "pending"
    ADMITTED = "admitted"
    DEFERRED = "deferred"
    DROPPED = "dropped"
    COMPLETED_IN_DEADLINE = "completed_in_deadline"
    COMPLETED_LATE = "completed_late"
    FAILED = "failed"

@dataclass
class SyndromeRound:
    round_id: str
    lease_ids: list[str]
    qubit_ids: list[str]
    arrival_time: float
    deadline: float
    retry_ordinal: int = 0
    state: RoundState = RoundState.PENDING

@dataclass
class DecoderJob:
    job_id: str
    round_id: str
    priority: int
    enqueue_time: float
    dequeue_time: float | None = None
    completion_time: float | None = None

class ReservationState(Enum):
    ACQUIRED = "acquired"
    CONFIGURING = "configuring"
    ACTIVE = "active"
    RELEASED = "released"

@dataclass
class SwitchPathReservation:
    path_id: PathId
    holder_id: str  # round_id or lease_id
    acquired_at: float
    released_at: float | None = None
    state: ReservationState = ReservationState.ACQUIRED

@dataclass(frozen=True)
class CalibrationEpoch:
    epoch_id: str
    decay_rate_per_class: dict[CoherenceClass, float]        # DecayModel: retention = exp(-rate*age)
    memory_access_channel_s: float                            # MemoryAccessModel fixed duration/access
    memory_access_wear_rate: float                             # MemoryAccessModel: retention loss/access
    heralding_p_per_path: dict[PathId, float]                   # HeraldingModel
    heralded_fidelity_per_path: dict[PathId, float]             # HeraldingModel
    round_success_logistic_midpoint: float                      # RoundSuccessModel
    round_success_logistic_slope: float                         # RoundSuccessModel
    round_success_slack_penalty_per_s: float                    # RoundSuccessModel
    decoder_service_rate: float                                  # DecoderServiceModel (exponential rate)

@dataclass
class PauliFrameToken:
    token_id: str
    created_at: float

# ============================================================
# models/protocols.py — VERBATIM from spec §6, plus the §8.1 addendum
# ============================================================
@dataclass(frozen=True)
class AccessCost:
    electron_channel_s: float
    retention_factor: float

class DecayModel(Protocol):
    def retention(self, age_s: float, coherence: CoherenceClass,
                  epoch: CalibrationEpoch) -> float: ...

class MemoryAccessModel(Protocol):
    def access_cost(self, qubit: QubitHandle, epoch: CalibrationEpoch) -> AccessCost: ...

class HeraldingModel(Protocol):
    def success_probability(self, path: PathId, epoch: CalibrationEpoch) -> float: ...
    def heralded_fidelity(self, path: PathId, epoch: CalibrationEpoch) -> float: ...

class RoundSuccessModel(Protocol):
    def success_probability(self, lease_fidelities: Sequence[float],
                            memory_retentions: Sequence[float],
                            decoder_latency_s: float,
                            deadline_slack_s: float) -> float: ...

class DecoderServiceModel(Protocol):
    def service_time_s(self, job: DecoderJob, backlog: int, draw: Draw) -> float: ...
    def expected_service_time_s(self, backlog: int, epoch: CalibrationEpoch) -> float: ...

# v1 implementations (one file per surface, matching spec §6 table):
#   models/decay.py:            ExponentialDecayModel, NoDecayModel (control: retention ≡ 1)
#   models/memory_access.py:    LinearMemoryAccessModel, ZeroCostMemoryAccessModel (control: free reads)
#   models/heralding.py:        BernoulliHeraldingModel
#   models/round_success.py:    LogisticRoundSuccessModel
#   models/decoder_service.py:  ExponentialDecoderServiceModel

# ============================================================
# workload/generator.py
# ============================================================
class WorkloadGenerator:
    def __init__(self, run_seed: int, arrival_rate_hz: float,
                 leases_per_round: int, deadline_slack_s: float): ...
        # arrivals: Poisson process (exponential interarrival), `workload`-stream keyed draws (§9,§10)

    def next_arrival(self, after_time: float, arrival_index: int) -> SyndromeRound:
        """arrival_index is the semantic key for the interarrival draw — never
        drawn from event-heap order (§10)."""

    def on_outcome(self, round: SyndromeRound, succeeded: bool) -> SyndromeRound | None:
        """Returns a retry SyndromeRound (retry_ordinal + 1, same round identity
        for lineage) on failure per policy, or None if no retry is due."""

# ============================================================
# observe/run_dir.py, work_accounting.py, views.py
# ============================================================
@dataclass
class WorkAccounting:
    offered: int = 0
    retries: int = 0
    admitted: int = 0
    deferred: int = 0
    dropped: int = 0
    completed_in_deadline: int = 0
    completed_late: int = 0
    failed: int = 0
    pool_returned: int = 0  # accounted separately per §5, never folded into "consumed"

    def attempts(self) -> int: ...       # offered + retries
    def goodput(self) -> float: ...      # completed_in_deadline / offered

class RunDirWriter:
    def __init__(self, root: Path, run_id: str): ...
    def write_header(self, config: "RunConfig", run_seed: int, git_sha: str,
                     filtering_declared: dict | None = None) -> None: ...
    def append_event(self, event: Event) -> None: ...  # appends to events.jsonl

# observe/views.py — pure functions over a run directory's events.jsonl (§12):
def goodput(events_path: Path) -> float: ...
def freshness_at_consumption(events_path: Path) -> list[float]: ...
def decoder_backlog_series(events_path: Path) -> list[tuple[float, int]]: ...
def deadline_compliance(events_path: Path) -> dict[str, float]: ...
def resource_utilization(events_path: Path) -> dict[str, float]: ...
def logical_error_proxy(events_path: Path) -> float: ...
def shared_key_fraction(events_path_a: Path, events_path_b: Path,
                        window_s: float) -> list[tuple[float, float]]: ...  # §10 paired-comparison view

# ============================================================
# experiments/config.py, run.py
# ============================================================
@dataclass(frozen=True)
class RunConfig:
    run_seed: int
    scheduler: str  # "S0" | "S1"
    epoch: CalibrationEpoch
    arrival_rate_hz: float
    leases_per_round: int
    deadline_slack_s: float
    switch_capacity_c: int
    reconfig_delay_s: float
    max_sim_time_s: float
    hold_until_consumption: bool = False
    admission_theta: float | None = None       # required if scheduler == "S1" (§8.1)
    pregen_low_water_mark: int | None = None   # required if scheduler == "S1" (§8.2)
    decay_control_enabled: bool = True         # False => NoDecayModel (§6, §15)
    memory_cost_control_enabled: bool = True   # False => ZeroCostMemoryAccessModel (§6, §15)

def run(config: RunConfig, out_dir: Path) -> Path:
    """Builds the engine (core.engine.Engine), wires models/policies/workload/
    observe per config, executes to max_sim_time_s or exhaustion, returns the
    run directory path. Single-run driver only for M0 (grid-sweep is M1)."""

# ============================================================
# core/engine.py
# ============================================================
class Engine:
    def __init__(self, config: "RunConfig", scheduler: Scheduler,
                 models: ModelBundle, workload: WorkloadGenerator,
                 trace: TraceBus, invariants: InvariantChecker): ...
    def run_to(self, max_sim_time_s: float) -> None:
        """The DES loop implementing §4's data flow end to end: pop next event,
        advance clock, dispatch by event kind (arrival / heralding attempt /
        decoder completion / retry), consult scheduler for admission and path
        allocation, apply decay/memory-access/round-success models at the
        appropriate instants, run the §5 failure-cleanup cascade on
        round failure/cancellation, publish every transition to `trace`,
        and call `invariants.observe` after every publish."""
```

## ⚠ Known Integration Gap — Scheduler Protocol Reconciliation Required

This plan was drafted by parallel agents grounded in the frozen contract
above. Seven of eight package sections (`core`, `entities`, `models`,
`workload`, `observe`, `experiments`, and the DES-loop half of `core/engine.py`)
match that contract exactly — spot-checked by grep across every cross-package
call site. **One section deviates, and it matters:**

The contract above sketches a thin `Scheduler` Protocol
(`on_round_request`, `allocate_path`, `on_lease_heralded`, `maintenance_tick`)
as a placeholder — it was never meant to be the final word, and `core/engine.py`
(Tasks 1–8 below) was written strictly against that placeholder. The
`policies/` section (Tasks 1–5 below), however, independently designed a
**richer and more carefully worked-out** protocol that the thin placeholder
was glossing over — `RoundProjection`/`ProjectableLease` (a real, held-vs-not
distinction with decay-appropriate fidelity projection), `AdmissionOutcome`/
`AdmissionDecision` (carrying the projected probability and threshold for
observability), `LeaseRequestPurpose`/`LeaseDisposition`/`DispositionKind`
(distinguishing round-bound cancellation from pool return from expiry, per
§5's cascade), and four methods — `decide_admission`, `next_lease_request`,
`on_round_terminal`, `register_round_demand` — that map more directly onto
what a real scheduler needs to do at each engine event than the placeholder's
four did.

**Recommendation: adopt `policies/`'s richer protocol as authoritative.**
It is not a casual rename — it resolves a real gap in the placeholder (the
placeholder's `on_round_request(round, state) -> AdmissionDecision` has no
way to express "this lease is already held, project its decay from
`state_held_since`" versus "this lease doesn't exist yet, project from
`HeraldingModel.heralded_fidelity`" without the caller pre-computing
`RoundProjection` — the placeholder just deferred that problem to whoever
implemented it, and `policies/` did the work of solving it).

**Before `core/engine.py` Task 8 (the end-to-end integration test) can pass,
someone with full context on both sides must:**
1. Read `qsim/policies/protocol.py` (Task 1 below) and `qsim/core/engine.py`'s
   actual call sites (Tasks 1–3, 6 below use `scheduler.on_round_request`,
   `scheduler.allocate_path`, `scheduler.on_lease_heralded`).
2. Rewrite those `core/engine.py` call sites to build a `RoundProjection`
   from the engine's real `SyndromeRound`/`EntanglementLease` state and call
   `scheduler.decide_admission(...)` / `scheduler.next_lease_request(...)` /
   `scheduler.on_round_terminal(...)` / `scheduler.register_round_demand(...)`
   instead — `allocate_path`'s path-selection responsibility folds into
   `next_lease_request` returning a `LeaseRequest` naming the desired
   `(path_id, coherence_class)`, which the engine then honors against §7's
   endpoint-exclusivity and capacity constraints (that part of `engine.py`'s
   logic does not need to change, only which object hands it the request).
3. Re-run engine Tasks 1–8's own test suites after the rewrite — they were
   written against the placeholder and will need their scheduler-call
   assertions updated to match, but their assertions about trace events,
   entity state, and timing should not need to change.

This is flagged here rather than silently patched because it is a genuine
design call (which protocol shape is right), not a typo, and the person
executing Task 8 will have running test suites on both sides to verify
against — a better position to make this call correctly than a plan author
guessing blind. Do not skip this reconciliation; `core/engine.py` as
written in Tasks 1–7 below will not import successfully against
`qsim/policies/s0.py`/`s1.py` as written, because the method names differ.

---


## Section 1 of 8 — core/ infrastructure (event heap, keyed RNG, trace bus, invariants, engine state)

### Task 1: Keyed deterministic RNG (qsim/core/rng.py)

**Files:**
- Create: `conftest.py`
- Create: `qsim/core/__init__.py`
- Create: `qsim/core/rng.py`
- Test: `tests/core/test_rng.py`

**Interfaces:**
- Consumes: none (foundational module).
- Produces:
  - `def draw_uniform(run_seed: int, stream: str, key: tuple) -> float`
  - `@dataclass(frozen=True) class Draw: u: float`
  - Task-local scaffolding: root `conftest.py` inserts the repo root onto `sys.path` so `qsim.core.*` (and sibling packages developed in parallel) import cleanly regardless of pytest invocation style. Every later task in this plan relies on this file existing; it is not re-created.

- [ ] **Step 1: Write the failing test**
```python
# tests/core/test_rng.py
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from qsim.core.rng import Draw, draw_uniform

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_draw_uniform_is_deterministic_for_same_inputs():
    a = draw_uniform(run_seed=42, stream="herald", key=("round-1", "ep-a", "ep-b", 0))
    b = draw_uniform(run_seed=42, stream="herald", key=("round-1", "ep-a", "ep-b", 0))
    assert a == b


def test_draw_uniform_varies_with_key():
    a = draw_uniform(run_seed=42, stream="herald", key=("round-1", 0))
    b = draw_uniform(run_seed=42, stream="herald", key=("round-1", 1))
    assert a != b


def test_draw_uniform_varies_with_stream():
    a = draw_uniform(run_seed=42, stream="herald", key=("round-1", 0))
    b = draw_uniform(run_seed=42, stream="decode", key=("round-1", 0))
    assert a != b


def test_draw_uniform_varies_with_run_seed():
    a = draw_uniform(run_seed=1, stream="herald", key=("round-1", 0))
    b = draw_uniform(run_seed=2, stream="herald", key=("round-1", 0))
    assert a != b


def test_draw_uniform_is_in_unit_interval():
    for i in range(2000):
        u = draw_uniform(run_seed=7, stream="workload", key=("arrival", i))
        assert 0.0 <= u < 1.0


def test_draw_uniform_does_not_depend_on_builtin_hash_seed():
    script = (
        "from qsim.core.rng import draw_uniform; "
        "print(draw_uniform(run_seed=99, stream='herald', key=('round-9', 'a', 'b', 3)))"
    )

    def run_with_hash_seed(seed: str) -> str:
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(REPO_ROOT))
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    assert run_with_hash_seed("0") == run_with_hash_seed("4242")


def test_draw_dataclass_holds_uniform_sample():
    d = Draw(u=0.5)
    assert d.u == 0.5


def test_draw_dataclass_is_frozen():
    d = Draw(u=0.5)
    with pytest.raises(FrozenInstanceError):
        d.u = 0.9
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_rng.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core'`
- [ ] **Step 3: Write minimal implementation**
```python
# conftest.py
"""Ensures the repo root is importable so `qsim.core.*` (and sibling qsim
packages developed in parallel) resolve regardless of how pytest is
invoked."""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
```
```python
# qsim/core/__init__.py
"""qsim core: event heap, keyed RNG, trace bus, invariants (frozen M0 contract)."""
```
```python
# qsim/core/rng.py
"""Deterministic, keyed randomness for the qsim engine (design spec §10).

Every draw is addressed by (run_seed, stream, key) rather than drawn from a
sequential stream, so paired policy comparisons can share randomness on
matching semantic events even when policies make different numbers of draws
in different orders. Python's builtin hash() is never used here: it is
salted per-process (PYTHONHASHSEED) and would silently break determinism
across runs, forks, and sweep workers.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

_UINT64_SPAN = 2 ** 64


def _canonical_bytes(run_seed: int, stream: str, key: tuple) -> bytes:
    """Canonical, deterministic serialization of the draw's identity.

    repr() of a tuple of str/int/float/tuple primitives is stable within a
    Python version and does not depend on object identity or hash order
    (unlike dict/set) — exactly the canonical encoding of
    (run_seed, stream, key) that §10 requires.
    """
    return repr((run_seed, stream, key)).encode("utf-8")


def draw_uniform(run_seed: int, stream: str, key: tuple) -> float:
    """Deterministic uniform sample in [0, 1).

    Seeded from SHA-256 over a canonical serialization of
    (run_seed, stream, key); the same semantic key always yields the same
    sample, in any process, with any PYTHONHASHSEED.
    """
    digest = hashlib.sha256(_canonical_bytes(run_seed, stream, key)).digest()
    top_64_bits = int.from_bytes(digest[:8], byteorder="big")
    return top_64_bits / _UINT64_SPAN


@dataclass(frozen=True)
class Draw:
    """A keyed uniform sample, already drawn by the engine (§10)."""
    u: float
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_rng.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add conftest.py qsim/core/__init__.py qsim/core/rng.py tests/core/test_rng.py
git commit -m "feat: add deterministic keyed RNG (qsim/core/rng.py, SHA-256, no builtin hash)"
```

### Task 2: Simulation clock (qsim/core/clock.py)

**Files:**
- Create: `qsim/core/clock.py`
- Test: `tests/core/test_clock.py`

**Interfaces:**
- Consumes: none.
- Produces:
  - `class SimClock: def now(self) -> float; def advance_to(self, t: float) -> None`  (raises if `t < now()`)

- [ ] **Step 1: Write the failing test**
```python
# tests/core/test_clock.py
import pytest

from qsim.core.clock import SimClock


def test_new_clock_starts_at_zero():
    clock = SimClock()
    assert clock.now() == 0.0


def test_advance_to_moves_time_forward():
    clock = SimClock()
    clock.advance_to(5.0)
    assert clock.now() == 5.0


def test_advance_to_same_time_is_allowed():
    clock = SimClock()
    clock.advance_to(3.0)
    clock.advance_to(3.0)
    assert clock.now() == 3.0


def test_advance_to_backward_raises_value_error():
    clock = SimClock()
    clock.advance_to(10.0)
    with pytest.raises(ValueError):
        clock.advance_to(9.999)
    assert clock.now() == 10.0  # rejected advance must not mutate state
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_clock.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.clock'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/core/clock.py
"""Simulation clock (design spec §14: event-time monotonicity)."""

from __future__ import annotations


class SimClock:
    """Monotonic simulation-time clock owned by the DES engine."""

    def __init__(self) -> None:
        self._now: float = 0.0

    def now(self) -> float:
        return self._now

    def advance_to(self, t: float) -> None:
        if t < self._now:
            raise ValueError(
                f"SimClock cannot move backward: now={self._now!r}, requested={t!r}"
            )
        self._now = t
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_clock.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/core/clock.py tests/core/test_clock.py
git commit -m "feat: add monotonic SimClock (qsim/core/clock.py)"
```

### Task 3: Event heap with (time, seq) tiebreak (qsim/core/event_heap.py)

**Files:**
- Create: `qsim/core/event_heap.py`
- Test: `tests/core/test_event_heap.py`

**Interfaces:**
- Consumes: none.
- Produces:
  - `@dataclass(order=True) class HeapEntry: time: float; seq: int; payload: object = field(compare=False)`
  - `class EventHeap: def push(self, time: float, payload: object) -> int; def pop(self) -> HeapEntry | None; def __len__(self) -> int`

- [ ] **Step 1: Write the failing test**
```python
# tests/core/test_event_heap.py
from qsim.core.event_heap import EventHeap, HeapEntry


def test_push_returns_sequential_seq_starting_at_zero():
    heap = EventHeap()
    assert heap.push(1.0, "a") == 0
    assert heap.push(2.0, "b") == 1
    assert heap.push(1.0, "c") == 2


def test_len_tracks_pending_entries():
    heap = EventHeap()
    assert len(heap) == 0
    heap.push(1.0, "a")
    heap.push(2.0, "b")
    assert len(heap) == 2
    heap.pop()
    assert len(heap) == 1


def test_pop_on_empty_heap_returns_none():
    heap = EventHeap()
    assert heap.pop() is None


def test_pop_returns_earliest_time_first():
    heap = EventHeap()
    heap.push(5.0, "later")
    heap.push(1.0, "earlier")
    heap.push(3.0, "middle")

    order = [heap.pop().payload for _ in range(3)]
    assert order == ["earlier", "middle", "later"]


def test_equal_time_events_tiebreak_by_seq_in_push_order():
    heap = EventHeap()
    heap.push(2.0, "second-pushed-later-time")
    seq_first = heap.push(1.0, "first-pushed-at-t1")
    seq_second = heap.push(1.0, "second-pushed-at-t1")
    assert seq_first < seq_second

    first = heap.pop()
    second = heap.pop()
    assert (first.time, first.payload) == (1.0, "first-pushed-at-t1")
    assert (second.time, second.payload) == (1.0, "second-pushed-at-t1")


def test_equal_time_tiebreak_is_independent_of_heap_internal_order():
    heap = EventHeap()
    seqs_and_payloads = []
    for payload in ["d", "b", "a", "c"]:
        seq = heap.push(9.0, payload)
        seqs_and_payloads.append((seq, payload))
    expected_order = [p for _, p in sorted(seqs_and_payloads)]

    popped = [heap.pop().payload for _ in range(4)]
    assert popped == expected_order


def test_heap_entry_orders_by_time_then_seq_ignoring_payload():
    a = HeapEntry(time=1.0, seq=0, payload={"unorderable": object()})
    b = HeapEntry(time=1.0, seq=1, payload={"unorderable": object()})
    c = HeapEntry(time=0.5, seq=5, payload=None)
    assert a < b
    assert c < a
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_event_heap.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.event_heap'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/core/event_heap.py
"""Event heap for the DES core: (time, seq) ordering (design spec §14)."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field


@dataclass(order=True)
class HeapEntry:
    time: float
    seq: int
    payload: object = field(compare=False)


class EventHeap:
    """Min-heap of (time, seq)-ordered entries.

    seq is assigned in push() call order and used as the tiebreak for
    equal-time entries, so events scheduled at the same simulated instant
    are popped in the order they were scheduled (FIFO), never in an order
    that depends on heap internal structure or payload identity/orderability.
    """

    def __init__(self) -> None:
        self._heap: list[HeapEntry] = []
        self._next_seq: int = 0

    def push(self, time: float, payload: object) -> int:
        seq = self._next_seq
        self._next_seq += 1
        heapq.heappush(self._heap, HeapEntry(time=time, seq=seq, payload=payload))
        return seq

    def pop(self) -> HeapEntry | None:
        if not self._heap:
            return None
        return heapq.heappop(self._heap)

    def __len__(self) -> int:
        return len(self._heap)
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_event_heap.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/core/event_heap.py tests/core/test_event_heap.py
git commit -m "feat: add EventHeap with (time, seq) tiebreak (qsim/core/event_heap.py)"
```

### Task 4: Trace bus and event schema (qsim/core/trace.py)

**Files:**
- Create: `qsim/core/trace.py`
- Test: `tests/core/test_trace.py`

**Interfaces:**
- Consumes: `qsim.core.clock.SimClock.now() -> float` (Task 2).
- Produces:
  - `EventId = tuple[str, int]`
  - `@dataclass(frozen=True) class Event: run_id: str; seq: int; sim_time: float; event_type: str; entity_id: str; causal_parent_id: EventId | None; payload: dict`
  - `EVENT_TYPES: list[str]` (verbatim 23-entry list from the frozen contract)
  - `class TraceBus: def publish(self, event_type: str, entity_id: str, causal_parent_id: EventId | None, payload: dict) -> EventId; def subscribe(self, fn: Callable[[Event], None]) -> None`
  - Task-local addition (constructor not fixed by the frozen contract, needed to satisfy `publish`'s frozen signature with no explicit time argument): `TraceBus.__init__(self, run_id: str, clock: SimClock)`. `qsim/core/engine.py` (separate section) must construct `TraceBus` this way.

- [ ] **Step 1: Write the failing test**
```python
# tests/core/test_trace.py
from dataclasses import FrozenInstanceError

import pytest

from qsim.core.clock import SimClock
from qsim.core.trace import EVENT_TYPES, Event, TraceBus


def test_publish_returns_event_id_with_run_id_and_incrementing_seq():
    bus = TraceBus(run_id="run-1", clock=SimClock())
    first = bus.publish("round.arrived", "round-1", None, {})
    second = bus.publish("round.arrived", "round-2", None, {})
    assert first == ("run-1", 0)
    assert second == ("run-1", 1)


def test_publish_stamps_event_with_current_clock_time():
    clock = SimClock()
    bus = TraceBus(run_id="run-1", clock=clock)
    clock.advance_to(4.5)

    received = []
    bus.subscribe(received.append)
    bus.publish("round.arrived", "round-1", None, {"x": 1})

    assert len(received) == 1
    event = received[0]
    assert isinstance(event, Event)
    assert event.sim_time == 4.5
    assert event.run_id == "run-1"
    assert event.entity_id == "round-1"
    assert event.event_type == "round.arrived"
    assert event.causal_parent_id is None
    assert event.payload == {"x": 1}


def test_subscribe_supports_multiple_subscribers_all_notified():
    bus = TraceBus(run_id="run-1", clock=SimClock())
    seen_a, seen_b = [], []
    bus.subscribe(seen_a.append)
    bus.subscribe(seen_b.append)

    bus.publish(
        "draw.sampled", "herald:round-1:0", None,
        {"stream": "herald", "key": (), "uniform": 0.4},
    )

    assert len(seen_a) == 1
    assert len(seen_b) == 1
    assert seen_a[0] is seen_b[0]


def test_publish_carries_causal_parent_id():
    bus = TraceBus(run_id="run-1", clock=SimClock())
    parent_id = bus.publish("round.arrived", "round-1", None, {})
    child_id = bus.publish("round.admitted", "round-1", parent_id, {})

    received = []
    bus.subscribe(received.append)
    bus.publish("round.completed_in_deadline", "round-1", child_id, {})
    assert received[0].causal_parent_id == child_id


def test_publish_rejects_unknown_event_type():
    bus = TraceBus(run_id="run-1", clock=SimClock())
    with pytest.raises(ValueError):
        bus.publish("round.made_up_type", "round-1", None, {})


def test_event_dataclass_is_frozen():
    event = Event(
        run_id="run-1", seq=0, sim_time=0.0, event_type="round.arrived",
        entity_id="round-1", causal_parent_id=None, payload={},
    )
    with pytest.raises(FrozenInstanceError):
        event.seq = 1


@pytest.mark.parametrize("event_type", EVENT_TYPES)
def test_every_event_type_is_publishable_and_round_trips(event_type):
    bus = TraceBus(run_id="run-1", clock=SimClock())
    received = []
    bus.subscribe(received.append)

    event_id = bus.publish(event_type, "entity-1", None, {"note": event_type})

    assert event_id == ("run-1", 0)
    assert len(received) == 1
    assert received[0].event_type == event_type
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_trace.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.trace'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/core/trace.py
"""Trace bus: every state transition is a typed, causally-linked event
(design spec §12: "the trace is the deliverable").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from qsim.core.clock import SimClock

EventId = tuple[str, int]


@dataclass(frozen=True)
class Event:
    run_id: str
    seq: int
    sim_time: float
    event_type: str
    entity_id: str
    causal_parent_id: EventId | None
    payload: dict


EVENT_TYPES = [
    # lease lifecycle (§5)
    "lease.requested", "lease.heralded", "lease.consumed", "lease.expired", "lease.cancelled",
    "lease.pool_returned",  # pregen return path, accounted separately per §5/§11
    # round lifecycle (§5, §11)
    "round.arrived", "round.admitted", "round.deferred", "round.dropped",
    "round.completed_in_deadline", "round.completed_late", "round.failed", "round.retried",
    # switch reservation lifecycle (§7)
    "reservation.acquired", "reservation.configuring", "reservation.active", "reservation.released",
    # decoder job lifecycle (§5)
    "decoder.enqueued", "decoder.dequeued", "decoder.completed", "decoder.cancelled",
    # randomness (§10) — every draw is itself a trace event
    "draw.sampled",  # payload: {stream, key, uniform}
]

_EVENT_TYPE_SET = frozenset(EVENT_TYPES)


class TraceBus:
    """Publishes trace events and fans them out to subscribers.

    Construction takes the run's identity and the shared SimClock so that
    publish()'s frozen signature (event_type, entity_id, causal_parent_id,
    payload) -> EventId never needs an explicit time argument: sim_time is
    always the engine's current clock reading at publish time.
    """

    def __init__(self, run_id: str, clock: SimClock) -> None:
        self._run_id = run_id
        self._clock = clock
        self._next_seq = 0
        self._subscribers: list[Callable[[Event], None]] = []

    def publish(self, event_type: str, entity_id: str,
                causal_parent_id: EventId | None, payload: dict) -> EventId:
        if event_type not in _EVENT_TYPE_SET:
            raise ValueError(f"unknown event_type: {event_type!r}")

        seq = self._next_seq
        self._next_seq += 1
        event = Event(
            run_id=self._run_id,
            seq=seq,
            sim_time=self._clock.now(),
            event_type=event_type,
            entity_id=entity_id,
            causal_parent_id=causal_parent_id,
            payload=payload,
        )
        for subscriber in self._subscribers:
            subscriber(event)
        return (self._run_id, seq)

    def subscribe(self, fn: Callable[[Event], None]) -> None:
        self._subscribers.append(fn)
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_trace.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/core/trace.py tests/core/test_trace.py
git commit -m "feat: add TraceBus and frozen Event/EVENT_TYPES schema (qsim/core/trace.py)"
```

### Task 5: Engine state and model bundle (qsim/core/state.py)

**Files:**
- Create: `qsim/core/state.py`
- Test: `tests/core/test_state.py`

**Interfaces:**
- Consumes: none (fields reference `qsim/entities/`/`qsim/models/` types by forward-reference string only — `qsim/core/` imports nothing from them, preserving §4's downward-only dependency direction).
- Produces:
  - `@dataclass(frozen=True) class ModelBundle: decay: "DecayModel"; memory_access: "MemoryAccessModel"; heralding: "HeraldingModel"; round_success: "RoundSuccessModel"; decoder_service: "DecoderServiceModel"`
  - `@dataclass class EngineState: now: float; epoch: "CalibrationEpoch"; models: ModelBundle; decoder_backlog: int; active_reservations: dict["PathId", "SwitchPathReservation"]; pool: dict[tuple["PathId", "CoherenceClass"], list["EntanglementLease"]]; switch_capacity_c: int; hold_until_consumption: bool`

- [ ] **Step 1: Write the failing test**
```python
# tests/core/test_state.py
import dataclasses

import pytest

from qsim.core.state import EngineState, ModelBundle


def test_model_bundle_holds_all_five_surfaces():
    bundle = ModelBundle(
        decay="decay-model", memory_access="memory-model", heralding="heralding-model",
        round_success="round-success-model", decoder_service="decoder-service-model",
    )
    assert bundle.decay == "decay-model"
    assert bundle.memory_access == "memory-model"
    assert bundle.heralding == "heralding-model"
    assert bundle.round_success == "round-success-model"
    assert bundle.decoder_service == "decoder-service-model"


def test_model_bundle_is_frozen():
    bundle = ModelBundle(
        decay="d", memory_access="m", heralding="h", round_success="r", decoder_service="s",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        bundle.decay = "other"


def test_engine_state_construction_exposes_all_fields():
    bundle = ModelBundle(decay="d", memory_access="m", heralding="h", round_success="r", decoder_service="s")
    state = EngineState(
        now=0.0,
        epoch="epoch-0",
        models=bundle,
        decoder_backlog=0,
        active_reservations={},
        pool={},
        switch_capacity_c=4,
        hold_until_consumption=False,
    )
    assert state.now == 0.0
    assert state.epoch == "epoch-0"
    assert state.models is bundle
    assert state.decoder_backlog == 0
    assert state.active_reservations == {}
    assert state.pool == {}
    assert state.switch_capacity_c == 4
    assert state.hold_until_consumption is False


def test_engine_state_is_mutable_for_engine_updates():
    bundle = ModelBundle(decay="d", memory_access="m", heralding="h", round_success="r", decoder_service="s")
    state = EngineState(
        now=0.0, epoch="epoch-0", models=bundle, decoder_backlog=0,
        active_reservations={}, pool={}, switch_capacity_c=4, hold_until_consumption=False,
    )
    state.now = 12.5
    state.decoder_backlog = 3
    state.active_reservations["path-a"] = "reservation-a"
    assert state.now == 12.5
    assert state.decoder_backlog == 3
    assert state.active_reservations == {"path-a": "reservation-a"}
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.state'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/core/state.py
"""Engine state passed into Scheduler and InvariantChecker calls
(design spec §4, §8, §14).

Field types reference entities/ and models/ types by forward-reference
string only (never imported): core/ is the dependency-free foundation
package (§4's "dependency arrows point downward only"), and importing
entities/models here would invert that direction.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelBundle:
    decay: "DecayModel"
    memory_access: "MemoryAccessModel"
    heralding: "HeraldingModel"
    round_success: "RoundSuccessModel"
    decoder_service: "DecoderServiceModel"


@dataclass
class EngineState:
    """Read-only view passed into Scheduler calls. The engine constructs and
    mutates the underlying state; policies must not mutate it directly."""
    now: float
    epoch: "CalibrationEpoch"
    models: ModelBundle
    decoder_backlog: int
    active_reservations: dict["PathId", "SwitchPathReservation"]
    pool: dict[tuple["PathId", "CoherenceClass"], list["EntanglementLease"]]
    switch_capacity_c: int
    hold_until_consumption: bool
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_state.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/core/state.py tests/core/test_state.py
git commit -m "feat: add ModelBundle and EngineState (qsim/core/state.py)"
```

### Task 6: Invariant checker (qsim/core/invariants.py)

**Files:**
- Create: `qsim/core/invariants.py`
- Test: `tests/core/test_invariants.py`

**Interfaces:**
- Consumes: `qsim.core.trace.Event` (Task 4); `qsim.core.state.EngineState` and its `.active_reservations` field (Task 5).
- Produces:
  - `class InvariantViolation(Exception)`
  - `class InvariantChecker: def observe(self, event: Event, state: EngineState) -> None`
  - Task-local conventions (documented here since `qsim/core/` cannot import `qsim/entities/`, and `qsim/core/engine.py`'s task must populate events/state compatibly with them):
    - Lease-lifecycle legality is tracked from `Event.event_type` strings restricted to `EVENT_TYPES`'s `lease.*` subset (`lease.requested`/`heralded`/`consumed`/`expired`/`cancelled`), not from `qsim.entities.LeaseState`. `lease.pool_returned` is deliberately excluded — it is pregen bookkeeping, not a lifecycle transition.
    - Fidelity legality is read from `Event.payload["fidelity"]` when that key is present; absent otherwise.
    - Reservation-leak detection duck-types each value in `EngineState.active_reservations` against `.holder_id: str` and `.state` (a bare string, or an enum exposing `.value`) equal to `"released"` once released — matching `qsim.entities.SwitchPathReservation`/`qsim.entities.ReservationState` without importing `qsim/entities/`.

- [ ] **Step 1: Write the failing test**
```python
# tests/core/test_invariants.py
import pytest

from qsim.core.invariants import InvariantChecker, InvariantViolation
from qsim.core.state import EngineState, ModelBundle
from qsim.core.trace import Event


def make_state(active_reservations=None):
    bundle = ModelBundle(decay="d", memory_access="m", heralding="h", round_success="r", decoder_service="s")
    return EngineState(
        now=0.0, epoch="epoch-0", models=bundle, decoder_backlog=0,
        active_reservations=active_reservations or {}, pool={},
        switch_capacity_c=4, hold_until_consumption=False,
    )


def make_event(event_type, entity_id, sim_time=0.0, payload=None, seq=0, causal_parent_id=None):
    return Event(
        run_id="run-1", seq=seq, sim_time=sim_time, event_type=event_type,
        entity_id=entity_id, causal_parent_id=causal_parent_id, payload=payload or {},
    )


class FakeReservation:
    def __init__(self, holder_id, state):
        self.holder_id = holder_id
        self.state = state  # plain string, mirrors ReservationState.value


def test_legal_lease_lifecycle_does_not_raise():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("lease.requested", "lease-1", sim_time=0.0, seq=0), state)
    checker.observe(make_event("lease.heralded", "lease-1", sim_time=1.0, seq=1), state)
    checker.observe(make_event("lease.consumed", "lease-1", sim_time=2.0, seq=2), state)


def test_event_time_non_monotonicity_raises():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("round.arrived", "round-1", sim_time=5.0, seq=0), state)
    with pytest.raises(InvariantViolation):
        checker.observe(make_event("round.admitted", "round-1", sim_time=4.9, seq=1), state)


def test_equal_sim_time_is_not_a_monotonicity_violation():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("round.arrived", "round-1", sim_time=3.0, seq=0), state)
    checker.observe(make_event("round.admitted", "round-1", sim_time=3.0, seq=1), state)


def test_invariant_violation_carries_offending_event():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("round.arrived", "round-1", sim_time=5.0, seq=0), state)
    offending = make_event("round.admitted", "round-1", sim_time=4.0, seq=1)
    with pytest.raises(InvariantViolation) as exc_info:
        checker.observe(offending, state)
    assert exc_info.value.event is offending


def test_illegal_lease_transition_consumed_without_heralding_raises():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("lease.requested", "lease-1", sim_time=0.0, seq=0), state)
    with pytest.raises(InvariantViolation):
        checker.observe(make_event("lease.consumed", "lease-1", sim_time=1.0, seq=1), state)


def test_double_consumption_raises():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("lease.requested", "lease-1", sim_time=0.0, seq=0), state)
    checker.observe(make_event("lease.heralded", "lease-1", sim_time=1.0, seq=1), state)
    checker.observe(make_event("lease.consumed", "lease-1", sim_time=2.0, seq=2), state)
    with pytest.raises(InvariantViolation):
        checker.observe(make_event("lease.consumed", "lease-1", sim_time=3.0, seq=3), state)


def test_pool_returned_event_is_not_checked_as_a_lease_transition():
    checker = InvariantChecker()
    state = make_state()
    checker.observe(make_event("lease.requested", "lease-1", sim_time=0.0, seq=0), state)
    checker.observe(make_event("lease.heralded", "lease-1", sim_time=1.0, seq=1), state)
    checker.observe(make_event("lease.pool_returned", "lease-1", sim_time=2.0, seq=2), state)
    checker.observe(make_event("lease.consumed", "lease-1", sim_time=3.0, seq=3), state)


def test_fidelity_above_one_raises():
    checker = InvariantChecker()
    state = make_state()
    with pytest.raises(InvariantViolation):
        checker.observe(
            make_event("lease.heralded", "lease-1", sim_time=0.0, seq=0, payload={"fidelity": 1.5}),
            state,
        )


def test_fidelity_below_zero_raises():
    checker = InvariantChecker()
    state = make_state()
    with pytest.raises(InvariantViolation):
        checker.observe(
            make_event("lease.heralded", "lease-1", sim_time=0.0, seq=0, payload={"fidelity": -0.01}),
            state,
        )


@pytest.mark.parametrize("boundary_fidelity", [0.0, 1.0])
def test_fidelity_at_boundary_is_legal(boundary_fidelity):
    checker = InvariantChecker()
    state = make_state()
    checker.observe(
        make_event("lease.heralded", "lease-1", sim_time=0.0, seq=0, payload={"fidelity": boundary_fidelity}),
        state,
    )


def test_reservation_outliving_its_holder_raises():
    checker = InvariantChecker()
    leaked = FakeReservation(holder_id="round-1", state="active")
    state = make_state(active_reservations={"path-a": leaked})

    checker.observe(make_event("round.arrived", "round-1", sim_time=0.0, seq=0), state)
    with pytest.raises(InvariantViolation):
        checker.observe(make_event("round.failed", "round-1", sim_time=1.0, seq=1), state)


def test_reservation_released_before_or_at_terminal_event_does_not_raise():
    checker = InvariantChecker()
    released = FakeReservation(holder_id="round-1", state="released")
    state = make_state(active_reservations={"path-a": released})

    checker.observe(make_event("round.arrived", "round-1", sim_time=0.0, seq=0), state)
    checker.observe(make_event("round.failed", "round-1", sim_time=1.0, seq=1), state)


def test_reservation_leak_for_unrelated_holder_does_not_raise():
    checker = InvariantChecker()
    other = FakeReservation(holder_id="round-2", state="active")
    state = make_state(active_reservations={"path-a": other})

    checker.observe(make_event("round.arrived", "round-1", sim_time=0.0, seq=0), state)
    checker.observe(make_event("round.failed", "round-1", sim_time=1.0, seq=1), state)
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_invariants.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.invariants'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/core/invariants.py
"""Mechanical invariant checks over the trace (design spec §14).

These invariants prove the bookkeeping is legal; they provide zero
protection against a wrong physics model (see §14's scope statement).
Violation is fail-stop: InvariantViolation carries the offending event so
the caller can flush the trace and crash loudly with its causal chain.
"""

from __future__ import annotations

from qsim.core.state import EngineState
from qsim.core.trace import Event


class InvariantViolation(Exception):
    """Raised with the causal chain of the offending event (§14)."""

    def __init__(self, message: str, event: Event) -> None:
        super().__init__(f"{message} | offending event: {event!r}")
        self.event = event


# Lease-lifecycle legality (design spec §5, §14), expressed directly over
# EVENT_TYPES' lease.* strings rather than entities.LeaseState: core/ does
# not import entities/ (dependency arrows point downward only, §4).
_LEASE_TRANSITION_EVENTS = {
    "lease.requested": "requested",
    "lease.heralded": "heralded",
    "lease.consumed": "consumed",
    "lease.expired": "expired",
    "lease.cancelled": "cancelled",
    # lease.pool_returned is bookkeeping for the pregen pool, not a
    # LeaseState transition (design spec §5), so it is deliberately absent
    # and never checked for lifecycle legality.
}

_LEGAL_LEASE_TRANSITIONS: dict[str | None, set[str]] = {
    None: {"requested"},
    "requested": {"heralded", "cancelled"},
    "heralded": {"consumed", "expired", "cancelled"},
    "consumed": set(),
    "expired": set(),
    "cancelled": set(),
}

_ROUND_TERMINAL_EVENTS = {
    "round.completed_in_deadline", "round.completed_late", "round.failed", "round.dropped",
}
_LEASE_TERMINAL_EVENTS = {"lease.consumed", "lease.expired", "lease.cancelled"}


class InvariantChecker:
    """Continuously checks mechanical correctness (§14).

    Maintains its own history of lease states and terminated holders,
    reconstructed purely from the Event stream it observes — EngineState is
    a present-moment view (§4) and does not itself retain that history.
    """

    def __init__(self) -> None:
        self._last_sim_time: float | None = None
        self._lease_states: dict[str, str | None] = {}
        self._terminated_holders: set[str] = set()

    def observe(self, event: Event, state: EngineState) -> None:
        self._check_monotonicity(event)
        self._check_lease_transition(event)
        self._check_fidelity(event)
        self._record_terminated_holder(event)
        self._check_reservation_leak(event, state)
        self._last_sim_time = event.sim_time

    def _check_monotonicity(self, event: Event) -> None:
        if self._last_sim_time is not None and event.sim_time < self._last_sim_time:
            raise InvariantViolation(
                f"event-time non-monotonicity: {event.sim_time} follows {self._last_sim_time}",
                event,
            )

    def _check_lease_transition(self, event: Event) -> None:
        target = _LEASE_TRANSITION_EVENTS.get(event.event_type)
        if target is None:
            return
        current = self._lease_states.get(event.entity_id)
        if target not in _LEGAL_LEASE_TRANSITIONS[current]:
            raise InvariantViolation(
                f"illegal lease transition for {event.entity_id!r}: "
                f"{current!r} -> {target!r} via {event.event_type!r}",
                event,
            )
        self._lease_states[event.entity_id] = target

    def _check_fidelity(self, event: Event) -> None:
        if "fidelity" not in event.payload:
            return
        fidelity = event.payload["fidelity"]
        if not (0.0 <= fidelity <= 1.0):
            raise InvariantViolation(
                f"fidelity {fidelity!r} outside [0,1] on entity {event.entity_id!r}",
                event,
            )

    def _record_terminated_holder(self, event: Event) -> None:
        if event.event_type in _ROUND_TERMINAL_EVENTS or event.event_type in _LEASE_TERMINAL_EVENTS:
            self._terminated_holders.add(event.entity_id)

    def _check_reservation_leak(self, event: Event, state: EngineState) -> None:
        for path_id, reservation in state.active_reservations.items():
            holder_id = reservation.holder_id
            if holder_id not in self._terminated_holders:
                continue
            state_value = getattr(reservation.state, "value", reservation.state)
            if state_value != "released":
                raise InvariantViolation(
                    f"SwitchPathReservation on {path_id!r} outlives terminated holder {holder_id!r}",
                    event,
                )
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_invariants.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/core/invariants.py tests/core/test_invariants.py
git commit -m "feat: add InvariantChecker for §14 mechanical invariants (qsim/core/invariants.py)"
```
---

## Section 2 of 8 — entities/ (inert dataclasses + lifecycle state machines)

### Task 1: Module / PortId / PathId

**Files:**
- Create: `qsim/__init__.py`, `qsim/entities/__init__.py`, `qsim/entities/module.py`
- Test: `tests/entities/test_module.py`

**Interfaces:**
- Consumes: none (foundational entity types; stdlib `dataclasses` only).
- Produces: `PortId` (frozen dataclass: `module_id: str`, `port_index: int`), `Module` (dataclass: `module_id: str`, `ports: tuple[PortId, ...]`), `PathId = tuple[PortId, PortId]`, `make_path_id(a: PortId, b: PortId) -> PathId`.

- [ ] **Step 1: Write the failing test**
```python
# tests/entities/test_module.py
import dataclasses

import pytest

from qsim.entities.module import Module, PathId, PortId, make_path_id


def test_portid_is_frozen():
    port = PortId(module_id="mod-a", port_index=0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        port.port_index = 1  # type: ignore[misc]


def test_portid_is_hashable_and_usable_in_sets():
    a = PortId("mod-a", 0)
    b = PortId("mod-a", 0)
    c = PortId("mod-a", 1)
    assert a == b
    assert {a, b, c} == {a, c}


def test_module_holds_ports_tuple():
    p0 = PortId("mod-a", 0)
    p1 = PortId("mod-a", 1)
    module = Module(module_id="mod-a", ports=(p0, p1))
    assert module.module_id == "mod-a"
    assert module.ports == (p0, p1)


def test_make_path_id_is_symmetric_and_canonically_ordered():
    a = PortId("mod-a", 0)
    b = PortId("mod-b", 1)
    assert make_path_id(a, b) == make_path_id(b, a)
    assert make_path_id(a, b) == (a, b)  # "mod-a" < "mod-b"


def test_make_path_id_usable_as_dict_key_regardless_of_argument_order():
    a = PortId("mod-a", 0)
    b = PortId("mod-b", 1)
    table: dict[PathId, str] = {make_path_id(a, b): "reservation-1"}
    assert table[make_path_id(b, a)] == "reservation-1"
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/entities/test_module.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim'` (or `qsim.entities.module`)
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/__init__.py
"""qsim: discrete-event simulator for entanglement-first quantum OS
resource management (design spec companion to docs/quantum_os_.md)."""
```
```python
# qsim/entities/__init__.py
"""qsim.entities: inert dataclass object model with lifecycle state
machines and no embedded decisions (design spec §4, §5)."""
```
```python
# qsim/entities/module.py
"""Module, PortId, and switch-fabric PathId entities (design spec §5, §7)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PortId:
    module_id: str
    port_index: int


@dataclass
class Module:
    module_id: str
    ports: tuple[PortId, ...]


# PathId is the pair of endpoints a crossbar path connects, canonically
# ordered so (a, b) and (b, a) hash identically (design spec §7).
PathId = tuple[PortId, PortId]


def make_path_id(a: PortId, b: PortId) -> PathId:
    return tuple(sorted((a, b), key=lambda p: (p.module_id, p.port_index)))
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/entities/test_module.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/__init__.py qsim/entities/__init__.py qsim/entities/module.py tests/entities/test_module.py
git commit -m "feat: add Module, PortId, and PathId entities"
```

### Task 2: CoherenceClass / QubitHandle

**Files:**
- Create: `qsim/entities/qubit.py`
- Test: `tests/entities/test_qubit.py`

**Interfaces:**
- Consumes: `"CalibrationEpoch"` (forward-reference type only, from `qsim.entities.calibration`, defined in Task 7; no runtime import to avoid a `qubit.py` <-> `calibration.py` cycle since `CalibrationEpoch` itself references `CoherenceClass`).
- Produces: `CoherenceClass` (Enum: `MESSENGER = "messenger"`, `MEMORY = "memory"`), `QubitHandle` (dataclass: `qubit_id: str`, `module_id: str`, `coherence_class: CoherenceClass`, `calibration_epoch: "CalibrationEpoch"`, `state_held_since: float | None = None`, `fidelity_at_hold_start: float | None = None`, `access_count: int = 0`) with task-local methods `hold(at: float, fidelity: float) -> None`, `release() -> None`, `record_access() -> None`.

- [ ] **Step 1: Write the failing test**
```python
# tests/entities/test_qubit.py
import pytest

from qsim.entities.qubit import CoherenceClass, QubitHandle


def make_handle() -> QubitHandle:
    return QubitHandle(
        qubit_id="q-1",
        module_id="mod-a",
        coherence_class=CoherenceClass.MEMORY,
        calibration_epoch=None,  # forward-ref type only; not exercised here
    )


def test_coherence_class_values():
    assert CoherenceClass.MESSENGER.value == "messenger"
    assert CoherenceClass.MEMORY.value == "memory"


def test_qubit_handle_starts_unheld():
    handle = make_handle()
    assert handle.state_held_since is None
    assert handle.fidelity_at_hold_start is None
    assert handle.access_count == 0


def test_hold_sets_timestamp_and_fidelity():
    handle = make_handle()
    handle.hold(at=10.0, fidelity=0.95)
    assert handle.state_held_since == 10.0
    assert handle.fidelity_at_hold_start == 0.95


def test_hold_while_already_held_raises():
    handle = make_handle()
    handle.hold(at=10.0, fidelity=0.95)
    with pytest.raises(ValueError):
        handle.hold(at=11.0, fidelity=0.9)


def test_release_clears_held_state():
    handle = make_handle()
    handle.hold(at=10.0, fidelity=0.95)
    handle.release()
    assert handle.state_held_since is None
    assert handle.fidelity_at_hold_start is None


def test_release_without_hold_raises():
    handle = make_handle()
    with pytest.raises(ValueError):
        handle.release()


def test_record_access_increments_count():
    handle = make_handle()
    handle.record_access()
    handle.record_access()
    assert handle.access_count == 2
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/entities/test_qubit.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.entities.qubit'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/entities/qubit.py
"""QubitHandle entity: location, role class, calibration epoch, and the
lazily materialized fidelity-tracking state described in design spec §5 —
passive decay is evaluated by the engine from `state_held_since` at access
and evaluation instants; nothing here updates per tick."""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qsim.entities.calibration import CalibrationEpoch


class CoherenceClass(Enum):
    MESSENGER = "messenger"
    MEMORY = "memory"


@dataclass
class QubitHandle:
    qubit_id: str
    module_id: str
    coherence_class: CoherenceClass
    calibration_epoch: "CalibrationEpoch"
    state_held_since: float | None = None
    fidelity_at_hold_start: float | None = None
    access_count: int = 0  # drives MemoryAccessModel's linear wear (§6)

    def hold(self, at: float, fidelity: float) -> None:
        """Begin holding entangled state at the given fidelity. Illegal
        while already holding (must release first)."""
        if self.state_held_since is not None:
            raise ValueError(
                f"qubit {self.qubit_id} is already held since "
                f"{self.state_held_since}; cannot hold again at {at}"
            )
        self.state_held_since = at
        self.fidelity_at_hold_start = fidelity

    def release(self) -> None:
        """Stop holding entangled state. Illegal if not currently held."""
        if self.state_held_since is None:
            raise ValueError(f"qubit {self.qubit_id} is not currently held")
        self.state_held_since = None
        self.fidelity_at_hold_start = None

    def record_access(self) -> None:
        """Record a memory-access event; drives MemoryAccessModel wear."""
        self.access_count += 1
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/entities/test_qubit.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/entities/qubit.py tests/entities/test_qubit.py
git commit -m "feat: add CoherenceClass and QubitHandle entities"
```

### Task 3: LeaseState / EntanglementLease

**Files:**
- Create: `qsim/entities/lease.py`
- Test: `tests/entities/test_lease.py`

**Interfaces:**
- Consumes: `PortId`, `PathId` from `qsim.entities.module` (Task 1).
- Produces: `LeaseState` (Enum: `REQUESTED`, `HERALDED`, `CONSUMED`, `EXPIRED`, `CANCELLED`), `TERMINAL_LEASE_STATES: frozenset[LeaseState]`, `EntanglementLease` (dataclass: `lease_id: str`, `endpoints: tuple[PortId, PortId]`, `path_id: PathId`, `created_at: float`, `freshness_bound_s: float`, `fidelity_at_herald: float | None = None`, `heralded_at: float | None = None`, `state: LeaseState = LeaseState.REQUESTED`, `retry_count: int = 0`) with task-local methods `mark_heralded(at: float, fidelity: float) -> None`, `consume() -> None`, `expire() -> None`, `cancel() -> None`, `is_fresh(now: float) -> bool`.

- [ ] **Step 1: Write the failing test**
```python
# tests/entities/test_lease.py
import pytest

from qsim.entities.lease import EntanglementLease, LeaseState
from qsim.entities.module import PortId, make_path_id


def make_lease(freshness_bound_s: float = 5.0) -> EntanglementLease:
    a = PortId("mod-a", 0)
    b = PortId("mod-b", 0)
    return EntanglementLease(
        lease_id="lease-1",
        endpoints=(a, b),
        path_id=make_path_id(a, b),
        created_at=0.0,
        freshness_bound_s=freshness_bound_s,
    )


def test_lease_starts_requested():
    lease = make_lease()
    assert lease.state is LeaseState.REQUESTED
    assert lease.heralded_at is None
    assert lease.fidelity_at_herald is None


def test_mark_heralded_sets_fields_and_state():
    lease = make_lease()
    lease.mark_heralded(at=1.0, fidelity=0.99)
    assert lease.state is LeaseState.HERALDED
    assert lease.heralded_at == 1.0
    assert lease.fidelity_at_herald == 0.99


def test_mark_heralded_twice_raises():
    lease = make_lease()
    lease.mark_heralded(at=1.0, fidelity=0.99)
    with pytest.raises(ValueError):
        lease.mark_heralded(at=2.0, fidelity=0.9)


def test_consume_from_heralded_succeeds():
    lease = make_lease()
    lease.mark_heralded(at=1.0, fidelity=0.99)
    lease.consume()
    assert lease.state is LeaseState.CONSUMED


def test_consume_without_heralding_raises():
    lease = make_lease()
    with pytest.raises(ValueError):
        lease.consume()


def test_double_consume_raises():
    lease = make_lease()
    lease.mark_heralded(at=1.0, fidelity=0.99)
    lease.consume()
    with pytest.raises(ValueError):
        lease.consume()


def test_consume_after_expiry_raises():
    lease = make_lease()
    lease.mark_heralded(at=1.0, fidelity=0.99)
    lease.expire()
    with pytest.raises(ValueError):
        lease.consume()


def test_expire_from_requested_and_heralded_succeeds():
    requested = make_lease()
    requested.expire()
    assert requested.state is LeaseState.EXPIRED

    heralded = make_lease()
    heralded.mark_heralded(at=1.0, fidelity=0.99)
    heralded.expire()
    assert heralded.state is LeaseState.EXPIRED


def test_expire_from_terminal_state_raises():
    lease = make_lease()
    lease.mark_heralded(at=1.0, fidelity=0.99)
    lease.cancel()
    with pytest.raises(ValueError):
        lease.expire()


def test_cancel_from_requested_and_heralded_succeeds():
    requested = make_lease()
    requested.cancel()
    assert requested.state is LeaseState.CANCELLED

    heralded = make_lease()
    heralded.mark_heralded(at=1.0, fidelity=0.99)
    heralded.cancel()
    assert heralded.state is LeaseState.CANCELLED


def test_cancel_from_terminal_state_raises():
    lease = make_lease()
    lease.mark_heralded(at=1.0, fidelity=0.99)
    lease.consume()
    with pytest.raises(ValueError):
        lease.cancel()


def test_is_fresh_true_within_bound():
    lease = make_lease(freshness_bound_s=5.0)
    lease.mark_heralded(at=1.0, fidelity=0.99)
    assert lease.is_fresh(now=5.0) is True


def test_is_fresh_false_after_bound():
    lease = make_lease(freshness_bound_s=5.0)
    lease.mark_heralded(at=1.0, fidelity=0.99)
    assert lease.is_fresh(now=7.0) is False


def test_is_fresh_false_if_never_heralded():
    lease = make_lease()
    assert lease.is_fresh(now=1.0) is False
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/entities/test_lease.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.entities.lease'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/entities/lease.py
"""EntanglementLease entity: lifecycle
requested -> heralded -> (consumed | expired | cancelled), exactly one
terminal state (design spec §5)."""

from dataclasses import dataclass
from enum import Enum

from qsim.entities.module import PathId, PortId


class LeaseState(Enum):
    REQUESTED = "requested"
    HERALDED = "heralded"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


TERMINAL_LEASE_STATES = frozenset(
    {LeaseState.CONSUMED, LeaseState.EXPIRED, LeaseState.CANCELLED}
)


@dataclass
class EntanglementLease:
    lease_id: str
    endpoints: tuple[PortId, PortId]
    path_id: PathId
    created_at: float
    freshness_bound_s: float
    fidelity_at_herald: float | None = None
    heralded_at: float | None = None
    state: LeaseState = LeaseState.REQUESTED
    retry_count: int = 0

    def mark_heralded(self, at: float, fidelity: float) -> None:
        """Transition requested -> heralded. Illegal from any other state."""
        if self.state is not LeaseState.REQUESTED:
            raise ValueError(
                f"lease {self.lease_id} cannot be heralded from state {self.state}"
            )
        self.heralded_at = at
        self.fidelity_at_herald = fidelity
        self.state = LeaseState.HERALDED

    def consume(self) -> None:
        """Transition heralded -> consumed. Illegal unless currently
        heralded (rejects double consumption and consumption of an
        expired, cancelled, or never-heralded lease)."""
        if self.state is not LeaseState.HERALDED:
            raise ValueError(
                f"lease {self.lease_id} cannot be consumed from state {self.state}"
            )
        self.state = LeaseState.CONSUMED

    def expire(self) -> None:
        """Transition (requested|heralded) -> expired. Illegal once the
        lease has already reached a terminal state."""
        if self.state in TERMINAL_LEASE_STATES:
            raise ValueError(
                f"lease {self.lease_id} cannot expire from terminal state {self.state}"
            )
        self.state = LeaseState.EXPIRED

    def cancel(self) -> None:
        """Transition (requested|heralded) -> cancelled — the round-bound
        (S0) disposition of the §5 failure-cleanup cascade. Illegal once
        the lease has already reached a terminal state."""
        if self.state in TERMINAL_LEASE_STATES:
            raise ValueError(
                f"lease {self.lease_id} cannot be cancelled from terminal state {self.state}"
            )
        self.state = LeaseState.CANCELLED

    def is_fresh(self, now: float) -> bool:
        """True iff a heralded, unconsumed lease is still within its
        freshness bound at `now` — the pooling-policy (pre-generation)
        disposition check of the §5 failure-cleanup cascade / §8.2 pool
        maintenance: fresh leases return to the pool untouched (no state
        transition), stale ones are expired via `expire()`."""
        if self.state is not LeaseState.HERALDED or self.heralded_at is None:
            return False
        return (now - self.heralded_at) <= self.freshness_bound_s
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/entities/test_lease.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/entities/lease.py tests/entities/test_lease.py
git commit -m "feat: add LeaseState and EntanglementLease lifecycle"
```

### Task 4: RoundState / SyndromeRound

**Files:**
- Create: `qsim/entities/round.py`
- Test: `tests/entities/test_round.py`

**Interfaces:**
- Consumes: none from other entity files (stdlib only).
- Produces: `RoundState` (Enum: `PENDING`, `ADMITTED`, `DEFERRED`, `DROPPED`, `COMPLETED_IN_DEADLINE`, `COMPLETED_LATE`, `FAILED`), `TERMINAL_ROUND_STATES: frozenset[RoundState]`, `SyndromeRound` (dataclass: `round_id: str`, `lease_ids: list[str]`, `qubit_ids: list[str]`, `arrival_time: float`, `deadline: float`, `retry_ordinal: int = 0`, `state: RoundState = RoundState.PENDING`) with task-local methods `admit() -> None`, `defer() -> None`, `drop() -> None`, `complete_in_deadline() -> None`, `complete_late() -> None`, `fail() -> None`, `is_terminal() -> bool`.

- [ ] **Step 1: Write the failing test**
```python
# tests/entities/test_round.py
import pytest

from qsim.entities.round import RoundState, SyndromeRound


def make_round() -> SyndromeRound:
    return SyndromeRound(
        round_id="round-1",
        lease_ids=["lease-1", "lease-2"],
        qubit_ids=["q-1", "q-2"],
        arrival_time=0.0,
        deadline=10.0,
    )


def test_round_starts_pending():
    r = make_round()
    assert r.state is RoundState.PENDING
    assert r.retry_ordinal == 0


def test_admit_from_pending_succeeds():
    r = make_round()
    r.admit()
    assert r.state is RoundState.ADMITTED


def test_admit_twice_raises():
    r = make_round()
    r.admit()
    with pytest.raises(ValueError):
        r.admit()


def test_defer_from_pending_succeeds():
    r = make_round()
    r.defer()
    assert r.state is RoundState.DEFERRED


def test_drop_from_pending_succeeds():
    r = make_round()
    r.drop()
    assert r.state is RoundState.DROPPED


def test_defer_from_non_pending_raises():
    r = make_round()
    r.admit()
    with pytest.raises(ValueError):
        r.defer()


def test_complete_in_deadline_requires_admitted():
    r = make_round()
    with pytest.raises(ValueError):
        r.complete_in_deadline()
    r.admit()
    r.complete_in_deadline()
    assert r.state is RoundState.COMPLETED_IN_DEADLINE


def test_complete_late_requires_admitted():
    r = make_round()
    with pytest.raises(ValueError):
        r.complete_late()
    r.admit()
    r.complete_late()
    assert r.state is RoundState.COMPLETED_LATE


def test_fail_requires_admitted():
    r = make_round()
    with pytest.raises(ValueError):
        r.fail()
    r.admit()
    r.fail()
    assert r.state is RoundState.FAILED


def test_is_terminal_for_terminal_and_nonterminal_states():
    pending = make_round()
    assert pending.is_terminal() is False

    admitted = make_round()
    admitted.admit()
    assert admitted.is_terminal() is False

    dropped = make_round()
    dropped.drop()
    assert dropped.is_terminal() is True

    failed = make_round()
    failed.admit()
    failed.fail()
    assert failed.is_terminal() is True
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/entities/test_round.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.entities.round'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/entities/round.py
"""SyndromeRound entity: lifecycle pending -> (admitted | deferred |
dropped); admitted -> (completed_in_deadline | completed_late | failed)
(design spec §5). `fail()` is the transition that triggers the §5
failure-cleanup cascade on the round's resources — decoder jobs, switch
reservations, and leases — each disposed via its own entity's method
elsewhere in this package; orchestrating the cascade itself is core/'s job."""

from dataclasses import dataclass
from enum import Enum


class RoundState(Enum):
    PENDING = "pending"
    ADMITTED = "admitted"
    DEFERRED = "deferred"
    DROPPED = "dropped"
    COMPLETED_IN_DEADLINE = "completed_in_deadline"
    COMPLETED_LATE = "completed_late"
    FAILED = "failed"


TERMINAL_ROUND_STATES = frozenset(
    {
        RoundState.DROPPED,
        RoundState.COMPLETED_IN_DEADLINE,
        RoundState.COMPLETED_LATE,
        RoundState.FAILED,
    }
)


@dataclass
class SyndromeRound:
    round_id: str
    lease_ids: list[str]
    qubit_ids: list[str]
    arrival_time: float
    deadline: float
    retry_ordinal: int = 0
    state: RoundState = RoundState.PENDING

    def admit(self) -> None:
        """Transition pending -> admitted. Illegal from any other state."""
        if self.state is not RoundState.PENDING:
            raise ValueError(
                f"round {self.round_id} cannot be admitted from state {self.state}"
            )
        self.state = RoundState.ADMITTED

    def defer(self) -> None:
        """Transition pending -> deferred. Illegal from any other state."""
        if self.state is not RoundState.PENDING:
            raise ValueError(
                f"round {self.round_id} cannot be deferred from state {self.state}"
            )
        self.state = RoundState.DEFERRED

    def drop(self) -> None:
        """Transition pending -> dropped. Illegal from any other state."""
        if self.state is not RoundState.PENDING:
            raise ValueError(
                f"round {self.round_id} cannot be dropped from state {self.state}"
            )
        self.state = RoundState.DROPPED

    def complete_in_deadline(self) -> None:
        """Transition admitted -> completed_in_deadline. Illegal unless
        currently admitted."""
        if self.state is not RoundState.ADMITTED:
            raise ValueError(
                f"round {self.round_id} cannot complete-in-deadline from state {self.state}"
            )
        self.state = RoundState.COMPLETED_IN_DEADLINE

    def complete_late(self) -> None:
        """Transition admitted -> completed_late. Illegal unless currently
        admitted."""
        if self.state is not RoundState.ADMITTED:
            raise ValueError(
                f"round {self.round_id} cannot complete-late from state {self.state}"
            )
        self.state = RoundState.COMPLETED_LATE

    def fail(self) -> None:
        """Transition admitted -> failed. Illegal unless currently
        admitted."""
        if self.state is not RoundState.ADMITTED:
            raise ValueError(
                f"round {self.round_id} cannot fail from state {self.state}"
            )
        self.state = RoundState.FAILED

    def is_terminal(self) -> bool:
        """True once the round has reached any terminal state."""
        return self.state in TERMINAL_ROUND_STATES
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/entities/test_round.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/entities/round.py tests/entities/test_round.py
git commit -m "feat: add RoundState and SyndromeRound lifecycle"
```

### Task 5: DecoderJob

**Files:**
- Create: `qsim/entities/decoder.py`
- Test: `tests/entities/test_decoder.py`

**Interfaces:**
- Consumes: none from other entity files (stdlib only).
- Produces: `DecoderJob` (dataclass: `job_id: str`, `round_id: str`, `priority: int`, `enqueue_time: float`, `dequeue_time: float | None = None`, `completion_time: float | None = None`, plus task-local field `cancelled_at: float | None = None` — not in the frozen contract's field list, added here to represent the §5 cascade's decoder-job-cancellation disposition without overloading `completion_time`) with task-local methods `dequeue(at: float) -> None`, `complete(at: float) -> None`, `cancel(at: float) -> None`.

- [ ] **Step 1: Write the failing test**
```python
# tests/entities/test_decoder.py
import pytest

from qsim.entities.decoder import DecoderJob


def make_job() -> DecoderJob:
    return DecoderJob(job_id="job-1", round_id="round-1", priority=0, enqueue_time=0.0)


def test_decoder_job_starts_enqueued_only():
    job = make_job()
    assert job.dequeue_time is None
    assert job.completion_time is None
    assert job.cancelled_at is None


def test_dequeue_sets_time():
    job = make_job()
    job.dequeue(at=1.0)
    assert job.dequeue_time == 1.0


def test_dequeue_twice_raises():
    job = make_job()
    job.dequeue(at=1.0)
    with pytest.raises(ValueError):
        job.dequeue(at=2.0)


def test_complete_requires_dequeue_first():
    job = make_job()
    with pytest.raises(ValueError):
        job.complete(at=2.0)


def test_complete_after_dequeue_succeeds():
    job = make_job()
    job.dequeue(at=1.0)
    job.complete(at=2.0)
    assert job.completion_time == 2.0


def test_complete_twice_raises():
    job = make_job()
    job.dequeue(at=1.0)
    job.complete(at=2.0)
    with pytest.raises(ValueError):
        job.complete(at=3.0)


def test_cancel_before_dequeue_succeeds():
    job = make_job()
    job.cancel(at=1.0)
    assert job.cancelled_at == 1.0


def test_cancel_after_completion_raises():
    job = make_job()
    job.dequeue(at=1.0)
    job.complete(at=2.0)
    with pytest.raises(ValueError):
        job.cancel(at=3.0)


def test_cancel_twice_raises():
    job = make_job()
    job.cancel(at=1.0)
    with pytest.raises(ValueError):
        job.cancel(at=2.0)


def test_complete_after_cancel_raises():
    job = make_job()
    job.dequeue(at=1.0)
    job.cancel(at=2.0)
    with pytest.raises(ValueError):
        job.complete(at=3.0)


def test_dequeue_after_cancel_raises():
    job = make_job()
    job.cancel(at=1.0)
    with pytest.raises(ValueError):
        job.dequeue(at=2.0)
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/entities/test_decoder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.entities.decoder'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/entities/decoder.py
"""DecoderJob entity: service demand, priority, and enqueue/dequeue/
completion timestamps (design spec §5). Adds a task-local `cancelled_at`
timestamp (not in the frozen interface contract's field list for
DecoderJob) to represent the §5 failure-cleanup cascade's decoder-job
cancellation disposition."""

from dataclasses import dataclass


@dataclass
class DecoderJob:
    job_id: str
    round_id: str
    priority: int
    enqueue_time: float
    dequeue_time: float | None = None
    completion_time: float | None = None
    cancelled_at: float | None = None  # task-local addition; see module docstring

    def dequeue(self, at: float) -> None:
        """Record dequeue time. Illegal if already dequeued, completed, or
        cancelled."""
        if self.dequeue_time is not None:
            raise ValueError(f"job {self.job_id} already dequeued at {self.dequeue_time}")
        if self.completion_time is not None:
            raise ValueError(f"job {self.job_id} already completed")
        if self.cancelled_at is not None:
            raise ValueError(f"job {self.job_id} already cancelled")
        self.dequeue_time = at

    def complete(self, at: float) -> None:
        """Record completion time. Illegal unless dequeued first, and
        illegal if already completed or cancelled (rejects double
        completion)."""
        if self.dequeue_time is None:
            raise ValueError(f"job {self.job_id} cannot complete before being dequeued")
        if self.completion_time is not None:
            raise ValueError(f"job {self.job_id} already completed at {self.completion_time}")
        if self.cancelled_at is not None:
            raise ValueError(f"job {self.job_id} already cancelled")
        self.completion_time = at

    def cancel(self, at: float) -> None:
        """Round-cleanup-cascade disposition (design spec §5): cancel this
        job on round failure/cancellation, whether or not it has already
        been dequeued. Illegal if already completed or already cancelled."""
        if self.completion_time is not None:
            raise ValueError(f"job {self.job_id} already completed, cannot cancel")
        if self.cancelled_at is not None:
            raise ValueError(f"job {self.job_id} already cancelled at {self.cancelled_at}")
        self.cancelled_at = at
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/entities/test_decoder.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/entities/decoder.py tests/entities/test_decoder.py
git commit -m "feat: add DecoderJob lifecycle with cancellation disposition"
```

### Task 6: ReservationState / SwitchPathReservation

**Files:**
- Create: `qsim/entities/reservation.py`
- Test: `tests/entities/test_reservation.py`

**Interfaces:**
- Consumes: `PathId` from `qsim.entities.module` (Task 1).
- Produces: `ReservationState` (Enum: `ACQUIRED`, `CONFIGURING`, `ACTIVE`, `RELEASED`), `SwitchPathReservation` (dataclass: `path_id: PathId`, `holder_id: str`, `acquired_at: float`, `released_at: float | None = None`, `state: ReservationState = ReservationState.ACQUIRED`) with task-local methods `configure() -> None`, `activate() -> None`, `release(at: float) -> None`.

- [ ] **Step 1: Write the failing test**
```python
# tests/entities/test_reservation.py
import pytest

from qsim.entities.module import PortId, make_path_id
from qsim.entities.reservation import ReservationState, SwitchPathReservation


def make_reservation() -> SwitchPathReservation:
    a = PortId("mod-a", 0)
    b = PortId("mod-b", 0)
    return SwitchPathReservation(
        path_id=make_path_id(a, b), holder_id="round-1", acquired_at=0.0
    )


def test_reservation_starts_acquired():
    r = make_reservation()
    assert r.state is ReservationState.ACQUIRED
    assert r.released_at is None


def test_configure_from_acquired_succeeds():
    r = make_reservation()
    r.configure()
    assert r.state is ReservationState.CONFIGURING


def test_configure_twice_raises():
    r = make_reservation()
    r.configure()
    with pytest.raises(ValueError):
        r.configure()


def test_activate_requires_configuring():
    r = make_reservation()
    with pytest.raises(ValueError):
        r.activate()
    r.configure()
    r.activate()
    assert r.state is ReservationState.ACTIVE


def test_activate_twice_raises():
    r = make_reservation()
    r.configure()
    r.activate()
    with pytest.raises(ValueError):
        r.activate()


def test_release_from_acquired_succeeds():
    # Round cancelled while reservation was still being negotiated.
    r = make_reservation()
    r.release(at=1.0)
    assert r.state is ReservationState.RELEASED
    assert r.released_at == 1.0


def test_release_from_configuring_succeeds():
    r = make_reservation()
    r.configure()
    r.release(at=1.0)
    assert r.state is ReservationState.RELEASED


def test_release_from_active_succeeds():
    r = make_reservation()
    r.configure()
    r.activate()
    r.release(at=2.0)
    assert r.state is ReservationState.RELEASED


def test_release_twice_raises():
    r = make_reservation()
    r.release(at=1.0)
    with pytest.raises(ValueError):
        r.release(at=2.0)


def test_configure_after_release_raises():
    r = make_reservation()
    r.release(at=1.0)
    with pytest.raises(ValueError):
        r.configure()
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/entities/test_reservation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.entities.reservation'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/entities/reservation.py
"""SwitchPathReservation entity: lifecycle
acquired -> configuring -> active -> released (design spec §7). Release is
also the §5 failure-cleanup cascade's disposition for reservations held on
behalf of a failed or cancelled round, and can occur directly from
`acquired` or `configuring` if the round is cancelled before heralding
attempts ever start."""

from dataclasses import dataclass
from enum import Enum

from qsim.entities.module import PathId


class ReservationState(Enum):
    ACQUIRED = "acquired"
    CONFIGURING = "configuring"
    ACTIVE = "active"
    RELEASED = "released"


@dataclass
class SwitchPathReservation:
    path_id: PathId
    holder_id: str  # round_id or lease_id
    acquired_at: float
    released_at: float | None = None
    state: ReservationState = ReservationState.ACQUIRED

    def configure(self) -> None:
        """Transition acquired -> configuring. Illegal from any other
        state."""
        if self.state is not ReservationState.ACQUIRED:
            raise ValueError(
                f"reservation on {self.path_id} cannot configure from state {self.state}"
            )
        self.state = ReservationState.CONFIGURING

    def activate(self) -> None:
        """Transition configuring -> active. Illegal from any other
        state."""
        if self.state is not ReservationState.CONFIGURING:
            raise ValueError(
                f"reservation on {self.path_id} cannot activate from state {self.state}"
            )
        self.state = ReservationState.ACTIVE

    def release(self, at: float) -> None:
        """Transition (acquired | configuring | active) -> released, at
        the first of heralding success, attempt-window/deadline expiry, or
        round cancellation (design spec §7). Illegal if already released
        (rejects a reservation being released twice, which would otherwise
        mask a resource leak)."""
        if self.state is ReservationState.RELEASED:
            raise ValueError(
                f"reservation on {self.path_id} already released at {self.released_at}"
            )
        self.released_at = at
        self.state = ReservationState.RELEASED
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/entities/test_reservation.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/entities/reservation.py tests/entities/test_reservation.py
git commit -m "feat: add ReservationState and SwitchPathReservation lifecycle"
```

### Task 7: CalibrationEpoch

**Files:**
- Create: `qsim/entities/calibration.py`
- Test: `tests/entities/test_calibration.py`

**Interfaces:**
- Consumes: `CoherenceClass` from `qsim.entities.qubit` (Task 2); `PathId`, `make_path_id`, `PortId` from `qsim.entities.module` (Task 1).
- Produces: `CalibrationEpoch` (frozen dataclass: `epoch_id: str`, `decay_rate_per_class: dict[CoherenceClass, float]`, `memory_access_channel_s: float`, `memory_access_wear_rate: float`, `heralding_p_per_path: dict[PathId, float]`, `heralded_fidelity_per_path: dict[PathId, float]`, `round_success_logistic_midpoint: float`, `round_success_logistic_slope: float`, `round_success_slack_penalty_per_s: float`, `decoder_service_rate: float`).

- [ ] **Step 1: Write the failing test**
```python
# tests/entities/test_calibration.py
import dataclasses

import pytest

from qsim.entities.calibration import CalibrationEpoch
from qsim.entities.module import PortId, make_path_id
from qsim.entities.qubit import CoherenceClass


def make_epoch() -> CalibrationEpoch:
    a = PortId("mod-a", 0)
    b = PortId("mod-b", 0)
    path = make_path_id(a, b)
    return CalibrationEpoch(
        epoch_id="epoch-1",
        decay_rate_per_class={
            CoherenceClass.MESSENGER: 0.5,
            CoherenceClass.MEMORY: 0.01,
        },
        memory_access_channel_s=0.001,
        memory_access_wear_rate=0.002,
        heralding_p_per_path={path: 0.3},
        heralded_fidelity_per_path={path: 0.98},
        round_success_logistic_midpoint=0.9,
        round_success_logistic_slope=10.0,
        round_success_slack_penalty_per_s=0.05,
        decoder_service_rate=100.0,
    )


def test_calibration_epoch_holds_fields():
    epoch = make_epoch()
    assert epoch.epoch_id == "epoch-1"
    assert epoch.decay_rate_per_class[CoherenceClass.MEMORY] == 0.01
    assert epoch.decoder_service_rate == 100.0


def test_calibration_epoch_is_immutable():
    epoch = make_epoch()
    with pytest.raises(dataclasses.FrozenInstanceError):
        epoch.decoder_service_rate = 50.0  # type: ignore[misc]


def test_calibration_epoch_maps_keyed_by_domain_types():
    a = PortId("mod-a", 0)
    b = PortId("mod-b", 0)
    epoch = make_epoch()
    assert epoch.heralding_p_per_path[make_path_id(b, a)] == 0.3
    assert epoch.heralded_fidelity_per_path[make_path_id(a, b)] == 0.98
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/entities/test_calibration.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.entities.calibration'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/entities/calibration.py
"""CalibrationEpoch entity: a versioned, immutable parameter snapshot the
scheduler and model surfaces consult (design spec §5, §6)."""

from dataclasses import dataclass

from qsim.entities.module import PathId
from qsim.entities.qubit import CoherenceClass


@dataclass(frozen=True)
class CalibrationEpoch:
    epoch_id: str
    decay_rate_per_class: dict[CoherenceClass, float]
    memory_access_channel_s: float
    memory_access_wear_rate: float
    heralding_p_per_path: dict[PathId, float]
    heralded_fidelity_per_path: dict[PathId, float]
    round_success_logistic_midpoint: float
    round_success_logistic_slope: float
    round_success_slack_penalty_per_s: float
    decoder_service_rate: float
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/entities/test_calibration.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/entities/calibration.py tests/entities/test_calibration.py
git commit -m "feat: add CalibrationEpoch entity"
```

### Task 8: PauliFrameToken

**Files:**
- Create: `qsim/entities/pauli_frame.py`
- Test: `tests/entities/test_pauli_frame.py`

**Interfaces:**
- Consumes: none.
- Produces: `PauliFrameToken` (dataclass: `token_id: str`, `created_at: float`).

- [ ] **Step 1: Write the failing test**
```python
# tests/entities/test_pauli_frame.py
from qsim.entities.pauli_frame import PauliFrameToken


def test_pauli_frame_token_holds_fields():
    token = PauliFrameToken(token_id="pft-1", created_at=3.5)
    assert token.token_id == "pft-1"
    assert token.created_at == 3.5


def test_pauli_frame_tokens_with_equal_fields_are_equal():
    a = PauliFrameToken(token_id="pft-1", created_at=3.5)
    b = PauliFrameToken(token_id="pft-1", created_at=3.5)
    assert a == b


def test_pauli_frame_tokens_with_different_ids_are_not_equal():
    a = PauliFrameToken(token_id="pft-1", created_at=3.5)
    b = PauliFrameToken(token_id="pft-2", created_at=3.5)
    assert a != b
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/entities/test_pauli_frame.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.entities.pauli_frame'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/entities/pauli_frame.py
"""PauliFrameToken entity: deferred-correction marker. V1: counted, not
semantically modeled — exists so fast-path pressure relief is observable
later (design spec §5)."""

from dataclasses import dataclass


@dataclass
class PauliFrameToken:
    token_id: str
    created_at: float
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/entities/test_pauli_frame.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/entities/pauli_frame.py tests/entities/test_pauli_frame.py
git commit -m "feat: add PauliFrameToken entity"
```

---

## Section 3 of 8 — models/ (Protocols + v1 analytic implementations)

### Task 1: Model protocols and AccessCost

**Files:**
- Create: `qsim/models/__init__.py`
- Create: `qsim/models/protocols.py`
- Test: `tests/models/test_protocols.py`

**Interfaces:**
- Consumes: `Draw` (`qsim.core.rng`, field `u: float`); `CalibrationEpoch`, `CoherenceClass`, `DecoderJob`, `PathId`, `QubitHandle` (`qsim.entities`)
- Produces:
  - `AccessCost` — frozen dataclass, fields `electron_channel_s: float`, `retention_factor: float`
  - `DecayModel(Protocol)` — `retention(self, age_s: float, coherence: CoherenceClass, epoch: CalibrationEpoch) -> float`
  - `MemoryAccessModel(Protocol)` — `access_cost(self, qubit: QubitHandle, epoch: CalibrationEpoch) -> AccessCost`
  - `HeraldingModel(Protocol)` — `success_probability(self, path: PathId, epoch: CalibrationEpoch) -> float`; `heralded_fidelity(self, path: PathId, epoch: CalibrationEpoch) -> float`
  - `RoundSuccessModel(Protocol)` — `success_probability(self, lease_fidelities: Sequence[float], memory_retentions: Sequence[float], decoder_latency_s: float, deadline_slack_s: float) -> float` (note: **no** `epoch` parameter — §8.1 reuses this exact surface for admission-control projection over purely numeric projected inputs)
  - `DecoderServiceModel(Protocol)` — `service_time_s(self, job: DecoderJob, backlog: int, draw: Draw) -> float` (note: **no** `epoch` parameter); `expected_service_time_s(self, backlog: int, epoch: CalibrationEpoch) -> float`

- [ ] **Step 1: Write the failing test**
```python
# tests/models/test_protocols.py
import inspect
from dataclasses import FrozenInstanceError

import pytest

from qsim.models.protocols import (
    AccessCost, DecayModel, MemoryAccessModel, HeraldingModel,
    RoundSuccessModel, DecoderServiceModel,
)


def test_access_cost_holds_electron_channel_and_retention_fields():
    cost = AccessCost(electron_channel_s=0.002, retention_factor=0.95)
    assert cost.electron_channel_s == 0.002
    assert cost.retention_factor == 0.95


def test_access_cost_is_frozen():
    cost = AccessCost(electron_channel_s=0.002, retention_factor=0.95)
    with pytest.raises(FrozenInstanceError):
        cost.retention_factor = 1.0


@pytest.mark.parametrize("protocol_cls,method_names", [
    (DecayModel, ["retention"]),
    (MemoryAccessModel, ["access_cost"]),
    (HeraldingModel, ["success_probability", "heralded_fidelity"]),
    (RoundSuccessModel, ["success_probability"]),
    (DecoderServiceModel, ["service_time_s", "expected_service_time_s"]),
])
def test_protocol_declares_expected_methods(protocol_cls, method_names):
    for name in method_names:
        assert hasattr(protocol_cls, name), f"{protocol_cls.__name__} missing {name}"
        assert inspect.isfunction(getattr(protocol_cls, name))


def test_round_success_protocol_has_no_epoch_parameter():
    sig = inspect.signature(RoundSuccessModel.success_probability)
    assert "epoch" not in sig.parameters


def test_decoder_service_time_s_protocol_has_no_epoch_parameter():
    sig = inspect.signature(DecoderServiceModel.service_time_s)
    assert "epoch" not in sig.parameters
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/models/test_protocols.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.models.protocols'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/models/__init__.py
```
```python
# qsim/models/protocols.py
"""Model surface protocols and shared value types (spec sec 6, verbatim).

All model surfaces are pure functions of their arguments plus a CalibrationEpoch:
no mutable state, no random draws. Where a sample is unavoidable
(DecoderServiceModel.service_time_s), the engine supplies a keyed Draw (sec 10);
the model never draws itself.

RoundSuccessModel.success_probability and DecoderServiceModel.service_time_s
deliberately take no CalibrationEpoch: sec 8.1 reuses success_probability for
admission-control projection over purely numeric projected inputs, and
service_time_s is called per decode attempt without epoch plumbing. Their v1
implementations are config-parameterized at construction time instead (see
models/round_success.py, models/decoder_service.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from qsim.core.rng import Draw
from qsim.entities import CalibrationEpoch, CoherenceClass, DecoderJob, PathId, QubitHandle


@dataclass(frozen=True)
class AccessCost:
    electron_channel_s: float
    retention_factor: float


class DecayModel(Protocol):
    def retention(self, age_s: float, coherence: CoherenceClass,
                  epoch: CalibrationEpoch) -> float:
        """Multiplicative retention in [0,1].
        fidelity(t) = fidelity_at_herald * retention(t - t_herald, class, epoch)."""
        ...


class MemoryAccessModel(Protocol):
    def access_cost(self, qubit: QubitHandle,
                    epoch: CalibrationEpoch) -> AccessCost:
        """Composes AFTER passive decay is applied up to the access instant:
        f_after = f_decayed_to_now * retention_factor."""
        ...


class HeraldingModel(Protocol):
    def success_probability(self, path: PathId,
                            epoch: CalibrationEpoch) -> float:
        """Per-attempt heralding success probability."""
        ...

    def heralded_fidelity(self, path: PathId,
                          epoch: CalibrationEpoch) -> float:
        """Initial fidelity of a successfully heralded pair on this path."""
        ...


class RoundSuccessModel(Protocol):
    def success_probability(self, lease_fidelities: Sequence[float],
                            memory_retentions: Sequence[float],
                            decoder_latency_s: float,
                            deadline_slack_s: float) -> float:
        """Round success given inputs at execution time. decoder_latency_s is the
        raw duration; deadline_slack_s = deadline - completion time (may be
        negative)."""
        ...


class DecoderServiceModel(Protocol):
    def service_time_s(self, job: DecoderJob, backlog: int,
                       draw: Draw) -> float:
        """Sampled service time; draw is an engine-supplied keyed source."""
        ...

    def expected_service_time_s(self, backlog: int,
                                epoch: CalibrationEpoch) -> float:
        """Closed-form mean service time at the given backlog, no draw."""
        ...
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/models/test_protocols.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/models/__init__.py qsim/models/protocols.py tests/models/test_protocols.py
git commit -m "feat: add models protocols and AccessCost (spec §6, verbatim)"
```

### Task 2: DecayModel v1 and no-decay control

**Files:**
- Create: `qsim/models/decay.py`
- Test: `tests/models/test_decay.py`

**Interfaces:**
- Consumes: `CalibrationEpoch` (field `decay_rate_per_class: dict[CoherenceClass, float]`), `CoherenceClass` (`qsim.entities`); `DecayModel` Protocol shape (`qsim.models.protocols`)
- Produces:
  - `ExponentialDecayModel()` — no constructor args; `retention(self, age_s: float, coherence: CoherenceClass, epoch: CalibrationEpoch) -> float`
  - `NoDecayModel()` — no constructor args; `retention(self, age_s: float, coherence: CoherenceClass, epoch: CalibrationEpoch) -> float` (always `1.0`)

- [ ] **Step 1: Write the failing test**
```python
# tests/models/test_decay.py
import math

import pytest

from qsim.entities import CalibrationEpoch, CoherenceClass
from qsim.models.decay import ExponentialDecayModel, NoDecayModel


def _epoch(decay_rate_per_class):
    return CalibrationEpoch(
        epoch_id="e0",
        decay_rate_per_class=decay_rate_per_class,
        memory_access_channel_s=0.0,
        memory_access_wear_rate=0.0,
        heralding_p_per_path={},
        heralded_fidelity_per_path={},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=1.0,
        round_success_slack_penalty_per_s=0.0,
        decoder_service_rate=1.0,
    )


def test_exponential_decay_retention_at_age_zero_is_one():
    epoch = _epoch({CoherenceClass.MESSENGER: 10.0, CoherenceClass.MEMORY: 1.0})
    model = ExponentialDecayModel()
    assert model.retention(0.0, CoherenceClass.MESSENGER, epoch) == pytest.approx(1.0)


def test_exponential_decay_retention_at_half_life_is_one_half():
    rate = 2.0
    half_life = math.log(2) / rate
    epoch = _epoch({CoherenceClass.MESSENGER: rate, CoherenceClass.MEMORY: rate})
    model = ExponentialDecayModel()
    assert model.retention(half_life, CoherenceClass.MESSENGER, epoch) == pytest.approx(0.5, rel=1e-9)


def test_exponential_decay_uses_per_coherence_class_rate():
    epoch = _epoch({CoherenceClass.MESSENGER: 1.0, CoherenceClass.MEMORY: 5.0})
    model = ExponentialDecayModel()
    age = 1.0
    messenger_retention = model.retention(age, CoherenceClass.MESSENGER, epoch)
    memory_retention = model.retention(age, CoherenceClass.MEMORY, epoch)
    assert messenger_retention == pytest.approx(math.exp(-1.0))
    assert memory_retention == pytest.approx(math.exp(-5.0))
    assert messenger_retention != memory_retention


def test_no_decay_control_is_always_one():
    epoch = _epoch({CoherenceClass.MESSENGER: 999.0, CoherenceClass.MEMORY: 999.0})
    model = NoDecayModel()
    assert model.retention(0.0, CoherenceClass.MESSENGER, epoch) == 1.0
    assert model.retention(1e6, CoherenceClass.MEMORY, epoch) == 1.0
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/models/test_decay.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.models.decay'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/models/decay.py
"""v1 DecayModel implementations (spec sec 6): exponential decay and the
required no-decay control."""
from __future__ import annotations

import math

from qsim.entities import CalibrationEpoch, CoherenceClass


class ExponentialDecayModel:
    """retention(age) = exp(-decay_rate_per_class[coherence] * age_s)."""

    def retention(self, age_s: float, coherence: CoherenceClass,
                  epoch: CalibrationEpoch) -> float:
        rate = epoch.decay_rate_per_class[coherence]
        return math.exp(-rate * age_s)


class NoDecayModel:
    """Required control (spec sec 6): retention identically 1, regardless of
    age, coherence class, or epoch -- neutralizes the decay surface entirely."""

    def retention(self, age_s: float, coherence: CoherenceClass,
                  epoch: CalibrationEpoch) -> float:
        return 1.0
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/models/test_decay.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/models/decay.py tests/models/test_decay.py
git commit -m "feat: add ExponentialDecayModel and NoDecayModel control"
```

### Task 3: MemoryAccessModel v1 and zero-cost control

**Files:**
- Create: `qsim/models/memory_access.py`
- Test: `tests/models/test_memory_access.py`

**Interfaces:**
- Consumes: `CalibrationEpoch` (fields `memory_access_channel_s: float`, `memory_access_wear_rate: float`), `QubitHandle` (field `access_count: int`), `CoherenceClass` (`qsim.entities`); `AccessCost`, `MemoryAccessModel` Protocol shape (`qsim.models.protocols`)
- Produces:
  - `LinearMemoryAccessModel()` — no constructor args; `access_cost(self, qubit: QubitHandle, epoch: CalibrationEpoch) -> AccessCost`
  - `ZeroCostMemoryAccessModel()` — no constructor args; `access_cost(self, qubit: QubitHandle, epoch: CalibrationEpoch) -> AccessCost` (always `AccessCost(electron_channel_s=0.0, retention_factor=1.0)`)

- [ ] **Step 1: Write the failing test**
```python
# tests/models/test_memory_access.py
import pytest

from qsim.entities import CalibrationEpoch, CoherenceClass, QubitHandle
from qsim.models.memory_access import LinearMemoryAccessModel, ZeroCostMemoryAccessModel


def _epoch(channel_s, wear_rate):
    return CalibrationEpoch(
        epoch_id="e0",
        decay_rate_per_class={CoherenceClass.MESSENGER: 1.0, CoherenceClass.MEMORY: 1.0},
        memory_access_channel_s=channel_s,
        memory_access_wear_rate=wear_rate,
        heralding_p_per_path={},
        heralded_fidelity_per_path={},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=1.0,
        round_success_slack_penalty_per_s=0.0,
        decoder_service_rate=1.0,
    )


def _qubit(epoch, access_count):
    return QubitHandle(qubit_id="q0", module_id="m0",
                       coherence_class=CoherenceClass.MEMORY,
                       calibration_epoch=epoch, access_count=access_count)


def test_linear_memory_access_no_prior_accesses_is_full_retention():
    epoch = _epoch(channel_s=0.002, wear_rate=0.1)
    model = LinearMemoryAccessModel()
    cost = model.access_cost(_qubit(epoch, access_count=0), epoch)
    assert cost.electron_channel_s == pytest.approx(0.002)
    assert cost.retention_factor == pytest.approx(1.0)


def test_linear_memory_access_wears_linearly_with_access_count():
    epoch = _epoch(channel_s=0.002, wear_rate=0.1)
    model = LinearMemoryAccessModel()
    cost = model.access_cost(_qubit(epoch, access_count=3), epoch)
    assert cost.retention_factor == pytest.approx(0.7)


def test_linear_memory_access_retention_floors_at_zero():
    epoch = _epoch(channel_s=0.002, wear_rate=0.5)
    model = LinearMemoryAccessModel()
    cost = model.access_cost(_qubit(epoch, access_count=100), epoch)
    assert cost.retention_factor == 0.0


def test_zero_cost_control_is_always_free_and_full_retention():
    epoch = _epoch(channel_s=0.002, wear_rate=0.9)
    model = ZeroCostMemoryAccessModel()
    for access_count in (0, 1, 1000):
        cost = model.access_cost(_qubit(epoch, access_count=access_count), epoch)
        assert cost.electron_channel_s == 0.0
        assert cost.retention_factor == 1.0
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/models/test_memory_access.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.models.memory_access'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/models/memory_access.py
"""v1 MemoryAccessModel implementations (spec sec 6): linear per-access wear
and the required zero-cost control."""
from __future__ import annotations

from qsim.entities import CalibrationEpoch, QubitHandle
from qsim.models.protocols import AccessCost


class LinearMemoryAccessModel:
    """Each access costs a fixed electron-channel duration and linearly wears
    retention: retention_factor = max(0.0, 1 - wear_rate * access_count).
    Floored at zero to keep retention_factor in [0,1] per sec 6's convention."""

    def access_cost(self, qubit: QubitHandle,
                    epoch: CalibrationEpoch) -> AccessCost:
        wear = epoch.memory_access_wear_rate * qubit.access_count
        retention_factor = max(0.0, 1.0 - wear)
        return AccessCost(electron_channel_s=epoch.memory_access_channel_s,
                          retention_factor=retention_factor)


class ZeroCostMemoryAccessModel:
    """Required control (spec sec 6): free reads -- zero channel time, no
    retention loss, regardless of access history. Neutralizes the
    memory-access surface entirely."""

    def access_cost(self, qubit: QubitHandle,
                    epoch: CalibrationEpoch) -> AccessCost:
        return AccessCost(electron_channel_s=0.0, retention_factor=1.0)
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/models/test_memory_access.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/models/memory_access.py tests/models/test_memory_access.py
git commit -m "feat: add LinearMemoryAccessModel and ZeroCostMemoryAccessModel control"
```

### Task 4: HeraldingModel v1

**Files:**
- Create: `qsim/models/heralding.py`
- Test: `tests/models/test_heralding.py`

**Interfaces:**
- Consumes: `CalibrationEpoch` (fields `heralding_p_per_path: dict[PathId, float]`, `heralded_fidelity_per_path: dict[PathId, float]`), `PathId`, `PortId`, `make_path_id`, `CoherenceClass` (`qsim.entities`); `draw_uniform(run_seed: int, stream: str, key: tuple) -> float` (`qsim.core.rng`); `HeraldingModel` Protocol shape (`qsim.models.protocols`)
- Produces:
  - `BernoulliHeraldingModel()` — no constructor args; `success_probability(self, path: PathId, epoch: CalibrationEpoch) -> float`; `heralded_fidelity(self, path: PathId, epoch: CalibrationEpoch) -> float`

- [ ] **Step 1: Write the failing test**
```python
# tests/models/test_heralding.py
import pytest

from qsim.core.rng import draw_uniform
from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.models.heralding import BernoulliHeraldingModel


def _path():
    return make_path_id(PortId(module_id="m0", port_index=0),
                        PortId(module_id="m1", port_index=0))


def _epoch(p, fidelity, path):
    return CalibrationEpoch(
        epoch_id="e0",
        decay_rate_per_class={CoherenceClass.MESSENGER: 1.0, CoherenceClass.MEMORY: 1.0},
        memory_access_channel_s=0.0,
        memory_access_wear_rate=0.0,
        heralding_p_per_path={path: p},
        heralded_fidelity_per_path={path: fidelity},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=1.0,
        round_success_slack_penalty_per_s=0.0,
        decoder_service_rate=1.0,
    )


def test_success_probability_reads_epoch_table():
    path = _path()
    epoch = _epoch(p=0.37, fidelity=0.9, path=path)
    model = BernoulliHeraldingModel()
    assert model.success_probability(path, epoch) == pytest.approx(0.37)


def test_heralded_fidelity_reads_epoch_table():
    path = _path()
    epoch = _epoch(p=0.37, fidelity=0.91, path=path)
    model = BernoulliHeraldingModel()
    assert model.heralded_fidelity(path, epoch) == pytest.approx(0.91)


def test_bernoulli_success_rate_over_many_keyed_draws_matches_epoch_p():
    path = _path()
    p = 0.63
    epoch = _epoch(p=p, fidelity=0.9, path=path)
    model = BernoulliHeraldingModel()
    threshold = model.success_probability(path, epoch)

    n = 5000
    run_seed = 42
    successes = 0
    for attempt_no in range(n):
        key = ("herald", "round-x", path, attempt_no)
        u = draw_uniform(run_seed, "herald", key)
        if u < threshold:
            successes += 1

    empirical_rate = successes / n
    # 5000 Bernoulli(0.63) draws: std dev ~ sqrt(0.63*0.37/5000) ~ 0.0068;
    # 5-sigma-plus tolerance avoids flakes while still catching a wrong
    # probability being plumbed through the engine's keyed-threshold contract.
    assert empirical_rate == pytest.approx(p, abs=0.035)
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/models/test_heralding.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.models.heralding'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/models/heralding.py
"""v1 HeraldingModel implementation (spec sec 6): Bernoulli(p) per attempt,
looked up directly from the calibration epoch's per-path tables. The model
returns a probability only -- it never draws; the engine thresholds a keyed
uniform against it per sec 10's contract."""
from __future__ import annotations

from qsim.entities import CalibrationEpoch, PathId


class BernoulliHeraldingModel:
    def success_probability(self, path: PathId,
                            epoch: CalibrationEpoch) -> float:
        return epoch.heralding_p_per_path[path]

    def heralded_fidelity(self, path: PathId,
                          epoch: CalibrationEpoch) -> float:
        return epoch.heralded_fidelity_per_path[path]
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/models/test_heralding.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/models/heralding.py tests/models/test_heralding.py
git commit -m "feat: add BernoulliHeraldingModel"
```

### Task 5: RoundSuccessModel v1

**Files:**
- Create: `qsim/models/round_success.py`
- Test: `tests/models/test_round_success.py`

**Interfaces:**
- Consumes: `RoundSuccessModel` Protocol shape (`qsim.models.protocols`) — `success_probability(self, lease_fidelities: Sequence[float], memory_retentions: Sequence[float], decoder_latency_s: float, deadline_slack_s: float) -> float`, no `epoch` parameter
- Produces:
  - `LogisticRoundSuccessModel(logistic_midpoint: float, logistic_slope: float, slack_penalty_per_s: float)` — constructor takes the config values that at wiring time come from `CalibrationEpoch.round_success_logistic_midpoint` / `.round_success_logistic_slope` / `.round_success_slack_penalty_per_s`; `success_probability(self, lease_fidelities: Sequence[float], memory_retentions: Sequence[float], decoder_latency_s: float, deadline_slack_s: float) -> float`

- [ ] **Step 1: Write the failing test**
```python
# tests/models/test_round_success.py
import math

import pytest

from qsim.models.round_success import LogisticRoundSuccessModel


def test_success_probability_at_aggregate_fidelity_equal_to_midpoint_is_one_half():
    model = LogisticRoundSuccessModel(logistic_midpoint=0.6, logistic_slope=8.0,
                                      slack_penalty_per_s=0.1)
    # single lease fidelity == midpoint, single memory retention == 1.0 =>
    # aggregate_fidelity == midpoint exactly; non-negative slack => no penalty.
    p = model.success_probability(lease_fidelities=[0.6], memory_retentions=[1.0],
                                  decoder_latency_s=0.01, deadline_slack_s=0.0)
    assert p == pytest.approx(0.5)


def test_success_probability_composes_fidelities_multiplicatively():
    midpoint, slope = 0.5, 4.0
    model = LogisticRoundSuccessModel(logistic_midpoint=midpoint, logistic_slope=slope,
                                      slack_penalty_per_s=0.0)
    lease_fidelities = [0.9, 0.8]
    memory_retentions = [0.95]
    aggregate = 0.9 * 0.8 * 0.95
    expected = 1.0 / (1.0 + math.exp(-slope * (aggregate - midpoint)))
    p = model.success_probability(lease_fidelities=lease_fidelities,
                                  memory_retentions=memory_retentions,
                                  decoder_latency_s=0.0, deadline_slack_s=0.0)
    assert p == pytest.approx(expected)


def test_negative_deadline_slack_applies_linear_penalty():
    model = LogisticRoundSuccessModel(logistic_midpoint=0.6, logistic_slope=8.0,
                                      slack_penalty_per_s=0.1)
    p = model.success_probability(lease_fidelities=[0.6], memory_retentions=[1.0],
                                  decoder_latency_s=0.0, deadline_slack_s=-2.0)
    assert p == pytest.approx(0.5 - 0.1 * 2.0)


def test_success_probability_floors_at_zero_when_penalty_exceeds_raw_probability():
    model = LogisticRoundSuccessModel(logistic_midpoint=0.6, logistic_slope=8.0,
                                      slack_penalty_per_s=10.0)
    p = model.success_probability(lease_fidelities=[0.6], memory_retentions=[1.0],
                                  decoder_latency_s=0.0, deadline_slack_s=-5.0)
    assert p == 0.0


def test_positive_deadline_slack_applies_no_penalty():
    model = LogisticRoundSuccessModel(logistic_midpoint=0.6, logistic_slope=8.0,
                                      slack_penalty_per_s=0.1)
    p_no_slack = model.success_probability(lease_fidelities=[0.6], memory_retentions=[1.0],
                                           decoder_latency_s=0.0, deadline_slack_s=0.0)
    p_positive_slack = model.success_probability(lease_fidelities=[0.6], memory_retentions=[1.0],
                                                 decoder_latency_s=0.0, deadline_slack_s=5.0)
    assert p_no_slack == pytest.approx(p_positive_slack)
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/models/test_round_success.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.models.round_success'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/models/round_success.py
"""v1 RoundSuccessModel implementation (spec sec 6): logistic curve on
aggregate fidelity with a linear deadline-slack penalty.

The frozen protocol gives success_probability no CalibrationEpoch parameter
(sec 8.1 reuses this exact surface for admission-control projection against
*projected* inputs, so it must be a pure function of its numeric arguments
alone). The logistic midpoint/slope and slack penalty are therefore
config-parameterized constructor arguments; wiring code constructs this model
from the run's CalibrationEpoch.round_success_logistic_midpoint /
.round_success_logistic_slope / .round_success_slack_penalty_per_s once.
"""
from __future__ import annotations

import math
from typing import Sequence


class LogisticRoundSuccessModel:
    def __init__(self, logistic_midpoint: float, logistic_slope: float,
                 slack_penalty_per_s: float):
        self._midpoint = logistic_midpoint
        self._slope = logistic_slope
        self._slack_penalty_per_s = slack_penalty_per_s

    def success_probability(self, lease_fidelities: Sequence[float],
                            memory_retentions: Sequence[float],
                            decoder_latency_s: float,
                            deadline_slack_s: float) -> float:
        # decoder_latency_s is accepted per the frozen signature but unused by
        # v1's formula; the caller's projection (sec 8.1) already folds
        # decoder latency into deadline_slack_s. Reserved for a future
        # service-time-sensitive extension.
        aggregate_fidelity = 1.0
        for f in lease_fidelities:
            aggregate_fidelity *= f
        for r in memory_retentions:
            aggregate_fidelity *= r

        z = self._slope * (aggregate_fidelity - self._midpoint)
        raw_p = 1.0 / (1.0 + math.exp(-z))

        if deadline_slack_s < 0.0:
            raw_p -= self._slack_penalty_per_s * abs(deadline_slack_s)

        return min(1.0, max(0.0, raw_p))
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/models/test_round_success.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/models/round_success.py tests/models/test_round_success.py
git commit -m "feat: add LogisticRoundSuccessModel"
```

### Task 6: DecoderServiceModel v1

**Files:**
- Create: `qsim/models/decoder_service.py`
- Test: `tests/models/test_decoder_service.py`

**Interfaces:**
- Consumes: `Draw` (field `u: float`) (`qsim.core.rng`); `CalibrationEpoch` (field `decoder_service_rate: float`), `DecoderJob` (`qsim.entities`); `DecoderServiceModel` Protocol shape (`qsim.models.protocols`) — `service_time_s(self, job: DecoderJob, backlog: int, draw: Draw) -> float`, no `epoch` parameter
- Produces:
  - `ExponentialDecoderServiceModel(service_rate: float)` — constructor takes the sampling rate (at wiring time, set from `CalibrationEpoch.decoder_service_rate`); `service_time_s(self, job: DecoderJob, backlog: int, draw: Draw) -> float`; `expected_service_time_s(self, backlog: int, epoch: CalibrationEpoch) -> float` (reads `epoch.decoder_service_rate` directly, independent of the constructor's `service_rate`)

- [ ] **Step 1: Write the failing test**
```python
# tests/models/test_decoder_service.py
import math

import pytest

from qsim.core.rng import Draw
from qsim.entities import CalibrationEpoch, CoherenceClass, DecoderJob
from qsim.models.decoder_service import ExponentialDecoderServiceModel


def _epoch(decoder_service_rate):
    return CalibrationEpoch(
        epoch_id="e0",
        decay_rate_per_class={CoherenceClass.MESSENGER: 1.0, CoherenceClass.MEMORY: 1.0},
        memory_access_channel_s=0.0,
        memory_access_wear_rate=0.0,
        heralding_p_per_path={},
        heralded_fidelity_per_path={},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=1.0,
        round_success_slack_penalty_per_s=0.0,
        decoder_service_rate=decoder_service_rate,
    )


def _job():
    return DecoderJob(job_id="j0", round_id="r0", priority=0, enqueue_time=0.0)


def test_expected_service_time_equals_closed_form_mean_independent_of_backlog():
    epoch = _epoch(decoder_service_rate=4.0)
    # Constructor rate deliberately differs from the epoch's rate:
    # expected_service_time_s must read the epoch, not the constructor arg.
    model = ExponentialDecoderServiceModel(service_rate=999.0)
    for backlog in (0, 1, 50):
        assert model.expected_service_time_s(backlog, epoch) == pytest.approx(1.0 / 4.0)


def test_service_time_s_matches_exponential_inverse_cdf_for_fixed_draw():
    rate = 2.5
    model = ExponentialDecoderServiceModel(service_rate=rate)
    draw = Draw(u=0.7)
    expected = -math.log(1.0 - 0.7) / rate
    assert model.service_time_s(_job(), backlog=0, draw=draw) == pytest.approx(expected)


def test_service_time_s_is_deterministic_given_the_same_draw_regardless_of_backlog():
    model = ExponentialDecoderServiceModel(service_rate=1.0)
    draw = Draw(u=0.42)
    t1 = model.service_time_s(_job(), backlog=0, draw=draw)
    t2 = model.service_time_s(_job(), backlog=10, draw=draw)
    assert t1 == pytest.approx(t2)  # v1 has no backlog penalty
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/models/test_decoder_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.models.decoder_service'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/models/decoder_service.py
"""v1 DecoderServiceModel implementation (spec sec 6): exponential service time.

The frozen protocol gives service_time_s no CalibrationEpoch parameter (it is
called at actual decode time, per attempt), so the sampling rate is a
config-parameterized constructor argument, consistent with spec sec 6's "one
analytic, config-parameterized implementation of each" -- wiring code
constructs this model from the run's CalibrationEpoch.decoder_service_rate
once. expected_service_time_s *is* given the epoch (it's the sec 8.1
admission-control projection, which always has a live epoch in hand) and
reads the rate from it directly, independent of the model's own constructor
rate.

v1 has no backlog penalty (sec 6 table calls it optional); backlog is
accepted per the frozen signatures and ignored, reserved for a future
congestion-aware extension.
"""
from __future__ import annotations

import math

from qsim.core.rng import Draw
from qsim.entities import CalibrationEpoch, DecoderJob


class ExponentialDecoderServiceModel:
    def __init__(self, service_rate: float):
        self._service_rate = service_rate

    def service_time_s(self, job: DecoderJob, backlog: int,
                       draw: Draw) -> float:
        # Inverse-CDF sampling: X = -ln(1-U)/rate ~ Exponential(rate).
        return -math.log(1.0 - draw.u) / self._service_rate

    def expected_service_time_s(self, backlog: int,
                                epoch: CalibrationEpoch) -> float:
        return 1.0 / epoch.decoder_service_rate
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/models/test_decoder_service.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/models/decoder_service.py tests/models/test_decoder_service.py
git commit -m "feat: add ExponentialDecoderServiceModel"
```
---

## Section 4 of 8 — policies/ (Scheduler protocol, S0, admission, pregen, S1)

**Note:** this section defines the richer Scheduler protocol referenced in the "Known Integration Gap" callout above — read that callout before or alongside these tasks.

### Task 1: policies/protocol.py — Scheduler Protocol and shared value types

**Files:**
- Create: `qsim/policies/__init__.py`
- Create: `qsim/policies/protocol.py`
- Test: `tests/policies/test_protocol.py`

**Interfaces:**
- Consumes: none internal to `qsim.policies` (leaf module); stdlib `dataclasses`, `enum`, `typing` only.
- Produces: `AdmissionOutcome`, `AdmissionDecision`, `LeaseRequestPurpose`, `LeaseRequest`, `DispositionKind`, `LeaseDisposition`, `ProjectableLease`, `RoundProjection`, and the `Scheduler` Protocol — consumed by every other task in this section, and by `core/engine.py`'s admission/path-allocation/lease-terminal call sites.

- [ ] **Step 1: Write the failing test**
```python
"""tests/policies/test_protocol.py — Scheduler protocol and shared value types (design spec §8)."""
from __future__ import annotations

from qsim.policies.protocol import (
    AdmissionDecision,
    AdmissionOutcome,
    DispositionKind,
    LeaseDisposition,
    LeaseRequest,
    LeaseRequestPurpose,
    ProjectableLease,
    RoundProjection,
    Scheduler,
)


def test_admission_outcome_has_admit_and_defer_members():
    assert AdmissionOutcome.ADMIT is not AdmissionOutcome.DEFER


def test_admission_decision_defaults_projection_fields_to_none():
    decision = AdmissionDecision(outcome=AdmissionOutcome.DEFER)
    assert decision.projected_success_probability is None
    assert decision.theta_admit is None
    assert decision.deadline_slack_s is None
    assert decision.decoder_latency_s_estimate is None


def test_lease_request_purpose_distinguishes_round_from_pool_replenish():
    assert LeaseRequestPurpose.ROUND is not LeaseRequestPurpose.POOL_REPLENISH


def test_lease_request_carries_identity_and_purpose():
    request = LeaseRequest(
        request_id="req-1", path_id="pathA", coherence_class="electron",
        purpose=LeaseRequestPurpose.ROUND, requested_at_s=0.0, round_id="r1",
    )
    assert request.round_id == "r1"


def test_disposition_kind_distinguishes_cancelled_pooled_and_expired():
    assert len({DispositionKind.CANCELLED, DispositionKind.RETURNED_TO_POOL,
                DispositionKind.EXPIRED}) == 3


def test_lease_disposition_is_positional_path_coherence_kind():
    disposition = LeaseDisposition("pathA", "electron", DispositionKind.EXPIRED)
    assert disposition.kind is DispositionKind.EXPIRED


def test_projectable_lease_defaults_to_not_held_not_consumed():
    lease = ProjectableLease(path_id="pathA", coherence_class="electron")
    assert lease.is_held is False
    assert lease.is_consumed is False


def test_round_projection_defaults_leases_and_qubits_to_empty_lists():
    round_ = RoundProjection(round_id="r1", deadline_s=10.0)
    assert round_.leases == []
    assert round_.qubits == []


def test_scheduler_protocol_is_structurally_satisfied_by_a_minimal_implementation():
    class _MinimalScheduler:
        def decide_admission(self, round_projection, now_s, decoder_backlog=0, epoch=None):
            return AdmissionDecision(outcome=AdmissionOutcome.ADMIT)

        def next_lease_request(self, now_s):
            return None

        def on_round_terminal(self, round_projection, succeeded, now_s):
            return []

        def register_round_demand(self, round_projection, now_s):
            return None

    assert isinstance(_MinimalScheduler(), Scheduler)
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/policies/test_protocol.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.policies'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/policies/__init__.py
"""qsim.policies: Scheduler protocol and implementations (design spec §8)."""
```
```python
# qsim/policies/protocol.py
"""Shared scheduler protocol and value types (design spec §8).

`Scheduler` is a Protocol: S0Scheduler, AdmissionMixin, and PregenMixin all
satisfy it structurally via cooperative multiple inheritance, so the §8
ablation ladder (S0, S0+admission, S0+pregen, S1) is expressed as
composition, not a family of hand-written subclasses.

`ProjectableLease`/`RoundProjection` are the projected view of a round the
engine builds for a `Scheduler` to score and dispose of — distinct from the
real `EntanglementLease`/`SyndromeRound` entities so `policies/` stays
decoupled from the entity/engine internals (§4 separation rule).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Protocol, runtime_checkable


class AdmissionOutcome(Enum):
    ADMIT = auto()
    DEFER = auto()


@dataclass(frozen=True)
class AdmissionDecision:
    """Outcome of `Scheduler.decide_admission` (design spec §8.1).

    The projection fields are populated only when a projection was actually
    computed — a scheduler that defers before projecting (e.g. S0's
    past-deadline check) leaves them `None`.
    """

    outcome: AdmissionOutcome
    projected_success_probability: float | None = None
    theta_admit: float | None = None
    deadline_slack_s: float | None = None
    decoder_latency_s_estimate: float | None = None
    reason: str | None = None


class LeaseRequestPurpose(Enum):
    """Why a scheduler is requesting a lease (design spec §8)."""

    ROUND = auto()
    POOL_REPLENISH = auto()


@dataclass(frozen=True)
class LeaseRequest:
    """A scheduler's request to acquire a lease on a path/coherence class."""

    request_id: str
    path_id: str
    coherence_class: str
    purpose: LeaseRequestPurpose
    requested_at_s: float
    round_id: str | None = None


class DispositionKind(Enum):
    """What happened to a lease at round-terminal time (design spec §5)."""

    CANCELLED = auto()          # round-bound (S0): unconsumed lease discarded
    RETURNED_TO_POOL = auto()   # pooling (pregen): still-fresh, returned
    EXPIRED = auto()            # pooling (pregen): stale, discarded


@dataclass(frozen=True)
class LeaseDisposition:
    """A scheduler's disposition of one lease at round-terminal time."""

    path_id: str
    coherence_class: str
    kind: DispositionKind


@dataclass
class ProjectableLease:
    """A lease's projectable state (design spec §8.1, §8.2)."""

    path_id: str
    coherence_class: str
    is_held: bool = False
    is_consumed: bool = False
    state_held_since: float | None = None
    freshness_bound_s: float = 1.0
    heralded_fidelity_estimate: float | None = None


@dataclass
class RoundProjection:
    """A round's projectable state, as built by the engine for a Scheduler."""

    round_id: str
    deadline_s: float
    leases: list[ProjectableLease] = field(default_factory=list)
    qubits: list = field(default_factory=list)


@runtime_checkable
class Scheduler(Protocol):
    """The scheduling interface every policy (S0, mixins, S1) implements."""

    def decide_admission(self, round_projection: RoundProjection, now_s: float,
                          decoder_backlog: int = 0, epoch: object | None = None) -> AdmissionDecision: ...

    def next_lease_request(self, now_s: float) -> LeaseRequest | None: ...

    def on_round_terminal(self, round_projection: RoundProjection, succeeded: bool,
                           now_s: float) -> list[LeaseDisposition]: ...

    def register_round_demand(self, round_projection: RoundProjection, now_s: float) -> None: ...
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/policies/test_protocol.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/policies/__init__.py qsim/policies/protocol.py tests/policies/test_protocol.py
git commit -m "feat: add Scheduler protocol and admission/lease value types (design spec §8)"
```

### Task 2: policies/s0.py — S0Scheduler, the competent baseline

**Files:**
- Create: `qsim/policies/s0.py`
- Test: `tests/policies/test_s0.py`

**Interfaces:**
- Consumes: `AdmissionDecision`, `AdmissionOutcome`, `DispositionKind`, `LeaseDisposition`, `LeaseRequest`, `LeaseRequestPurpose`, `RoundProjection` from `qsim.policies.protocol` (Task 1).
- Produces: `S0Scheduler` — the terminal base class in the mixin MRO chain (`S1Scheduler(PregenMixin, AdmissionMixin, S0Scheduler)`, Task 5), satisfying `Scheduler` directly with deadline-based admission, earliest-deadline-first lease-request ordering, and round-bound lease cancellation on termination (design spec §8, §5).

- [ ] **Step 1: Write the failing test**
```python
"""tests/policies/test_s0.py — S0Scheduler, the competent baseline (design spec §8)."""
from __future__ import annotations

from dataclasses import dataclass, field

from qsim.policies.protocol import (
    AdmissionOutcome,
    DispositionKind,
    LeaseRequestPurpose,
    Scheduler,
)
from qsim.policies.s0 import S0Scheduler


@dataclass
class _FakeLease:
    path_id: str
    coherence_class: str
    is_held: bool = False
    is_consumed: bool = False


@dataclass
class _FakeRound:
    round_id: str
    deadline_s: float
    leases: list = field(default_factory=list)
    qubits: list = field(default_factory=list)


def test_s0_scheduler_requires_no_constructor_arguments():
    assert isinstance(S0Scheduler(), Scheduler)


def test_s0_scheduler_swallows_stray_kwargs_as_the_mro_chains_terminal_init():
    # S0Scheduler is the terminal __init__ in the mixin MRO chain; it must
    # not forward unexpected kwargs to object.__init__, which would raise.
    assert isinstance(S0Scheduler(unexpected_kwarg="ignored"), S0Scheduler)


def test_decide_admission_defers_at_or_after_deadline_with_no_projection_fields():
    scheduler = S0Scheduler()
    round_ = _FakeRound(round_id="r1", deadline_s=10.0)

    decision = scheduler.decide_admission(round_, now_s=10.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.DEFER
    assert decision.projected_success_probability is None


def test_decide_admission_admits_before_deadline():
    scheduler = S0Scheduler()
    round_ = _FakeRound(round_id="r1", deadline_s=10.0)

    decision = scheduler.decide_admission(round_, now_s=1.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.ADMIT


def test_next_lease_request_is_none_with_no_registered_demand():
    assert S0Scheduler().next_lease_request(now_s=0.0) is None


def test_next_lease_request_serves_unheld_leases_in_earliest_deadline_first_order():
    scheduler = S0Scheduler()
    urgent = _FakeRound(round_id="urgent", deadline_s=5.0,
                         leases=[_FakeLease(path_id="pathA", coherence_class="electron")])
    relaxed = _FakeRound(round_id="relaxed", deadline_s=50.0,
                          leases=[_FakeLease(path_id="pathB", coherence_class="nuclear")])
    scheduler.register_round_demand(relaxed, now_s=0.0)
    scheduler.register_round_demand(urgent, now_s=0.0)

    first = scheduler.next_lease_request(now_s=0.0)

    assert first.path_id == "pathA"
    assert first.purpose is LeaseRequestPurpose.ROUND
    assert first.round_id == "urgent"


def test_register_round_demand_does_not_request_already_held_leases():
    scheduler = S0Scheduler()
    round_ = _FakeRound(round_id="r1", deadline_s=5.0,
                         leases=[_FakeLease(path_id="pathA", coherence_class="electron", is_held=True)])
    scheduler.register_round_demand(round_, now_s=0.0)

    assert scheduler.next_lease_request(now_s=0.0) is None


def test_on_round_terminal_cancels_held_unconsumed_leases():
    scheduler = S0Scheduler()
    lease = _FakeLease(path_id="pathA", coherence_class="electron", is_held=True, is_consumed=False)
    round_ = _FakeRound(round_id="r1", deadline_s=5.0, leases=[lease])

    dispositions = scheduler.on_round_terminal(round_, succeeded=False, now_s=1.0)

    assert len(dispositions) == 1
    assert dispositions[0].kind is DispositionKind.CANCELLED


def test_on_round_terminal_skips_consumed_and_never_held_leases():
    scheduler = S0Scheduler()
    consumed = _FakeLease(path_id="pathA", coherence_class="electron", is_held=True, is_consumed=True)
    never_held = _FakeLease(path_id="pathB", coherence_class="nuclear", is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=5.0, leases=[consumed, never_held])

    assert scheduler.on_round_terminal(round_, succeeded=True, now_s=1.0) == []
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/policies/test_s0.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.policies.s0'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/policies/s0.py
"""S0Scheduler: the competent baseline (design spec §8).

Deadline-based admission, earliest-deadline-first lease-request ordering,
and round-bound lease cancellation on termination (§5's cleanup cascade for
non-pooling policies) — everything a good real-time engineer builds without
the perishability insight. Composes as the terminal base class in the mixin
chain: `S1Scheduler(PregenMixin, AdmissionMixin, S0Scheduler)`.
`S0Scheduler.__init__` is the MRO chain's terminus: it accepts and discards
any stray `**kwargs` the mixins pass down, rather than forwarding them to
`object.__init__`, which raises on unexpected keyword arguments.
"""
from __future__ import annotations

import heapq
import itertools
from typing import TYPE_CHECKING

from qsim.policies.protocol import (
    AdmissionDecision,
    AdmissionOutcome,
    DispositionKind,
    LeaseDisposition,
    LeaseRequest,
    LeaseRequestPurpose,
)

if TYPE_CHECKING:
    from qsim.entities import CalibrationEpoch
    from qsim.policies.protocol import RoundProjection


class S0Scheduler:
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self._pending: list[tuple[float, int, LeaseRequest]] = []
        self._sequence = itertools.count()

    def decide_admission(self, round_projection: RoundProjection, now_s: float,
                          decoder_backlog: int = 0,
                          epoch: CalibrationEpoch | None = None) -> AdmissionDecision:
        if now_s >= round_projection.deadline_s:
            return AdmissionDecision(outcome=AdmissionOutcome.DEFER,
                                      reason="past deadline at admission time")
        return AdmissionDecision(outcome=AdmissionOutcome.ADMIT)

    def register_round_demand(self, round_projection: RoundProjection, now_s: float) -> None:
        for lease in round_projection.leases:
            if lease.is_held:
                continue
            self._enqueue(round_projection.round_id, round_projection.deadline_s,
                          lease.path_id, lease.coherence_class, now_s)

    def next_lease_request(self, now_s: float) -> LeaseRequest | None:
        if not self._pending:
            return None
        _, _, request = heapq.heappop(self._pending)
        return request

    def on_round_terminal(self, round_projection: RoundProjection, succeeded: bool,
                           now_s: float) -> list[LeaseDisposition]:
        dispositions: list[LeaseDisposition] = []
        for lease in round_projection.leases:
            if lease.is_held and not lease.is_consumed:
                dispositions.append(LeaseDisposition(
                    lease.path_id, lease.coherence_class, DispositionKind.CANCELLED))
        return dispositions

    def _enqueue(self, round_id: str, deadline_s: float, path_id: str,
                 coherence_class: str, now_s: float) -> None:
        seq = next(self._sequence)
        request = LeaseRequest(
            request_id=f"round-{round_id}-{path_id}-{coherence_class}-{seq}",
            path_id=path_id,
            coherence_class=coherence_class,
            purpose=LeaseRequestPurpose.ROUND,
            requested_at_s=now_s,
            round_id=round_id,
        )
        heapq.heappush(self._pending, (deadline_s, seq, request))
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/policies/test_s0.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/policies/s0.py tests/policies/test_s0.py
git commit -m "feat: add S0Scheduler competent baseline (design spec §8)"
```

### Task 3: policies/admission.py — AdmissionMixin, §8.1's projection gate

**Files:**
- Create: `qsim/policies/admission.py`
- Test: `tests/policies/test_admission.py`

**Interfaces:**
- Consumes: `AdmissionDecision`, `AdmissionOutcome`, `RoundProjection` from `qsim.policies.protocol` (Task 1); `S0Scheduler` (Task 2, composed via cooperative multiple inheritance); `DecayModel`, `HeraldingModel`, `MemoryAccessModel`, `RoundSuccessModel`, `DecoderServiceModel` from `qsim.models.protocols` (type hints only); `CalibrationEpoch` from `qsim.entities` (type hint only).
- Produces: `AdmissionMixin`, implementing §8.1's projected-success-probability admission gate; composed as `S1Scheduler(PregenMixin, AdmissionMixin, S0Scheduler)` in Task 5.

- [ ] **Step 1: Write the failing test**
```python
"""tests/policies/test_admission.py — AdmissionMixin projection gate (design spec §8.1)."""
from __future__ import annotations

from dataclasses import dataclass, field

from qsim.policies.admission import AdmissionMixin
from qsim.policies.protocol import AdmissionOutcome
from qsim.policies.s0 import S0Scheduler


@dataclass
class _FakeLease:
    path_id: str
    coherence_class: str
    is_held: bool = False
    state_held_since: float | None = None
    heralded_fidelity_estimate: float | None = None


@dataclass
class _FakeRound:
    round_id: str
    deadline_s: float
    leases: list = field(default_factory=list)
    qubits: list = field(default_factory=list)


class _ConstantDecay:
    def __init__(self, retention: float) -> None:
        self._retention = retention

    def retention(self, age_s, coherence_class, epoch):
        return self._retention


class _ConstantHeralding:
    def __init__(self, fidelity: float) -> None:
        self._fidelity = fidelity

    def heralded_fidelity(self, path, epoch):
        return self._fidelity

    def success_probability(self, path, epoch):
        return 1.0


@dataclass
class _FakeAccessCost:
    electron_channel_s: float
    retention_factor: float


class _ConstantMemoryAccess:
    def __init__(self, retention_factor: float) -> None:
        self._retention_factor = retention_factor

    def access_cost(self, qubit, epoch):
        return _FakeAccessCost(electron_channel_s=0.0, retention_factor=self._retention_factor)


class _MinFidelityRoundSuccess:
    def success_probability(self, lease_fidelities, memory_retentions, decoder_latency_s, deadline_slack_s):
        if deadline_slack_s <= 0:
            return 0.0
        return min(lease_fidelities) if lease_fidelities else 1.0


class _ZeroLatencyDecoderService:
    def expected_service_time_s(self, backlog, epoch):
        return 0.0

    def service_time_s(self, job, backlog, draw):
        return 0.0


def _make_scheduler(*, theta_admit: float, heralded_fidelity: float) -> AdmissionMixin:
    class _Scheduler(AdmissionMixin, S0Scheduler):
        pass

    return _Scheduler(
        theta_admit=theta_admit,
        decay_model=_ConstantDecay(1.0),
        heralding_model=_ConstantHeralding(heralded_fidelity),
        memory_access_model=_ConstantMemoryAccess(1.0),
        round_success_model=_MinFidelityRoundSuccess(),
        decoder_service_model=_ZeroLatencyDecoderService(),
    )


def test_admits_when_projected_success_probability_exceeds_theta_admit():
    scheduler = _make_scheduler(theta_admit=0.9, heralded_fidelity=0.95)
    lease = _FakeLease(path_id="pathA", coherence_class="electron", is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[lease])

    decision = scheduler.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.ADMIT
    assert decision.projected_success_probability == 0.95
    assert decision.theta_admit == 0.9


def test_defers_when_projected_success_probability_is_below_theta_admit():
    scheduler = _make_scheduler(theta_admit=0.9, heralded_fidelity=0.5)
    lease = _FakeLease(path_id="pathA", coherence_class="electron", is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[lease])

    decision = scheduler.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.DEFER
    assert decision.projected_success_probability == 0.5


def test_projection_uses_held_lease_age_from_state_held_since_not_heralding_model():
    # Already-held lease: fidelity must come from heralded_fidelity_estimate
    # decayed from state_held_since, NOT re-queried from HeraldingModel.
    scheduler = _make_scheduler(theta_admit=0.5, heralded_fidelity=0.1)  # would fail if (mis)used
    lease = _FakeLease(
        path_id="pathA", coherence_class="electron",
        is_held=True, state_held_since=0.0, heralded_fidelity_estimate=0.99,
    )
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[lease])

    decision = scheduler.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)

    assert decision.projected_success_probability == 0.99


def test_defers_at_theta_admit_boundary_when_strictly_below():
    scheduler = _make_scheduler(theta_admit=0.95, heralded_fidelity=0.9499999999999999)
    lease = _FakeLease(path_id="pathA", coherence_class="electron", is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[lease])

    decision = scheduler.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.DEFER


def test_admits_exactly_at_theta_admit_boundary():
    scheduler = _make_scheduler(theta_admit=0.9, heralded_fidelity=0.9)
    lease = _FakeLease(path_id="pathA", coherence_class="electron", is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[lease])

    decision = scheduler.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.ADMIT


def test_base_scheduler_deadline_defer_short_circuits_before_projection():
    scheduler = _make_scheduler(theta_admit=0.0, heralded_fidelity=1.0)  # would always admit if projected
    lease = _FakeLease(path_id="pathA", coherence_class="electron", is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=10.0, leases=[lease])

    decision = scheduler.decide_admission(round_, now_s=10.0, decoder_backlog=0, epoch=None)

    assert decision.outcome is AdmissionOutcome.DEFER
    assert decision.projected_success_probability is None  # never computed
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/policies/test_admission.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.policies.admission'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/policies/admission.py
"""AdmissionMixin: freshness-aware admission control (design spec §8.1).

Composes with any base Scheduler that implements `decide_admission`
(policies/s0.py's S0Scheduler in v1) via cooperative multiple inheritance:
this mixin defers to the base class's decision first (e.g. S0's
already-past-deadline check) and only computes the §8.1 projection when the
base class has not already deferred.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from qsim.policies.protocol import AdmissionDecision, AdmissionOutcome

if TYPE_CHECKING:
    from qsim.entities import CalibrationEpoch
    from qsim.models.protocols import (
        DecayModel,
        DecoderServiceModel,
        HeraldingModel,
        MemoryAccessModel,
        RoundSuccessModel,
    )
    from qsim.policies.protocol import RoundProjection


class AdmissionMixin:
    def __init__(self, *, theta_admit: float, decay_model: DecayModel,
                 heralding_model: HeraldingModel,
                 memory_access_model: MemoryAccessModel,
                 round_success_model: RoundSuccessModel,
                 decoder_service_model: DecoderServiceModel,
                 **kwargs) -> None:
        super().__init__(decoder_service_model=decoder_service_model, **kwargs)
        self._theta_admit = theta_admit
        self._decay_model = decay_model
        self._heralding_model = heralding_model
        self._memory_access_model = memory_access_model
        self._round_success_model = round_success_model
        self._admission_decoder_service_model = decoder_service_model

    def decide_admission(self, round_projection: RoundProjection, now_s: float,
                          decoder_backlog: int = 0,
                          epoch: CalibrationEpoch | None = None) -> AdmissionDecision:
        base = super().decide_admission(round_projection, now_s, decoder_backlog, epoch)
        if base.outcome is AdmissionOutcome.DEFER:
            return base

        decoder_latency_s = self._admission_decoder_service_model.expected_service_time_s(decoder_backlog, epoch)
        # v1 simplification (flagged, not specified by §8.1): projected time
        # from `now_s` to consumption is approximated as decoder_latency_s
        # alone; a richer projected_time_to_consumption term (heralding
        # attempt time, queueing ahead of decode) is future work.
        consumption_instant_s = now_s + decoder_latency_s

        lease_fidelities: list[float] = []
        for lease in round_projection.leases:
            if lease.is_held and lease.state_held_since is not None:
                age_s = consumption_instant_s - lease.state_held_since
                base_fidelity = lease.heralded_fidelity_estimate
            else:
                age_s = consumption_instant_s - now_s
                base_fidelity = self._heralding_model.heralded_fidelity(lease.path_id, epoch)
            retention = self._decay_model.retention(max(age_s, 0.0), lease.coherence_class, epoch)
            lease_fidelities.append(base_fidelity * retention)

        memory_retentions: list[float] = []
        for qubit in round_projection.qubits:
            access_cost = self._memory_access_model.access_cost(qubit, epoch)
            decay_to_access = self._decay_model.retention(
                max(consumption_instant_s - now_s, 0.0), qubit.coherence_class, epoch)
            memory_retentions.append(access_cost.retention_factor * decay_to_access)

        deadline_slack_s = round_projection.deadline_s - consumption_instant_s
        projected_p = self._round_success_model.success_probability(
            lease_fidelities, memory_retentions, decoder_latency_s, deadline_slack_s)

        outcome = AdmissionOutcome.ADMIT if projected_p >= self._theta_admit else AdmissionOutcome.DEFER
        return AdmissionDecision(
            outcome=outcome,
            projected_success_probability=projected_p,
            theta_admit=self._theta_admit,
            deadline_slack_s=deadline_slack_s,
            decoder_latency_s_estimate=decoder_latency_s,
            reason=f"projected p={projected_p!r} vs theta_admit={self._theta_admit!r}",
        )
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/policies/test_admission.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/policies/admission.py tests/policies/test_admission.py
git commit -m "feat: add AdmissionMixin implementing the §8.1 projection gate"
```

### Task 4: policies/pregen.py — PregenMixin per spec §8.2

**Files:**
- Create: `qsim/policies/pregen.py`
- Test: `tests/policies/test_pregen.py`

**Interfaces:**
- Consumes: `LeaseRequest`, `LeaseRequestPurpose`, `LeaseDisposition`, `DispositionKind` from `qsim.policies.protocol`; `S0Scheduler.next_lease_request(now_s)` and `S0Scheduler.on_round_terminal(round_projection, succeeded, now_s)` via cooperative `super()`.
- Produces: `PregenMixin` class — `__init__(self, *, low_water_mark: int, tracked_keys, **kwargs)`; `pool_depth(key) -> int`; `deposit_to_pool(lease) -> None`; `withdraw_from_pool(key) -> ProjectableLease | None`; overrides `next_lease_request(now_s) -> LeaseRequest | None`; overrides `on_round_terminal(round_projection, succeeded, now_s) -> list[LeaseDisposition]`.

- [ ] **Step 1: Write the failing test**
```python
"""tests/policies/test_pregen.py — PregenMixin pool + §5 cascade (design spec §8.2)."""
from dataclasses import dataclass, field

from qsim.policies.protocol import DispositionKind, LeaseRequestPurpose
from qsim.policies.pregen import PregenMixin
from qsim.policies.s0 import S0Scheduler


@dataclass
class _FakeLease:
    path_id: str
    coherence_class: str
    is_held: bool = False
    is_consumed: bool = False
    state_held_since: float | None = None
    freshness_bound_s: float = 1.0
    heralded_fidelity_estimate: float | None = None


@dataclass
class _FakeRound:
    round_id: str
    deadline_s: float
    leases: list = field(default_factory=list)
    qubits: list = field(default_factory=list)


class _S0WithPregen(PregenMixin, S0Scheduler):
    pass


KEY = ("pathA", "electron")


def test_next_lease_request_triggers_pool_replenish_below_low_water_mark():
    scheduler = _S0WithPregen(low_water_mark=2, tracked_keys=[KEY])

    request = scheduler.next_lease_request(now_s=0.0)

    assert request is not None
    assert request.purpose is LeaseRequestPurpose.POOL_REPLENISH
    assert request.path_id == "pathA"
    assert request.coherence_class == "electron"
    assert request.round_id is None


def test_next_lease_request_does_not_trigger_at_exactly_low_water_mark():
    scheduler = _S0WithPregen(low_water_mark=2, tracked_keys=[KEY])
    scheduler.deposit_to_pool(_FakeLease(path_id="pathA", coherence_class="electron", is_held=True))
    scheduler.deposit_to_pool(_FakeLease(path_id="pathA", coherence_class="electron", is_held=True))

    assert scheduler.pool_depth(KEY) == 2
    assert scheduler.next_lease_request(now_s=0.0) is None


def test_round_bound_demand_takes_priority_over_pool_replenish():
    scheduler = _S0WithPregen(low_water_mark=2, tracked_keys=[KEY])
    lease = _FakeLease(path_id="pathB", coherence_class="nuclear", is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=10.0, leases=[lease])
    scheduler.register_round_demand(round_, now_s=0.0)

    request = scheduler.next_lease_request(now_s=0.0)

    assert request.purpose is LeaseRequestPurpose.ROUND
    assert request.path_id == "pathB"


def test_on_round_terminal_returns_fresh_leases_to_pool():
    scheduler = _S0WithPregen(low_water_mark=1, tracked_keys=[KEY])
    fresh = _FakeLease(path_id="pathA", coherence_class="electron",
                        is_held=True, is_consumed=False,
                        state_held_since=4.0, freshness_bound_s=1.0)
    round_ = _FakeRound(round_id="r1", deadline_s=10.0, leases=[fresh])

    dispositions = scheduler.on_round_terminal(round_, succeeded=False, now_s=4.5)  # age 0.5 <= 1.0

    assert len(dispositions) == 1
    assert dispositions[0].kind is DispositionKind.RETURNED_TO_POOL
    assert scheduler.pool_depth(KEY) == 1


def test_on_round_terminal_expires_stale_leases_without_pooling_them():
    scheduler = _S0WithPregen(low_water_mark=1, tracked_keys=[KEY])
    stale = _FakeLease(path_id="pathA", coherence_class="electron",
                        is_held=True, is_consumed=False,
                        state_held_since=0.0, freshness_bound_s=1.0)
    round_ = _FakeRound(round_id="r1", deadline_s=10.0, leases=[stale])

    dispositions = scheduler.on_round_terminal(round_, succeeded=False, now_s=5.0)  # age 5.0 > 1.0

    assert len(dispositions) == 1
    assert dispositions[0].kind is DispositionKind.EXPIRED
    assert scheduler.pool_depth(KEY) == 0


def test_on_round_terminal_skips_consumed_and_never_held_leases():
    scheduler = _S0WithPregen(low_water_mark=1, tracked_keys=[KEY])
    consumed = _FakeLease(path_id="pathA", coherence_class="electron", is_held=True, is_consumed=True)
    never_held = _FakeLease(path_id="pathA", coherence_class="electron", is_held=False, is_consumed=False)
    round_ = _FakeRound(round_id="r1", deadline_s=10.0, leases=[consumed, never_held])

    dispositions = scheduler.on_round_terminal(round_, succeeded=True, now_s=1.0)

    assert dispositions == []
    assert scheduler.pool_depth(KEY) == 0
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/policies/test_pregen.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.policies.pregen'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/policies/pregen.py
"""PregenMixin: lease pre-generation pool policy (design spec §8.2).

Maintains a pool of not-yet-consumed leases keyed by (path, coherence
class); triggers a POOL_REPLENISH LeaseRequest whenever a tracked pool's
depth falls strictly below its low-water mark L. Composes with any base
Scheduler via cooperative multiple inheritance: round-bound LeaseRequests
from the base class (S0Scheduler) always take priority over pool
replenishment in `next_lease_request`.

Implements the §5 cleanup cascade for pooling policies: on round-terminal,
still-fresh unconsumed leases are returned to the pool; stale ones expire.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from qsim.policies.protocol import DispositionKind, LeaseDisposition, LeaseRequest, LeaseRequestPurpose

if TYPE_CHECKING:
    from qsim.policies.protocol import ProjectableLease, RoundProjection


class PregenMixin:
    def __init__(self, *, low_water_mark: int, tracked_keys, **kwargs) -> None:
        super().__init__(**kwargs)
        self._low_water_mark = low_water_mark
        self._pool: dict[tuple, list[ProjectableLease]] = {key: [] for key in tracked_keys}
        self._pool_request_seq = 0

    def pool_depth(self, key: tuple) -> int:
        return len(self._pool.get(key, []))

    def deposit_to_pool(self, lease: ProjectableLease) -> None:
        key = (lease.path_id, lease.coherence_class)
        self._pool.setdefault(key, []).append(lease)

    def withdraw_from_pool(self, key: tuple) -> ProjectableLease | None:
        pool = self._pool.get(key, [])
        return pool.pop(0) if pool else None

    def next_lease_request(self, now_s: float) -> LeaseRequest | None:
        base_request = super().next_lease_request(now_s)
        if base_request is not None:
            return base_request
        for key, pool in self._pool.items():
            if len(pool) < self._low_water_mark:
                self._pool_request_seq += 1
                path_id, coherence_class = key
                return LeaseRequest(
                    request_id=f"pool-{path_id}-{coherence_class}-{self._pool_request_seq}",
                    path_id=path_id,
                    coherence_class=coherence_class,
                    purpose=LeaseRequestPurpose.POOL_REPLENISH,
                    requested_at_s=now_s,
                    round_id=None,
                )
        return None

    def on_round_terminal(self, round_projection: RoundProjection, succeeded: bool,
                           now_s: float) -> list[LeaseDisposition]:
        super().on_round_terminal(round_projection, succeeded, now_s)
        dispositions: list[LeaseDisposition] = []
        for lease in round_projection.leases:
            if not (lease.is_held and not lease.is_consumed):
                continue
            age_s = now_s - (lease.state_held_since if lease.state_held_since is not None else now_s)
            if age_s <= lease.freshness_bound_s:
                self.deposit_to_pool(lease)
                dispositions.append(LeaseDisposition(lease.path_id, lease.coherence_class, DispositionKind.RETURNED_TO_POOL))
            else:
                dispositions.append(LeaseDisposition(lease.path_id, lease.coherence_class, DispositionKind.EXPIRED))
        return dispositions
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/policies/test_pregen.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/policies/pregen.py tests/policies/test_pregen.py
git commit -m "feat: add PregenMixin (low-water-mark trigger, §5 dispose cascade)"
```

### Task 5: policies/s1.py — S1Scheduler composing S0Scheduler with both mixins

**Files:**
- Create: `qsim/policies/s1.py`
- Test: `tests/policies/test_s1.py`

**Interfaces:**
- Consumes: `S0Scheduler` from `qsim.policies.s0`; `AdmissionMixin` from `qsim.policies.admission`; `PregenMixin` from `qsim.policies.pregen`.
- Produces: `S1Scheduler(PregenMixin, AdmissionMixin, S0Scheduler)` — no new methods; inherits `decide_admission`, `next_lease_request`, `on_round_terminal`, `register_round_demand`, `pool_depth`, `deposit_to_pool`, `withdraw_from_pool` from its MRO.

- [ ] **Step 1: Write the failing test**
```python
"""tests/policies/test_s1.py — S1Scheduler composability and joint behavior."""
from dataclasses import dataclass, field

from qsim.policies.admission import AdmissionMixin
from qsim.policies.pregen import PregenMixin
from qsim.policies.protocol import AdmissionOutcome, LeaseRequestPurpose
from qsim.policies.s0 import S0Scheduler
from qsim.policies.s1 import S1Scheduler


@dataclass
class _FakeAccessCost:
    electron_channel_s: float
    retention_factor: float


class _ConstantDecay:
    def __init__(self, retention: float) -> None:
        self._retention = retention

    def retention(self, age_s, coherence_class, epoch):
        return self._retention


class _ConstantHeralding:
    def __init__(self, fidelity: float) -> None:
        self._fidelity = fidelity

    def heralded_fidelity(self, path, epoch):
        return self._fidelity

    def success_probability(self, path, epoch):
        return 1.0


class _ConstantMemoryAccess:
    def access_cost(self, qubit, epoch):
        return _FakeAccessCost(electron_channel_s=0.0, retention_factor=1.0)


class _MinFidelityRoundSuccess:
    def success_probability(self, lease_fidelities, memory_retentions, decoder_latency_s, deadline_slack_s):
        if deadline_slack_s <= 0:
            return 0.0
        return min(lease_fidelities) if lease_fidelities else 1.0


class _ZeroLatencyDecoderService:
    def expected_service_time_s(self, backlog, epoch):
        return 0.0

    def service_time_s(self, job, backlog, draw):
        return 0.0


@dataclass
class _FakeLease:
    path_id: str
    coherence_class: str
    is_held: bool = False
    is_consumed: bool = False
    state_held_since: float | None = None
    freshness_bound_s: float = 1.0
    heralded_fidelity_estimate: float | None = None


@dataclass
class _FakeRound:
    round_id: str
    deadline_s: float
    leases: list = field(default_factory=list)
    qubits: list = field(default_factory=list)


KEY = ("pathA", "electron")


def _make_s1(theta_admit: float, heralded_fidelity: float, low_water_mark: int) -> S1Scheduler:
    return S1Scheduler(
        theta_admit=theta_admit,
        decay_model=_ConstantDecay(1.0),
        heralding_model=_ConstantHeralding(heralded_fidelity),
        memory_access_model=_ConstantMemoryAccess(),
        round_success_model=_MinFidelityRoundSuccess(),
        decoder_service_model=_ZeroLatencyDecoderService(),
        low_water_mark=low_water_mark,
        tracked_keys=[KEY],
    )


def test_s1_is_composed_from_the_three_named_classes_not_a_rewrite():
    assert S0Scheduler in S1Scheduler.__mro__
    assert AdmissionMixin in S1Scheduler.__mro__
    assert PregenMixin in S1Scheduler.__mro__


def test_s1_admission_gate_matches_standalone_admission_mixin_behavior():
    admits = _make_s1(theta_admit=0.9, heralded_fidelity=0.95, low_water_mark=0)
    lease = _FakeLease(path_id="pathA", coherence_class="electron", is_held=False)
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[lease])

    decision = admits.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)
    assert decision.outcome is AdmissionOutcome.ADMIT

    defers = _make_s1(theta_admit=0.9, heralded_fidelity=0.5, low_water_mark=0)
    decision2 = defers.decide_admission(round_, now_s=0.0, decoder_backlog=0, epoch=None)
    assert decision2.outcome is AdmissionOutcome.DEFER


def test_s1_pool_replenish_triggers_when_no_round_bound_demand_pending():
    scheduler = _make_s1(theta_admit=0.0, heralded_fidelity=1.0, low_water_mark=1)

    request = scheduler.next_lease_request(now_s=0.0)

    assert request is not None
    assert request.purpose is LeaseRequestPurpose.POOL_REPLENISH


def test_s1_round_terminal_disposal_cascade_returns_fresh_lease_to_pool():
    scheduler = _make_s1(theta_admit=0.0, heralded_fidelity=1.0, low_water_mark=1)
    fresh = _FakeLease(path_id="pathA", coherence_class="electron",
                        is_held=True, is_consumed=False,
                        state_held_since=0.0, freshness_bound_s=10.0)
    round_ = _FakeRound(round_id="r1", deadline_s=100.0, leases=[fresh])

    scheduler.on_round_terminal(round_, succeeded=False, now_s=1.0)

    assert scheduler.pool_depth(KEY) == 1
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/policies/test_s1.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.policies.s1'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/policies/s1.py
"""S1Scheduler: S0Scheduler + AdmissionMixin + PregenMixin (design spec §8).

Both perishability mechanisms composed via Python's cooperative multiple
inheritance (MRO), not a hand-merged rewrite, so the ablation ladder
(S0, S0+admission, S0+pregen, S1) reuses these exact three classes
unmodified — S0+admission is `class(AdmissionMixin, S0Scheduler)`,
S0+pregen is `class(PregenMixin, S0Scheduler)`, both already exercised in
tests/policies/test_admission.py and tests/policies/test_pregen.py.
"""
from __future__ import annotations

from qsim.policies.admission import AdmissionMixin
from qsim.policies.pregen import PregenMixin
from qsim.policies.s0 import S0Scheduler


class S1Scheduler(PregenMixin, AdmissionMixin, S0Scheduler):
    pass
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/policies/test_s1.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/policies/s1.py tests/policies/test_s1.py
git commit -m "feat: add S1Scheduler composing S0Scheduler with AdmissionMixin and PregenMixin"
```
---

## Section 5 of 8 — workload/ (closed-loop synthetic demand generator)

### Task 1: WorkloadGenerator — Poisson arrivals with keyed interarrival draws

**Files:**
- Create: `qsim/workload/generator.py`
- Test: `tests/workload/test_generator.py`

**Interfaces:**
- Consumes:
  - `draw_uniform(run_seed: int, stream: str, key: tuple) -> float` (from `qsim.core.rng`)
  - `SyndromeRound` dataclass — fields `round_id: str, lease_ids: list[str], qubit_ids: list[str], arrival_time: float, deadline: float, retry_ordinal: int = 0, state: RoundState = RoundState.PENDING` (from `qsim.entities`)
  - `RoundState` enum — `RoundState.PENDING` (from `qsim.entities`)
- Produces:
  - `class WorkloadGenerator`
  - `WorkloadGenerator.__init__(self, run_seed: int, arrival_rate_hz: float, leases_per_round: int, deadline_slack_s: float)`
  - `WorkloadGenerator.next_arrival(self, after_time: float, arrival_index: int) -> SyndromeRound`
  - Task-local constant `WorkloadGenerator.STREAM = "workload"` (the §10 named stream this generator draws from)

- [ ] **Step 1: Write the failing test**
```python
import math

import pytest

from qsim.core.rng import draw_uniform
from qsim.entities import RoundState
from qsim.workload.generator import WorkloadGenerator


def test_interarrival_deterministic_same_seed_and_index():
    # Same run_seed + same arrival_index => identical interarrival draw (§10 CRN guarantee).
    g1 = WorkloadGenerator(run_seed=42, arrival_rate_hz=2.0, leases_per_round=3, deadline_slack_s=1.0)
    g2 = WorkloadGenerator(run_seed=42, arrival_rate_hz=2.0, leases_per_round=3, deadline_slack_s=1.0)
    r1 = g1.next_arrival(after_time=0.0, arrival_index=7)
    r2 = g2.next_arrival(after_time=0.0, arrival_index=7)
    assert r1.arrival_time == r2.arrival_time


def test_different_seed_changes_interarrival():
    g1 = WorkloadGenerator(run_seed=1, arrival_rate_hz=2.0, leases_per_round=1, deadline_slack_s=1.0)
    g2 = WorkloadGenerator(run_seed=2, arrival_rate_hz=2.0, leases_per_round=1, deadline_slack_s=1.0)
    r1 = g1.next_arrival(after_time=0.0, arrival_index=7)
    r2 = g2.next_arrival(after_time=0.0, arrival_index=7)
    assert r1.arrival_time != r2.arrival_time


def test_interarrival_keyed_by_index_not_call_order():
    # The draw is keyed by arrival_index, so call order must not affect the result (§10).
    g1 = WorkloadGenerator(run_seed=1, arrival_rate_hz=1.0, leases_per_round=1, deadline_slack_s=0.5)
    a = g1.next_arrival(after_time=0.0, arrival_index=1)
    b = g1.next_arrival(after_time=0.0, arrival_index=2)

    g2 = WorkloadGenerator(run_seed=1, arrival_rate_hz=1.0, leases_per_round=1, deadline_slack_s=0.5)
    b2 = g2.next_arrival(after_time=0.0, arrival_index=2)  # reversed call order
    a2 = g2.next_arrival(after_time=0.0, arrival_index=1)

    assert a.arrival_time == a2.arrival_time
    assert b.arrival_time == b2.arrival_time


def test_interarrival_is_exponential_inverse_transform_of_keyed_uniform():
    seed, rate, idx = 99, 4.0, 3
    g = WorkloadGenerator(run_seed=seed, arrival_rate_hz=rate, leases_per_round=1, deadline_slack_s=0.0)
    u = draw_uniform(seed, "workload", ("arrival", idx))
    expected_interarrival = -math.log(1.0 - u) / rate
    r = g.next_arrival(after_time=10.0, arrival_index=idx)
    # arrival_time = after_time + exponential(rate) interarrival.
    assert r.arrival_time == pytest.approx(10.0 + expected_interarrival)


def test_next_arrival_builds_pending_round_with_leases_and_deadline():
    g = WorkloadGenerator(run_seed=5, arrival_rate_hz=1.0, leases_per_round=4, deadline_slack_s=2.5)
    r = g.next_arrival(after_time=0.0, arrival_index=11)
    assert r.round_id == "round-11"
    assert len(r.lease_ids) == 4
    assert r.retry_ordinal == 0
    assert r.state is RoundState.PENDING
    assert r.deadline == pytest.approx(r.arrival_time + 2.5)
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/workload/test_generator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.workload.generator'` (the module and `WorkloadGenerator` do not yet exist).

- [ ] **Step 3: Write minimal implementation**
```python
import math

from qsim.core.rng import draw_uniform
from qsim.entities import RoundState, SyndromeRound


class WorkloadGenerator:
    STREAM = "workload"

    def __init__(self, run_seed: int, arrival_rate_hz: float,
                 leases_per_round: int, deadline_slack_s: float):
        self.run_seed = run_seed
        self.arrival_rate_hz = arrival_rate_hz
        self.leases_per_round = leases_per_round
        self.deadline_slack_s = deadline_slack_s

    def next_arrival(self, after_time: float, arrival_index: int) -> SyndromeRound:
        # arrival_index is the semantic key for the interarrival draw — never event-heap order (§10).
        u = draw_uniform(self.run_seed, self.STREAM, ("arrival", arrival_index))
        interarrival_s = -math.log(1.0 - u) / self.arrival_rate_hz
        arrival_time = after_time + interarrival_s
        round_id = f"round-{arrival_index}"
        lease_ids = [f"{round_id}-lease-{i}" for i in range(self.leases_per_round)]
        return SyndromeRound(
            round_id=round_id,
            lease_ids=lease_ids,
            qubit_ids=[],
            arrival_time=arrival_time,
            deadline=arrival_time + self.deadline_slack_s,
            retry_ordinal=0,
            state=RoundState.PENDING,
        )
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/workload/test_generator.py -v`
Expected: PASS (all five tests).

- [ ] **Step 5: Commit**
```bash
git add qsim/workload/generator.py tests/workload/test_generator.py
git commit -m "feat(workload): WorkloadGenerator Poisson arrivals with arrival_index-keyed interarrival draws"
```

---

### Task 2: WorkloadGenerator.on_outcome — closed-loop retry with lineage

**Files:**
- Create: `qsim/workload/generator.py` (extends the class from Task 1)
- Test: `tests/workload/test_generator_outcome.py`

**Interfaces:**
- Consumes:
  - `SyndromeRound` dataclass — fields `round_id`, `lease_ids`, `qubit_ids`, `arrival_time`, `deadline`, `retry_ordinal`, `state` (from `qsim.entities`)
  - `RoundState.PENDING` (from `qsim.entities`)
  - `WorkloadGenerator.next_arrival` (from Task 1, to construct the round under test)
- Produces:
  - `WorkloadGenerator.on_outcome(self, round: SyndromeRound, succeeded: bool) -> SyndromeRound | None` — returns `None` on success; on failure returns a retry `SyndromeRound` with `retry_ordinal + 1` and the same `round_id` (lineage), reset to `RoundState.PENDING`. v1 retry policy: always retry on failure.

- [ ] **Step 1: Write the failing test**
```python
from qsim.entities import RoundState
from qsim.workload.generator import WorkloadGenerator


def _round(index=0):
    g = WorkloadGenerator(run_seed=1, arrival_rate_hz=1.0, leases_per_round=2, deadline_slack_s=1.0)
    return g, g.next_arrival(after_time=0.0, arrival_index=index)


def test_on_outcome_success_returns_none():
    g, r = _round()
    assert g.on_outcome(r, succeeded=True) is None


def test_on_outcome_failure_returns_retry_with_incremented_ordinal_same_identity():
    g, r = _round(index=8)
    retry = g.on_outcome(r, succeeded=False)
    assert retry is not None
    assert retry.round_id == r.round_id            # round identity preserved for lineage
    assert retry.lease_ids == r.lease_ids
    assert retry.retry_ordinal == r.retry_ordinal + 1
    assert retry.state is RoundState.PENDING


def test_retry_ordinal_increments_across_repeated_failures():
    g, r = _round(index=3)
    r1 = g.on_outcome(r, succeeded=False)
    r2 = g.on_outcome(r1, succeeded=False)
    assert (r1.retry_ordinal, r2.retry_ordinal) == (1, 2)
    assert r2.round_id == r.round_id               # lineage held across multiple retries


def test_retry_is_a_distinct_object_from_the_original():
    g, r = _round()
    retry = g.on_outcome(r, succeeded=False)
    assert retry is not r
    assert r.retry_ordinal == 0                    # original round is not mutated
    assert r.state is RoundState.PENDING
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/workload/test_generator_outcome.py -v`
Expected: FAIL with `AttributeError: 'WorkloadGenerator' object has no attribute 'on_outcome'`.

- [ ] **Step 3: Write minimal implementation**
Add the `on_outcome` method to the `WorkloadGenerator` class in `qsim/workload/generator.py` (full file shown for clarity):
```python
import math

from qsim.core.rng import draw_uniform
from qsim.entities import RoundState, SyndromeRound


class WorkloadGenerator:
    STREAM = "workload"

    def __init__(self, run_seed: int, arrival_rate_hz: float,
                 leases_per_round: int, deadline_slack_s: float):
        self.run_seed = run_seed
        self.arrival_rate_hz = arrival_rate_hz
        self.leases_per_round = leases_per_round
        self.deadline_slack_s = deadline_slack_s

    def next_arrival(self, after_time: float, arrival_index: int) -> SyndromeRound:
        # arrival_index is the semantic key for the interarrival draw — never event-heap order (§10).
        u = draw_uniform(self.run_seed, self.STREAM, ("arrival", arrival_index))
        interarrival_s = -math.log(1.0 - u) / self.arrival_rate_hz
        arrival_time = after_time + interarrival_s
        round_id = f"round-{arrival_index}"
        lease_ids = [f"{round_id}-lease-{i}" for i in range(self.leases_per_round)]
        return SyndromeRound(
            round_id=round_id,
            lease_ids=lease_ids,
            qubit_ids=[],
            arrival_time=arrival_time,
            deadline=arrival_time + self.deadline_slack_s,
            retry_ordinal=0,
            state=RoundState.PENDING,
        )

    def on_outcome(self, round: SyndromeRound, succeeded: bool) -> SyndromeRound | None:
        if succeeded:
            return None
        # v1 policy: failures always retry. Same round_id preserves lineage across the retry chain.
        return SyndromeRound(
            round_id=round.round_id,
            lease_ids=list(round.lease_ids),
            qubit_ids=list(round.qubit_ids),
            arrival_time=round.arrival_time,
            deadline=round.deadline,
            retry_ordinal=round.retry_ordinal + 1,
            state=RoundState.PENDING,
        )
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/workload/test_generator_outcome.py -v`
Expected: PASS (all four tests). Also run `pytest tests/workload/ -v` to confirm Task 1's tests still pass.

- [ ] **Step 5: Commit**
```bash
git add qsim/workload/generator.py tests/workload/test_generator_outcome.py
git commit -m "feat(workload): on_outcome closed-loop retry preserving round identity for lineage"
```

---

## Section 6 of 8 — observe/ (trace sink, work accounting, metric views)

### Task 1: RunDirWriter — run directory scaffold and header.json

**Files:**
- Create: `qsim/observe/__init__.py`
- Create: `qsim/observe/run_dir.py`
- Test: `tests/observe/test_run_dir.py`

**Interfaces:**
- Consumes: none from sibling packages. `write_header`'s `config` parameter is accepted structurally (duck-typed via `dataclasses.fields`/`dataclasses.is_dataclass`) exactly because the frozen contract gives it as a bare forward-reference `"RunConfig"` — `observe/` must not import `experiments/config.py` (upward dependency). Any dataclass instance works, including `entities.CalibrationEpoch`-shaped nested structures with `Enum` values/keys and tuple-of-dataclass keys (e.g. `PathId`).
- Produces:
  - `SCHEMA_VERSION: int` (module constant, task-local)
  - `class RunDirWriter:` with `__init__(self, root: Path, run_id: str)` — verbatim from frozen contract
  - `RunDirWriter.write_header(self, config, run_seed: int, git_sha: str, filtering_declared: dict | None = None) -> None` — verbatim from frozen contract. Writes `root/run_id/header.json` containing keys `run_id`, `run_seed`, `git_sha`, `schema_version`, `filtering`, `config`. Per spec §12: when `filtering_declared` is `None`, `header["filtering"]` is written as the explicit dict `{"enabled": False}` — never omitted.
  - `__init__` also creates `root/run_id/` and `root/run_id/checkpoints/` on disk (run directory scaffold per §12).
  - Task-local private helpers `_json_safe(obj)` and `_key_to_str(key)` (recursive, generic JSON-safety conversion for dataclasses/Enums/tuple-or-dataclass dict keys — used by `write_header` and reused by Task 2's `append_event`).

- [ ] **Step 1: Write the failing test**
```python
import json
from dataclasses import dataclass
from enum import Enum

from qsim.observe.run_dir import RunDirWriter, SCHEMA_VERSION


class _FakeCoherenceClass(Enum):
    MESSENGER = "messenger"
    MEMORY = "memory"


@dataclass(frozen=True)
class _FakePortId:
    module_id: str
    port_index: int


@dataclass(frozen=True)
class _FakeEpoch:
    epoch_id: str
    decay_rate_per_class: dict
    heralding_p_per_path: dict


@dataclass(frozen=True)
class _FakeRunConfig:
    run_seed: int
    scheduler: str
    epoch: _FakeEpoch


def _plain_config():
    return _FakeRunConfig(
        run_seed=42, scheduler="S0",
        epoch=_FakeEpoch(epoch_id="e0", decay_rate_per_class={}, heralding_p_per_path={}),
    )


def test_write_header_declares_no_filtering_by_default(tmp_path):
    writer = RunDirWriter(root=tmp_path, run_id="run-1")

    writer.write_header(config=_plain_config(), run_seed=42, git_sha="abc123")

    header = json.loads((tmp_path / "run-1" / "header.json").read_text())
    assert "filtering" in header
    assert header["filtering"] == {"enabled": False}


def test_write_header_records_declared_filtering_verbatim(tmp_path):
    writer = RunDirWriter(root=tmp_path, run_id="run-2")
    filtering = {"enabled": True, "reason": "capped at 1000 events", "cap": 1000}

    writer.write_header(config=_plain_config(), run_seed=1, git_sha="def456",
                         filtering_declared=filtering)

    header = json.loads((tmp_path / "run-2" / "header.json").read_text())
    assert header["filtering"] == filtering


def test_write_header_includes_identity_and_schema_version(tmp_path):
    writer = RunDirWriter(root=tmp_path, run_id="run-3")

    writer.write_header(config=_plain_config(), run_seed=9, git_sha="jkl012")

    header = json.loads((tmp_path / "run-3" / "header.json").read_text())
    assert header["run_id"] == "run-3"
    assert header["run_seed"] == 9
    assert header["git_sha"] == "jkl012"
    assert header["schema_version"] == SCHEMA_VERSION


def test_write_header_serializes_enum_and_tuple_dataclass_keys(tmp_path):
    writer = RunDirWriter(root=tmp_path, run_id="run-4")
    port_a = _FakePortId(module_id="modA", port_index=0)
    port_b = _FakePortId(module_id="modB", port_index=1)
    epoch = _FakeEpoch(
        epoch_id="e0",
        decay_rate_per_class={_FakeCoherenceClass.MEMORY: 0.01},
        heralding_p_per_path={(port_a, port_b): 0.5},
    )
    config = _FakeRunConfig(run_seed=7, scheduler="S0", epoch=epoch)

    writer.write_header(config=config, run_seed=7, git_sha="ghi789")

    raw = (tmp_path / "run-4" / "header.json").read_text()
    header = json.loads(raw)  # must not raise: proves valid JSON was written
    epoch_out = header["config"]["epoch"]
    assert epoch_out["decay_rate_per_class"] == {"memory": 0.01}
    (path_key,) = epoch_out["heralding_p_per_path"].keys()
    assert epoch_out["heralding_p_per_path"][path_key] == 0.5


def test_init_creates_run_directory_with_checkpoints_subdir(tmp_path):
    RunDirWriter(root=tmp_path, run_id="run-5")

    assert (tmp_path / "run-5").is_dir()
    assert (tmp_path / "run-5" / "checkpoints").is_dir()
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/observe/test_run_dir.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.observe.run_dir'` (or `ImportError` for `RunDirWriter`/`SCHEMA_VERSION`)
- [ ] **Step 3: Write minimal implementation**
```python
import dataclasses
import json
from enum import Enum
from pathlib import Path

SCHEMA_VERSION = 1


def _key_to_str(key):
    if isinstance(key, str):
        return key
    if isinstance(key, Enum):
        return str(key.value)
    if isinstance(key, (int, float)) and not isinstance(key, bool):
        return str(key)
    return json.dumps(_json_safe(key), sort_keys=True)


def _json_safe(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _json_safe(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {_key_to_str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj


class RunDirWriter:
    def __init__(self, root: Path, run_id: str) -> None:
        self.root = Path(root)
        self.run_id = run_id
        self.run_dir = self.root / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
        self.header_path = self.run_dir / "header.json"
        self.events_path = self.run_dir / "events.jsonl"

    def write_header(self, config, run_seed: int, git_sha: str,
                      filtering_declared: dict | None = None) -> None:
        filtering = filtering_declared if filtering_declared is not None else {"enabled": False}
        header = {
            "run_id": self.run_id,
            "run_seed": run_seed,
            "git_sha": git_sha,
            "schema_version": SCHEMA_VERSION,
            "filtering": filtering,
            "config": _json_safe(config),
        }
        self.header_path.write_text(json.dumps(header, indent=2, sort_keys=True))
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/observe/test_run_dir.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/observe/__init__.py qsim/observe/run_dir.py tests/observe/test_run_dir.py
git commit -m "feat(observe): RunDirWriter directory scaffold and header.json with explicit filtering declaration"
```

### Task 2: RunDirWriter — events.jsonl append_event

**Files:**
- Create: `qsim/observe/run_dir.py` (edit, adds a method)
- Test: `tests/observe/test_run_dir_append_event.py`

**Interfaces:**
- Consumes: `qsim.core.trace.Event` — frozen dataclass fields `run_id: str, seq: int, sim_time: float, event_type: str, entity_id: str, causal_parent_id: EventId | None, payload: dict`, where `EventId = tuple[str, int]`.
- Produces: `RunDirWriter.append_event(self, event: Event) -> None` — verbatim from frozen contract. Appends one JSON line to `events.jsonl` per call, preserving call order. `causal_parent_id` is serialized as a JSON array `[run_id, seq]` or `null`; `payload` is passed through `_json_safe` (Task 1) for robustness.

- [ ] **Step 1: Write the failing test**
```python
import json

from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter


def test_append_event_writes_single_jsonl_line_with_all_fields(tmp_path):
    writer = RunDirWriter(root=tmp_path, run_id="run-1")
    event = Event(
        run_id="run-1", seq=0, sim_time=1.5, event_type="round.arrived",
        entity_id="round-1", causal_parent_id=None,
        payload={"retry_ordinal": 0},
    )

    writer.append_event(event)

    lines = (tmp_path / "run-1" / "events.jsonl").read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record == {
        "run_id": "run-1", "seq": 0, "sim_time": 1.5,
        "event_type": "round.arrived", "entity_id": "round-1",
        "causal_parent_id": None, "payload": {"retry_ordinal": 0},
    }


def test_append_event_serializes_causal_parent_id_tuple_as_list(tmp_path):
    writer = RunDirWriter(root=tmp_path, run_id="run-2")
    event = Event(
        run_id="run-2", seq=3, sim_time=2.0, event_type="lease.consumed",
        entity_id="lease-9", causal_parent_id=("run-2", 1),
        payload={"fidelity_at_consumption": 0.87},
    )

    writer.append_event(event)

    record = json.loads((tmp_path / "run-2" / "events.jsonl").read_text().splitlines()[0])
    assert record["causal_parent_id"] == ["run-2", 1]


def test_append_event_multiple_calls_preserve_order(tmp_path):
    writer = RunDirWriter(root=tmp_path, run_id="run-3")
    for i in range(3):
        writer.append_event(Event(
            run_id="run-3", seq=i, sim_time=float(i), event_type="round.arrived",
            entity_id=f"round-{i}", causal_parent_id=None, payload={"retry_ordinal": 0},
        ))

    lines = (tmp_path / "run-3" / "events.jsonl").read_text().splitlines()
    seqs = [json.loads(line)["seq"] for line in lines]
    assert seqs == [0, 1, 2]
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/observe/test_run_dir_append_event.py -v`
Expected: FAIL with `AttributeError: 'RunDirWriter' object has no attribute 'append_event'`
- [ ] **Step 3: Write minimal implementation**
```python
    def append_event(self, event) -> None:
        record = {
            "run_id": event.run_id,
            "seq": event.seq,
            "sim_time": event.sim_time,
            "event_type": event.event_type,
            "entity_id": event.entity_id,
            "causal_parent_id": (
                list(event.causal_parent_id) if event.causal_parent_id is not None else None
            ),
            "payload": _json_safe(event.payload),
        }
        with open(self.events_path, "a") as f:
            f.write(json.dumps(record) + "\n")
```
(Append this method to the `RunDirWriter` class body in `qsim/observe/run_dir.py`, immediately after `write_header`.)
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/observe/test_run_dir_append_event.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/observe/run_dir.py tests/observe/test_run_dir_append_event.py
git commit -m "feat(observe): RunDirWriter.append_event writes ordered events.jsonl lines"
```

### Task 3: WorkAccounting dataclass — counters, attempts(), goodput()

**Files:**
- Create: `qsim/observe/work_accounting.py`
- Test: `tests/observe/test_work_accounting.py`

**Interfaces:**
- Consumes: none.
- Produces: `@dataclass class WorkAccounting` with fields `offered: int = 0, retries: int = 0, admitted: int = 0, deferred: int = 0, dropped: int = 0, completed_in_deadline: int = 0, completed_late: int = 0, failed: int = 0, pool_returned: int = 0` — verbatim from frozen contract; methods `attempts(self) -> int` (= `offered + retries`) and `goodput(self) -> float` (= `completed_in_deadline / offered`, `0.0` if `offered == 0`) — verbatim from frozen contract.

- [ ] **Step 1: Write the failing test**
```python
from qsim.observe.work_accounting import WorkAccounting


def test_defaults_are_all_zero():
    wa = WorkAccounting()
    assert wa.offered == 0
    assert wa.retries == 0
    assert wa.admitted == 0
    assert wa.deferred == 0
    assert wa.dropped == 0
    assert wa.completed_in_deadline == 0
    assert wa.completed_late == 0
    assert wa.failed == 0
    assert wa.pool_returned == 0


def test_attempts_is_offered_plus_retries():
    wa = WorkAccounting(offered=10, retries=4)
    assert wa.attempts() == 14


def test_goodput_is_completed_in_deadline_over_offered():
    wa = WorkAccounting(offered=8, completed_in_deadline=2)
    assert wa.goodput() == 0.25


def test_goodput_is_zero_when_no_work_offered():
    wa = WorkAccounting(offered=0, completed_in_deadline=0)
    assert wa.goodput() == 0.0


def test_pool_returned_is_tracked_separately_from_completed():
    wa = WorkAccounting(offered=5, completed_in_deadline=1, pool_returned=3)
    assert wa.goodput() == 0.2
    assert wa.pool_returned == 3
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/observe/test_work_accounting.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.observe.work_accounting'`
- [ ] **Step 3: Write minimal implementation**
```python
from dataclasses import dataclass


@dataclass
class WorkAccounting:
    offered: int = 0
    retries: int = 0
    admitted: int = 0
    deferred: int = 0
    dropped: int = 0
    completed_in_deadline: int = 0
    completed_late: int = 0
    failed: int = 0
    pool_returned: int = 0

    def attempts(self) -> int:
        return self.offered + self.retries

    def goodput(self) -> float:
        if self.offered == 0:
            return 0.0
        return self.completed_in_deadline / self.offered
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/observe/test_work_accounting.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/observe/work_accounting.py tests/observe/test_work_accounting.py
git commit -m "feat(observe): WorkAccounting counters with attempts() and offered-normalized goodput()"
```

### Task 4: iter_events + compute_work_accounting — trace aggregation

**Files:**
- Create: `qsim/observe/work_accounting.py` (edit, adds functions)
- Test: `tests/observe/test_compute_work_accounting.py`

**Interfaces:**
- Consumes: `RunDirWriter` (Tasks 1–2) and `qsim.core.trace.Event` as test fixture builders; `events.jsonl` line format produced by `RunDirWriter.append_event`.
- Produces (task-local additions, not in the frozen contract but required plumbing for §11/§12 views):
  - `iter_events(events_path: Path) -> Iterator[dict]` — yields one parsed JSON dict per line of `events.jsonl`, in file order.
  - `compute_work_accounting(events_path: Path) -> WorkAccounting` — scans a trace and returns a populated `WorkAccounting`. **Local trace convention** (documented here since payload shapes are not frozen by the interface contract): a `round.arrived` event's `payload["retry_ordinal"]` of `0` counts toward `offered`; any value `> 0` counts toward `retries`. `round.admitted`, `round.deferred`, `round.dropped`, `round.completed_in_deadline`, `round.completed_late`, `round.failed`, and `lease.pool_returned` each increment the identically-named `WorkAccounting` field once per occurrence.

- [ ] **Step 1: Write the failing test**
```python
from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.work_accounting import compute_work_accounting, iter_events


def _seed_events(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def test_iter_events_yields_dicts_in_file_order(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="round.arrived",
              entity_id="round-0", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=1, sim_time=1.0, event_type="round.admitted",
              entity_id="round-0", causal_parent_id=("r", 0), payload={}),
    ]
    path = _seed_events(tmp_path, "run-iter", events)

    records = list(iter_events(path))

    assert [r["event_type"] for r in records] == ["round.arrived", "round.admitted"]


def test_compute_work_accounting_counts_each_event_type(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="round.arrived",
              entity_id="round-0", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=1, sim_time=0.1, event_type="round.arrived",
              entity_id="round-1", causal_parent_id=None, payload={"retry_ordinal": 1}),
        Event(run_id="r", seq=2, sim_time=0.2, event_type="round.admitted",
              entity_id="round-0", causal_parent_id=("r", 0), payload={}),
        Event(run_id="r", seq=3, sim_time=0.3, event_type="round.deferred",
              entity_id="round-1", causal_parent_id=("r", 1), payload={}),
        Event(run_id="r", seq=4, sim_time=0.4, event_type="round.dropped",
              entity_id="round-2", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=5, sim_time=0.5, event_type="round.completed_in_deadline",
              entity_id="round-0", causal_parent_id=("r", 2), payload={"success_probability": 0.9}),
        Event(run_id="r", seq=6, sim_time=0.6, event_type="round.completed_late",
              entity_id="round-3", causal_parent_id=None, payload={"success_probability": 0.8}),
        Event(run_id="r", seq=7, sim_time=0.7, event_type="round.failed",
              entity_id="round-4", causal_parent_id=None, payload={"success_probability": 0.3}),
        Event(run_id="r", seq=8, sim_time=0.8, event_type="lease.pool_returned",
              entity_id="lease-0", causal_parent_id=None, payload={}),
    ]
    path = _seed_events(tmp_path, "run-wa", events)

    wa = compute_work_accounting(path)

    assert wa.offered == 1
    assert wa.retries == 1
    assert wa.admitted == 1
    assert wa.deferred == 1
    assert wa.dropped == 1
    assert wa.completed_in_deadline == 1
    assert wa.completed_late == 1
    assert wa.failed == 1
    assert wa.pool_returned == 1


def test_compute_work_accounting_empty_trace_is_all_zero(tmp_path):
    path = _seed_events(tmp_path, "run-empty", [])

    wa = compute_work_accounting(path)

    assert wa.offered == 0
    assert wa.attempts() == 0
    assert wa.goodput() == 0.0
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/observe/test_compute_work_accounting.py -v`
Expected: FAIL with `ImportError: cannot import name 'iter_events' from 'qsim.observe.work_accounting'`
- [ ] **Step 3: Write minimal implementation**
```python
import json
from pathlib import Path
from typing import Iterator


def iter_events(events_path: Path) -> Iterator[dict]:
    with open(events_path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


_TERMINAL_ROUND_FIELD = {
    "round.admitted": "admitted",
    "round.deferred": "deferred",
    "round.dropped": "dropped",
    "round.completed_in_deadline": "completed_in_deadline",
    "round.completed_late": "completed_late",
    "round.failed": "failed",
    "lease.pool_returned": "pool_returned",
}


def compute_work_accounting(events_path: Path) -> WorkAccounting:
    wa = WorkAccounting()
    for record in iter_events(events_path):
        event_type = record["event_type"]
        if event_type == "round.arrived":
            if record["payload"].get("retry_ordinal", 0) == 0:
                wa.offered += 1
            else:
                wa.retries += 1
            continue
        field = _TERMINAL_ROUND_FIELD.get(event_type)
        if field is not None:
            setattr(wa, field, getattr(wa, field) + 1)
    return wa
```
(Add these imports/functions to `qsim/observe/work_accounting.py`, above or below the existing `WorkAccounting` class; `json`, `Path`, and `Iterator` imports go at the top of the file alongside the existing `dataclasses` import.)
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/observe/test_compute_work_accounting.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/observe/work_accounting.py tests/observe/test_compute_work_accounting.py
git commit -m "feat(observe): iter_events and compute_work_accounting trace aggregation"
```

### Task 5: views.goodput — primary, offered-normalized metric

**Files:**
- Create: `qsim/observe/views.py`
- Test: `tests/observe/test_views_goodput.py`

**Interfaces:**
- Consumes: `compute_work_accounting(events_path: Path) -> WorkAccounting` (Task 4); `RunDirWriter`, `qsim.core.trace.Event` as fixture builders.
- Produces: `goodput(events_path: Path) -> float` — verbatim from frozen contract. Per §11, this is `completed_in_deadline / offered` and must never be gameable by rejecting work (that would be a "compliance-among-admitted" metric, which this function does not compute).

- [ ] **Step 1: Write the failing test**
```python
from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.views import goodput


def _seed(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def test_goodput_is_completed_in_deadline_over_offered(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="round.arrived",
              entity_id="round-0", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=1, sim_time=0.1, event_type="round.arrived",
              entity_id="round-1", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=2, sim_time=0.2, event_type="round.completed_in_deadline",
              entity_id="round-0", causal_parent_id=None, payload={"success_probability": 0.95}),
        Event(run_id="r", seq=3, sim_time=0.3, event_type="round.failed",
              entity_id="round-1", causal_parent_id=None, payload={"success_probability": 0.2}),
    ]
    path = _seed(tmp_path, "run-gp", events)

    assert goodput(path) == 0.5


def test_goodput_is_not_fooled_by_dropping_work_to_raise_compliance_among_admitted(tmp_path):
    # 4 rounds offered. Only 1 is admitted and completes in time; the other 3
    # are dropped outright. A naive "compliance among admitted" metric
    # (completed_in_deadline / admitted == 1/1 == 100%) would look perfect,
    # but the primary offered-normalized goodput view must reflect that most
    # offered work never got served.
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="round.arrived",
              entity_id="round-0", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=1, sim_time=0.1, event_type="round.arrived",
              entity_id="round-1", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=2, sim_time=0.2, event_type="round.arrived",
              entity_id="round-2", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=3, sim_time=0.3, event_type="round.arrived",
              entity_id="round-3", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=4, sim_time=0.4, event_type="round.admitted",
              entity_id="round-0", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=5, sim_time=0.5, event_type="round.completed_in_deadline",
              entity_id="round-0", causal_parent_id=None, payload={"success_probability": 0.95}),
        Event(run_id="r", seq=6, sim_time=0.6, event_type="round.dropped",
              entity_id="round-1", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=7, sim_time=0.7, event_type="round.dropped",
              entity_id="round-2", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=8, sim_time=0.8, event_type="round.dropped",
              entity_id="round-3", causal_parent_id=None, payload={}),
    ]
    path = _seed(tmp_path, "run-gaming", events)

    naive_compliance_among_admitted = 1 / 1  # what a work-rejecting admission controller would show
    assert naive_compliance_among_admitted == 1.0

    assert goodput(path) == 0.25


def test_goodput_is_zero_on_empty_trace(tmp_path):
    path = _seed(tmp_path, "run-empty", [])
    assert goodput(path) == 0.0
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/observe/test_views_goodput.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.observe.views'`
- [ ] **Step 3: Write minimal implementation**
```python
from pathlib import Path

from qsim.observe.work_accounting import compute_work_accounting, iter_events


def goodput(events_path: Path) -> float:
    return compute_work_accounting(events_path).goodput()
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/observe/test_views_goodput.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/observe/views.py tests/observe/test_views_goodput.py
git commit -m "feat(observe): goodput view normalized by offered work, resistant to admission gaming"
```

### Task 6: views.freshness_at_consumption

**Files:**
- Create: `qsim/observe/views.py` (edit, adds function)
- Test: `tests/observe/test_views_freshness.py`

**Interfaces:**
- Consumes: `iter_events(events_path: Path) -> Iterator[dict]` (Task 4).
- Produces: `freshness_at_consumption(events_path: Path) -> list[float]` — verbatim from frozen contract. **Local trace convention:** a `lease.consumed` event's `payload["fidelity_at_consumption"]` (float) is the fidelity value collected; order matches trace order.

- [ ] **Step 1: Write the failing test**
```python
from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.views import freshness_at_consumption


def _seed(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def test_freshness_at_consumption_returns_fidelity_values_in_order(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="lease.consumed",
              entity_id="lease-0", causal_parent_id=None, payload={"fidelity_at_consumption": 0.91}),
        Event(run_id="r", seq=1, sim_time=1.0, event_type="lease.expired",
              entity_id="lease-1", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=2, sim_time=2.0, event_type="lease.consumed",
              entity_id="lease-2", causal_parent_id=None, payload={"fidelity_at_consumption": 0.77}),
    ]
    path = _seed(tmp_path, "run-fresh", events)

    assert freshness_at_consumption(path) == [0.91, 0.77]


def test_freshness_at_consumption_empty_when_no_consumptions(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="lease.expired",
              entity_id="lease-0", causal_parent_id=None, payload={}),
    ]
    path = _seed(tmp_path, "run-nofresh", events)

    assert freshness_at_consumption(path) == []
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/observe/test_views_freshness.py -v`
Expected: FAIL with `ImportError: cannot import name 'freshness_at_consumption' from 'qsim.observe.views'`
- [ ] **Step 3: Write minimal implementation**
```python
def freshness_at_consumption(events_path: Path) -> list[float]:
    return [
        record["payload"]["fidelity_at_consumption"]
        for record in iter_events(events_path)
        if record["event_type"] == "lease.consumed"
    ]
```
(Append to `qsim/observe/views.py`.)
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/observe/test_views_freshness.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/observe/views.py tests/observe/test_views_freshness.py
git commit -m "feat(observe): freshness_at_consumption view over lease.consumed events"
```

### Task 7: views.decoder_backlog_series

**Files:**
- Create: `qsim/observe/views.py` (edit, adds function)
- Test: `tests/observe/test_views_decoder_backlog.py`

**Interfaces:**
- Consumes: `iter_events(events_path: Path) -> Iterator[dict]` (Task 4).
- Produces: `decoder_backlog_series(events_path: Path) -> list[tuple[float, int]]` — verbatim from frozen contract. **Local trace convention:** backlog = count of decoder jobs currently in system (enqueued but not yet completed/cancelled). `decoder.enqueued` increments backlog by 1; `decoder.completed` and `decoder.cancelled` each decrement by 1; `decoder.dequeued` (start of service) does not change backlog. A `(sim_time, backlog)` point is emitted on every backlog-changing event, in trace order.

- [ ] **Step 1: Write the failing test**
```python
from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.views import decoder_backlog_series


def _seed(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def test_decoder_backlog_series_tracks_jobs_in_system(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="decoder.enqueued",
              entity_id="job-0", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=1, sim_time=1.0, event_type="decoder.enqueued",
              entity_id="job-1", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=2, sim_time=2.0, event_type="decoder.dequeued",
              entity_id="job-0", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=3, sim_time=3.0, event_type="decoder.completed",
              entity_id="job-0", causal_parent_id=None, payload={}),
        Event(run_id="r", seq=4, sim_time=4.0, event_type="decoder.cancelled",
              entity_id="job-1", causal_parent_id=None, payload={}),
    ]
    path = _seed(tmp_path, "run-backlog", events)

    assert decoder_backlog_series(path) == [
        (0.0, 1),
        (1.0, 2),
        (3.0, 1),
        (4.0, 0),
    ]


def test_decoder_backlog_series_empty_on_empty_trace(tmp_path):
    path = _seed(tmp_path, "run-backlog-empty", [])
    assert decoder_backlog_series(path) == []
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/observe/test_views_decoder_backlog.py -v`
Expected: FAIL with `ImportError: cannot import name 'decoder_backlog_series' from 'qsim.observe.views'`
- [ ] **Step 3: Write minimal implementation**
```python
def decoder_backlog_series(events_path: Path) -> list[tuple[float, int]]:
    series: list[tuple[float, int]] = []
    backlog = 0
    for record in iter_events(events_path):
        event_type = record["event_type"]
        if event_type == "decoder.enqueued":
            backlog += 1
        elif event_type in ("decoder.completed", "decoder.cancelled"):
            backlog -= 1
        else:
            continue
        series.append((record["sim_time"], backlog))
    return series
```
(Append to `qsim/observe/views.py`.)
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/observe/test_views_decoder_backlog.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/observe/views.py tests/observe/test_views_decoder_backlog.py
git commit -m "feat(observe): decoder_backlog_series view tracking jobs in system"
```

### Task 8: views.deadline_compliance

**Files:**
- Create: `qsim/observe/views.py` (edit, adds function)
- Test: `tests/observe/test_views_deadline_compliance.py`

**Interfaces:**
- Consumes: `compute_work_accounting(events_path: Path) -> WorkAccounting` (Task 4).
- Produces: `deadline_compliance(events_path: Path) -> dict[str, float]` — verbatim from frozen contract. Returns fractions of **offered** work (§11 normalization) with fixed keys `"completed_in_deadline"`, `"completed_late"`, `"failed"`, `"dropped"`; all `0.0` when `offered == 0`.

- [ ] **Step 1: Write the failing test**
```python
from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.views import deadline_compliance


def _seed(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def test_deadline_compliance_reports_fractions_of_offered(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="round.arrived",
              entity_id="round-0", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=1, sim_time=0.1, event_type="round.arrived",
              entity_id="round-1", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=2, sim_time=0.2, event_type="round.arrived",
              entity_id="round-2", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=3, sim_time=0.3, event_type="round.arrived",
              entity_id="round-3", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=4, sim_time=0.4, event_type="round.completed_in_deadline",
              entity_id="round-0", causal_parent_id=None, payload={"success_probability": 0.9}),
        Event(run_id="r", seq=5, sim_time=0.5, event_type="round.completed_late",
              entity_id="round-1", causal_parent_id=None, payload={"success_probability": 0.9}),
        Event(run_id="r", seq=6, sim_time=0.6, event_type="round.failed",
              entity_id="round-2", causal_parent_id=None, payload={"success_probability": 0.1}),
        Event(run_id="r", seq=7, sim_time=0.7, event_type="round.dropped",
              entity_id="round-3", causal_parent_id=None, payload={}),
    ]
    path = _seed(tmp_path, "run-compliance", events)

    assert deadline_compliance(path) == {
        "completed_in_deadline": 0.25,
        "completed_late": 0.25,
        "failed": 0.25,
        "dropped": 0.25,
    }


def test_deadline_compliance_all_zero_on_empty_trace(tmp_path):
    path = _seed(tmp_path, "run-compliance-empty", [])

    assert deadline_compliance(path) == {
        "completed_in_deadline": 0.0,
        "completed_late": 0.0,
        "failed": 0.0,
        "dropped": 0.0,
    }
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/observe/test_views_deadline_compliance.py -v`
Expected: FAIL with `ImportError: cannot import name 'deadline_compliance' from 'qsim.observe.views'`
- [ ] **Step 3: Write minimal implementation**
```python
def deadline_compliance(events_path: Path) -> dict[str, float]:
    wa = compute_work_accounting(events_path)
    if wa.offered == 0:
        return {
            "completed_in_deadline": 0.0,
            "completed_late": 0.0,
            "failed": 0.0,
            "dropped": 0.0,
        }
    return {
        "completed_in_deadline": wa.completed_in_deadline / wa.offered,
        "completed_late": wa.completed_late / wa.offered,
        "failed": wa.failed / wa.offered,
        "dropped": wa.dropped / wa.offered,
    }
```
(Append to `qsim/observe/views.py`.)
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/observe/test_views_deadline_compliance.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/observe/views.py tests/observe/test_views_deadline_compliance.py
git commit -m "feat(observe): deadline_compliance view, offered-normalized"
```

### Task 9: views.resource_utilization

**Files:**
- Create: `qsim/observe/views.py` (edit, adds function)
- Test: `tests/observe/test_views_resource_utilization.py`

**Interfaces:**
- Consumes: `iter_events(events_path: Path) -> Iterator[dict]` (Task 4).
- Produces: `resource_utilization(events_path: Path) -> dict[str, float]` — verbatim from frozen contract; task-local helper `_path_key(path_id_payload) -> str`. **Local trace convention:** `reservation.acquired`/`reservation.released` payloads carry `payload["path_id"]` as a two-element list of `[module_id, port_index]` pairs (JSON form of §7/entities' `PathId`) and `payload["holder_id"]`. Utilization per path = total busy time (`released.sim_time - acquired.sim_time`, summed over all acquire/release pairs on that path) divided by the run's total observed duration (`max(sim_time)` over the whole trace). Empty trace yields `{}`.

- [ ] **Step 1: Write the failing test**
```python
from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.views import resource_utilization


def _seed(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def test_resource_utilization_computes_busy_fraction_per_path(tmp_path):
    path_ab = [["modA", 0], ["modB", 1]]
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="reservation.acquired",
              entity_id="resv-0", causal_parent_id=None,
              payload={"path_id": path_ab, "holder_id": "round-0"}),
        Event(run_id="r", seq=1, sim_time=4.0, event_type="reservation.released",
              entity_id="resv-0", causal_parent_id=None,
              payload={"path_id": path_ab, "holder_id": "round-0"}),
        Event(run_id="r", seq=2, sim_time=10.0, event_type="round.arrived",
              entity_id="round-1", causal_parent_id=None, payload={"retry_ordinal": 0}),
    ]
    path = _seed(tmp_path, "run-util", events)

    utilization = resource_utilization(path)

    assert utilization == {"modA:0|modB:1": 0.4}  # busy 4s of 10s total run


def test_resource_utilization_empty_on_empty_trace(tmp_path):
    path = _seed(tmp_path, "run-util-empty", [])
    assert resource_utilization(path) == {}
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/observe/test_views_resource_utilization.py -v`
Expected: FAIL with `ImportError: cannot import name 'resource_utilization' from 'qsim.observe.views'`
- [ ] **Step 3: Write minimal implementation**
```python
def _path_key(path_id_payload) -> str:
    return "|".join(f"{module_id}:{port_index}" for module_id, port_index in path_id_payload)


def resource_utilization(events_path: Path) -> dict[str, float]:
    records = list(iter_events(events_path))
    if not records:
        return {}
    total_duration = max(record["sim_time"] for record in records)
    busy_time: dict[str, float] = {}
    open_acquisitions: dict[str, float] = {}
    for record in records:
        if record["event_type"] == "reservation.acquired":
            key = _path_key(record["payload"]["path_id"])
            open_acquisitions[key] = record["sim_time"]
        elif record["event_type"] == "reservation.released":
            key = _path_key(record["payload"]["path_id"])
            acquired_at = open_acquisitions.pop(key, record["sim_time"])
            busy_time[key] = busy_time.get(key, 0.0) + (record["sim_time"] - acquired_at)
    if total_duration == 0:
        return {key: 0.0 for key in busy_time}
    return {key: duration / total_duration for key, duration in busy_time.items()}
```
(Append to `qsim/observe/views.py`.)
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/observe/test_views_resource_utilization.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/observe/views.py tests/observe/test_views_resource_utilization.py
git commit -m "feat(observe): resource_utilization view over switch-path reservation lifecycle"
```

### Task 10: views.logical_error_proxy

**Files:**
- Create: `qsim/observe/views.py` (edit, adds function)
- Test: `tests/observe/test_views_logical_error_proxy.py`

**Interfaces:**
- Consumes: `compute_work_accounting(events_path: Path) -> WorkAccounting`, `iter_events(events_path: Path) -> Iterator[dict]` (Task 4).
- Produces: `logical_error_proxy(events_path: Path) -> float` — verbatim from frozen contract. **Local trace convention:** every `round.failed` event's `payload["success_probability"]` carries the `RoundSuccessModel` score computed at execution time for that failed round. Per §11, the proxy is `sum_over_failed_rounds(1 - success_probability) / offered` — normalized by **offered**, not by attempts or failures, so it cannot be shrunk merely by dropping (never scoring) work; `0.0` when `offered == 0` or there are no failures.

- [ ] **Step 1: Write the failing test**
```python
import pytest

from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.views import logical_error_proxy


def _seed(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def test_logical_error_proxy_aggregates_failure_weight_over_offered(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="round.arrived",
              entity_id="round-0", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=1, sim_time=0.1, event_type="round.arrived",
              entity_id="round-1", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=2, sim_time=0.2, event_type="round.arrived",
              entity_id="round-2", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=3, sim_time=0.3, event_type="round.arrived",
              entity_id="round-3", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=4, sim_time=0.4, event_type="round.completed_in_deadline",
              entity_id="round-0", causal_parent_id=None, payload={"success_probability": 0.95}),
        Event(run_id="r", seq=5, sim_time=0.5, event_type="round.failed",
              entity_id="round-1", causal_parent_id=None, payload={"success_probability": 0.4}),
        Event(run_id="r", seq=6, sim_time=0.6, event_type="round.failed",
              entity_id="round-2", causal_parent_id=None, payload={"success_probability": 0.0}),
        Event(run_id="r", seq=7, sim_time=0.7, event_type="round.dropped",
              entity_id="round-3", causal_parent_id=None, payload={}),
    ]
    path = _seed(tmp_path, "run-error-proxy", events)

    # failures contribute (1 - 0.4) + (1 - 0.0) = 1.6, over 4 offered rounds
    assert logical_error_proxy(path) == pytest.approx(1.6 / 4)


def test_logical_error_proxy_is_zero_with_no_failures(tmp_path):
    events = [
        Event(run_id="r", seq=0, sim_time=0.0, event_type="round.arrived",
              entity_id="round-0", causal_parent_id=None, payload={"retry_ordinal": 0}),
        Event(run_id="r", seq=1, sim_time=0.1, event_type="round.completed_in_deadline",
              entity_id="round-0", causal_parent_id=None, payload={"success_probability": 0.99}),
    ]
    path = _seed(tmp_path, "run-error-proxy-zero", events)

    assert logical_error_proxy(path) == 0.0


def test_logical_error_proxy_is_zero_on_empty_trace(tmp_path):
    path = _seed(tmp_path, "run-error-proxy-empty", [])
    assert logical_error_proxy(path) == 0.0
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/observe/test_views_logical_error_proxy.py -v`
Expected: FAIL with `ImportError: cannot import name 'logical_error_proxy' from 'qsim.observe.views'`
- [ ] **Step 3: Write minimal implementation**
```python
def logical_error_proxy(events_path: Path) -> float:
    wa = compute_work_accounting(events_path)
    if wa.offered == 0:
        return 0.0
    total_error_weight = sum(
        1.0 - record["payload"]["success_probability"]
        for record in iter_events(events_path)
        if record["event_type"] == "round.failed"
    )
    return total_error_weight / wa.offered
```
(Append to `qsim/observe/views.py`.)
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/observe/test_views_logical_error_proxy.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/observe/views.py tests/observe/test_views_logical_error_proxy.py
git commit -m "feat(observe): logical_error_proxy view, offered-normalized RoundSuccessModel-scored failures"
```

### Task 11: views.shared_key_fraction — paired-comparison view

**Files:**
- Create: `qsim/observe/views.py` (edit, adds function)
- Test: `tests/observe/test_views_shared_key_fraction.py`

**Interfaces:**
- Consumes: `iter_events(events_path: Path) -> Iterator[dict]` (Task 4); `draw.sampled` event payload shape given verbatim in the frozen contract's `EVENT_TYPES` comment: `{"stream": str, "key": list, "uniform": float}`.
- Produces: `shared_key_fraction(events_path_a: Path, events_path_b: Path, window_s: float) -> list[tuple[float, float]]` — verbatim from frozen contract; task-local helpers `_draw_key(record) -> tuple`, `_to_hashable(value)`. Per §10: buckets `draw.sampled` events from both runs into `window_s`-wide windows keyed by `floor(sim_time / window_s) * window_s`; for each non-empty window, reports the Jaccard shared-key fraction `|keys_a ∩ keys_b| / |keys_a ∪ keys_b|` where a "key" is the `(stream, key)` pair. Windows with draws in neither run are omitted; result is sorted by window start.

- [ ] **Step 1: Write the failing test**
```python
import pytest

from qsim.core.trace import Event
from qsim.observe.run_dir import RunDirWriter
from qsim.observe.views import shared_key_fraction


def _seed(tmp_path, run_id, events):
    writer = RunDirWriter(root=tmp_path, run_id=run_id)
    for e in events:
        writer.append_event(e)
    return writer.events_path


def _draw(run_id, seq, sim_time, stream, key):
    return Event(
        run_id=run_id, seq=seq, sim_time=sim_time, event_type="draw.sampled",
        entity_id=stream, causal_parent_id=None,
        payload={"stream": stream, "key": list(key), "uniform": 0.5},
    )


def test_shared_key_fraction_known_overlap_per_window(tmp_path):
    # Window 0 [0,10): A draws keys {r1, r2}; B draws keys {r1, r4}.
    #   intersection = {r1} (size 1), union = {r1, r2, r4} (size 3) -> 1/3
    # Window 1 [10,20): A and B both draw {r3} -> intersection == union -> 1.0
    events_a = [
        _draw("a", 0, 1.0, "herald", ("herald", "r1", "p1", 1)),
        _draw("a", 1, 2.0, "herald", ("herald", "r2", "p1", 1)),
        _draw("a", 2, 15.0, "herald", ("herald", "r3", "p1", 1)),
    ]
    events_b = [
        _draw("b", 0, 1.0, "herald", ("herald", "r1", "p1", 1)),
        _draw("b", 1, 3.0, "herald", ("herald", "r4", "p1", 1)),
        _draw("b", 2, 16.0, "herald", ("herald", "r3", "p1", 1)),
    ]
    path_a = _seed(tmp_path, "run-a", events_a)
    path_b = _seed(tmp_path, "run-b", events_b)

    result = shared_key_fraction(path_a, path_b, window_s=10.0)

    assert result == [
        pytest.approx((0.0, 1 / 3)),
        pytest.approx((10.0, 1.0)),
    ]


def test_shared_key_fraction_no_draws_returns_empty(tmp_path):
    path_a = _seed(tmp_path, "run-a-empty", [])
    path_b = _seed(tmp_path, "run-b-empty", [])

    assert shared_key_fraction(path_a, path_b, window_s=10.0) == []
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/observe/test_views_shared_key_fraction.py -v`
Expected: FAIL with `ImportError: cannot import name 'shared_key_fraction' from 'qsim.observe.views'`
- [ ] **Step 3: Write minimal implementation**
```python
def _to_hashable(value):
    if isinstance(value, list):
        return tuple(_to_hashable(v) for v in value)
    return value


def _draw_key(record: dict):
    return (record["payload"]["stream"], _to_hashable(record["payload"]["key"]))


def shared_key_fraction(events_path_a: Path, events_path_b: Path,
                         window_s: float) -> list[tuple[float, float]]:
    windows: dict[float, tuple[set, set]] = {}
    for events_path, side in ((events_path_a, 0), (events_path_b, 1)):
        for record in iter_events(events_path):
            if record["event_type"] != "draw.sampled":
                continue
            window_start = (record["sim_time"] // window_s) * window_s
            bucket = windows.setdefault(window_start, (set(), set()))
            bucket[side].add(_draw_key(record))

    result = []
    for window_start in sorted(windows):
        keys_a, keys_b = windows[window_start]
        union = keys_a | keys_b
        if not union:
            continue
        intersection = keys_a & keys_b
        result.append((window_start, len(intersection) / len(union)))
    return result
```
(Append to `qsim/observe/views.py`.)
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/observe/test_views_shared_key_fraction.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/observe/views.py tests/observe/test_views_shared_key_fraction.py
git commit -m "feat(observe): shared_key_fraction paired-comparison view over windowed keyed draws"
```

---

## Section 7 of 8 — core/engine.py (the DES run loop, §4's data flow end to end)

**Note:** this section's scheduler call sites (Tasks 1, 2, 3, 6) are written against the placeholder Scheduler protocol and need reconciliation with Section 4's richer protocol per the "Known Integration Gap" callout above before Task 8 (end-to-end integration) can pass.

### Task 1: Engine construction, DES loop, and arrival/admission dispatch

**Files:**
- Create: `qsim/core/engine.py`
- Test: `tests/core/test_engine.py`

**Interfaces:**
- Consumes: `qsim.core.clock.SimClock`, `qsim.core.event_heap.EventHeap`/`HeapEntry`, `qsim.core.trace.TraceBus`/`Event`/`EventId`, `qsim.core.invariants.InvariantChecker`, `qsim.core.state.EngineState`/`ModelBundle`, `qsim.policies.protocol.Scheduler`/`AdmissionDecision`, `qsim.workload.generator.WorkloadGenerator`, `qsim.entities.PortId`/`RoundState`/`SyndromeRound`, `qsim.experiments.config.RunConfig` (type-only, `TYPE_CHECKING`). Assumes `qsim/entities/__init__.py` re-exports all entity names flatly (`from qsim.entities import X`) since the contract only specifies `qsim/entities/*.py` without per-file names — flagged as a cross-package assumption.
- Produces: `qsim.core.engine.Engine` (constructor per frozen signature, `run_to(max_sim_time_s: float) -> None`), task-local types `_ArrivalPayload`, `_RoundContext`, and module function `_synthesize_ports(switch_capacity_c: int) -> list[PortId]` — a task-local port-topology synthesis that fills a gap in the frozen contract (`RunConfig` has no topology field). This is a flagged finding, not a silent assumption: later tasks in this file use `Engine._ports` and `Engine._port_pair_counter` for endpoint selection.

- [ ] **Step 1: Write the failing test**
```python
# tests/core/test_engine.py
from qsim.entities import CalibrationEpoch, CoherenceClass
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
from qsim.experiments.config import RunConfig

RUN_SEED = 42
ARRIVAL_RATE_HZ = 1.0
LEASES_PER_ROUND = 1
DEADLINE_SLACK_S = 10.0


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
        round_success=LogisticRoundSuccessModel(),
        decoder_service=ExponentialDecoderServiceModel(),
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


def test_first_arrival_deferred_and_dropped_when_capacity_is_zero():
    # Peek pattern: derive expected values from the same real, keyed,
    # deterministic components the engine uses internally, rather than
    # hardcoding magic numbers.
    first_round = make_workload().next_arrival(0.0, 1)
    expected_retry = make_workload().on_outcome(first_round, False)

    events = []
    trace = TraceBus(run_id="test-run")
    trace.subscribe(events.append)
    engine = Engine(
        config=make_config(switch_capacity_c=0), scheduler=S0Scheduler(),
        models=make_models(), workload=make_workload(),
        trace=trace, invariants=InvariantChecker(),
    )

    engine.run_to(first_round.arrival_time + 1e-6)

    types = [e.event_type for e in events]
    assert types[0] == "round.arrived"
    assert types[1] == "round.deferred"
    assert events[0].entity_id == first_round.round_id
    assert events[1].causal_parent_id == (events[0].run_id, events[0].seq)
    if expected_retry is None:
        assert types[2] == "round.dropped"
        assert events[2].entity_id == first_round.round_id
    else:
        assert types[2] == "round.arrived"
        assert events[2].entity_id == expected_retry.round_id
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_engine.py::test_first_arrival_deferred_and_dropped_when_capacity_is_zero -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.engine'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/core/engine.py
"""The DES run loop implementing §4's end-to-end data flow."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qsim.core.clock import SimClock
from qsim.core.event_heap import EventHeap
from qsim.core.invariants import InvariantChecker
from qsim.core.state import EngineState, ModelBundle
from qsim.core.trace import Event, EventId, TraceBus
from qsim.entities import PortId, RoundState, SyndromeRound
from qsim.policies.protocol import Scheduler
from qsim.workload.generator import WorkloadGenerator

if TYPE_CHECKING:
    from qsim.experiments.config import RunConfig


def _synthesize_ports(switch_capacity_c: int) -> list[PortId]:
    """Task-local topology synthesis. The frozen contract's RunConfig has no
    port/module topology field; this fills that gap deterministically so §7
    endpoint-exclusivity has something concrete to contend over. Flagged as
    a contract gap for the experiments/entities sections to reconcile."""
    count = max(2, switch_capacity_c * 2)
    return [PortId(module_id=f"M{i}", port_index=0) for i in range(count)]


@dataclass(frozen=True)
class _ArrivalPayload:
    round: SyndromeRound
    causal_parent_id: EventId | None


@dataclass
class _RoundContext:
    round: SyndromeRound
    causal_parent_id: EventId | None


class Engine:
    def __init__(self, config: "RunConfig", scheduler: Scheduler,
                 models: ModelBundle, workload: WorkloadGenerator,
                 trace: TraceBus, invariants: InvariantChecker) -> None:
        self._config = config
        self._scheduler = scheduler
        self._workload = workload
        self._trace = trace
        self._invariants = invariants
        self._clock = SimClock()
        self._heap = EventHeap()
        self._state = EngineState(
            now=0.0,
            epoch=config.epoch,
            models=models,
            decoder_backlog=0,
            active_reservations={},
            pool={},
            switch_capacity_c=config.switch_capacity_c,
            hold_until_consumption=config.hold_until_consumption,
        )
        self._ports = _synthesize_ports(config.switch_capacity_c)
        self._port_pair_counter = 0
        self._arrival_index = 0
        self._round_contexts: dict[str, _RoundContext] = {}

    def _publish(self, event_type: str, entity_id: str,
                 causal_parent_id: EventId | None, payload: dict) -> EventId:
        event_id = self._trace.publish(event_type, entity_id, causal_parent_id, payload)
        event = Event(
            run_id=event_id[0], seq=event_id[1], sim_time=self._state.now,
            event_type=event_type, entity_id=entity_id,
            causal_parent_id=causal_parent_id, payload=payload,
        )
        self._invariants.observe(event, self._state)
        return event_id

    def _schedule_next_arrival(self, after_time: float) -> None:
        self._arrival_index += 1
        next_round = self._workload.next_arrival(after_time, self._arrival_index)
        self._heap.push(next_round.arrival_time, _ArrivalPayload(next_round, None))

    def run_to(self, max_sim_time_s: float) -> None:
        self._schedule_next_arrival(0.0)
        while len(self._heap) > 0:
            entry = self._heap.pop()
            if entry.time > max_sim_time_s:
                break
            self._clock.advance_to(entry.time)
            self._state.now = entry.time
            self._dispatch(entry.payload)

    def _dispatch(self, payload: object) -> None:
        if isinstance(payload, _ArrivalPayload):
            self._on_arrival(payload)
        else:
            raise TypeError(f"unknown event payload type: {type(payload)!r}")

    def _on_arrival(self, payload: _ArrivalPayload) -> None:
        round_ = payload.round
        arrived_id = self._publish(
            "round.arrived", round_.round_id, payload.causal_parent_id,
            {"deadline": round_.deadline, "retry_ordinal": round_.retry_ordinal},
        )
        self._schedule_next_arrival(round_.arrival_time)
        self._round_contexts[round_.round_id] = _RoundContext(round_, arrived_id)
        decision = self._scheduler.on_round_request(round_, self._state)
        if decision.admit:
            round_.state = RoundState.ADMITTED
            admitted_id = self._publish("round.admitted", round_.round_id, arrived_id,
                                        {"reason": decision.reason})
            self._begin_lease_acquisition(round_, admitted_id)
        else:
            round_.state = RoundState.DEFERRED
            deferred_id = self._publish("round.deferred", round_.round_id, arrived_id,
                                        {"reason": decision.reason})
            self._retry_or_drop(round_, deferred_id)

    def _retry_or_drop(self, round_: SyndromeRound, causal_parent_id: EventId) -> None:
        retry_round = self._workload.on_outcome(round_, False)
        if retry_round is not None:
            self._heap.push(retry_round.arrival_time,
                            _ArrivalPayload(retry_round, causal_parent_id))
        else:
            round_.state = RoundState.DROPPED
            self._publish("round.dropped", round_.round_id, causal_parent_id, {})
        del self._round_contexts[round_.round_id]

    def _begin_lease_acquisition(self, round_: SyndromeRound, causal_parent_id: EventId) -> None:
        # Replaced in Task 2 with real path-allocation logic.
        self._round_contexts[round_.round_id].causal_parent_id = causal_parent_id
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_engine.py::test_first_arrival_deferred_and_dropped_when_capacity_is_zero -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/core/engine.py tests/core/test_engine.py
git commit -m "feat: engine DES loop skeleton with arrival and admission dispatch"
```

### Task 2: Path allocation and switch-reservation lifecycle

**Files:**
- Modify: `qsim/core/engine.py`
- Test: `tests/core/test_engine_reservation.py`

**Interfaces:**
- Consumes: `qsim.policies.protocol.LeaseRequest`, `Scheduler.allocate_path(request: LeaseRequest, state: EngineState) -> PathId | None`, `qsim.entities.PathId`/`make_path_id`/`SwitchPathReservation`/`ReservationState`/`EntanglementLease`/`LeaseState`.
- Produces: task-local `_ReservationActivatePayload`, `Engine._endpoints_for`, `Engine._begin_lease_acquisition` (replaces Task 1's stub), `Engine._acquire_path`, `Engine._on_reservation_active` (stub, replaced in Task 3), `Engine._fail_round` (minimal version: publishes `round.failed` + retries via workload; replaced in Task 7 to run the full §5 cascade first).

- [ ] **Step 1: Write the failing test**
```python
# tests/core/test_engine_reservation.py
from tests.core.test_engine import make_config, make_models, make_workload
from qsim.core.trace import TraceBus
from qsim.core.invariants import InvariantChecker
from qsim.core.engine import Engine
from qsim.policies.s0 import S0Scheduler
from qsim.entities import ReservationState


def test_admitted_round_acquires_configures_and_activates_a_path():
    workload = make_workload()
    first_round = workload.next_arrival(0.0, 1)
    config = make_config(switch_capacity_c=2)
    config = config.__class__(**{**config.__dict__, "reconfig_delay_s": 0.5})

    events = []
    trace = TraceBus(run_id="test-run")
    trace.subscribe(events.append)
    engine = Engine(config=config, scheduler=S0Scheduler(), models=make_models(),
                    workload=make_workload(), trace=trace, invariants=InvariantChecker())

    engine.run_to(first_round.arrival_time + config.reconfig_delay_s + 1e-6)

    types = [e.event_type for e in events]
    assert types[:2] == ["round.arrived", "round.admitted"]
    assert "reservation.acquired" in types
    assert "reservation.configuring" in types
    assert "reservation.active" in types

    acquired = events[types.index("reservation.acquired")]
    configuring = events[types.index("reservation.configuring")]
    active = events[types.index("reservation.active")]
    assert acquired.sim_time == configuring.sim_time == first_round.arrival_time
    assert active.sim_time == first_round.arrival_time + config.reconfig_delay_s
    assert configuring.causal_parent_id == (acquired.run_id, acquired.seq)
    assert active.causal_parent_id == (configuring.run_id, configuring.seq)

    path_id = engine._round_contexts[first_round.round_id].reservations[
        next(iter(engine._round_contexts[first_round.round_id].reservations))
    ].path_id
    reservation = engine._state.active_reservations[path_id]
    assert reservation.state == ReservationState.ACTIVE
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_engine_reservation.py -v`
Expected: FAIL with `AttributeError: 'Engine' object has no attribute '_endpoints_for'` (or `NotImplementedError` from `_begin_lease_acquisition`)
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/core/engine.py — add imports
from qsim.entities import (
    EntanglementLease, LeaseState, PathId, ReservationState,
    SwitchPathReservation, make_path_id,
)
from qsim.policies.protocol import LeaseRequest

# qsim/core/engine.py — add task-local payload type near _ArrivalPayload
@dataclass(frozen=True)
class _ReservationActivatePayload:
    path_id: PathId
    round_id: str
    lease_id: str
    causal_parent_id: EventId | None

# qsim/core/engine.py — extend _RoundContext
@dataclass
class _RoundContext:
    round: SyndromeRound
    causal_parent_id: EventId | None
    reservations: dict[str, SwitchPathReservation] = field(default_factory=dict)
    leases: dict[str, EntanglementLease] = field(default_factory=dict)

# qsim/core/engine.py — add `from dataclasses import dataclass, field` (replace existing import line)

# qsim/core/engine.py — Engine: replace _begin_lease_acquisition, add helpers
    def _endpoints_for(self, round_id: str, ordinal: int) -> tuple[PortId, PortId]:
        n = len(self._ports)
        idx = self._port_pair_counter % n
        self._port_pair_counter += 1
        return (self._ports[idx], self._ports[(idx + 1) % n])

    def _begin_lease_acquisition(self, round_: SyndromeRound, causal_parent_id: EventId) -> None:
        ctx = self._round_contexts[round_.round_id]
        ctx.causal_parent_id = causal_parent_id
        for ordinal, lease_id in enumerate(round_.lease_ids):
            endpoints = self._endpoints_for(round_.round_id, ordinal)
            request = LeaseRequest(round_id=round_.round_id, endpoints=endpoints)
            self._acquire_path(round_, lease_id, request, causal_parent_id)

    def _acquire_path(self, round_: SyndromeRound, lease_id: str,
                      request: LeaseRequest, causal_parent_id: EventId) -> None:
        path_id = self._scheduler.allocate_path(request, self._state)
        if path_id is None:
            self._fail_round(round_, "no_path_available", causal_parent_id)
            return
        reservation = SwitchPathReservation(
            path_id=path_id, holder_id=round_.round_id,
            acquired_at=self._state.now, state=ReservationState.ACQUIRED,
        )
        self._state.active_reservations[path_id] = reservation
        self._round_contexts[round_.round_id].reservations[lease_id] = reservation
        entity_id = f"{path_id[0].module_id}:{path_id[0].port_index}->{path_id[1].module_id}:{path_id[1].port_index}"
        acquired_id = self._publish("reservation.acquired", entity_id, causal_parent_id,
                                    {"round_id": round_.round_id, "lease_id": lease_id})
        reservation.state = ReservationState.CONFIGURING
        configuring_id = self._publish("reservation.configuring", entity_id, acquired_id,
                                       {"round_id": round_.round_id, "lease_id": lease_id})
        activate_at = self._state.now + self._config.reconfig_delay_s
        self._heap.push(activate_at, _ReservationActivatePayload(
            path_id=path_id, round_id=round_.round_id, lease_id=lease_id,
            causal_parent_id=configuring_id,
        ))

    def _on_reservation_active(self, payload: "_ReservationActivatePayload") -> None:
        reservation = self._state.active_reservations[payload.path_id]
        reservation.state = ReservationState.ACTIVE
        entity_id = f"{payload.path_id[0].module_id}:{payload.path_id[0].port_index}->{payload.path_id[1].module_id}:{payload.path_id[1].port_index}"
        self._publish("reservation.active", entity_id, payload.causal_parent_id,
                      {"round_id": payload.round_id, "lease_id": payload.lease_id})
        # Task 3 attaches the first heralding attempt here.

    def _fail_round(self, round_: SyndromeRound, reason: str, causal_parent_id: EventId) -> None:
        round_.state = RoundState.FAILED
        failed_id = self._publish("round.failed", round_.round_id, causal_parent_id, {"reason": reason})
        self._retry_or_drop(round_, failed_id)

# qsim/core/engine.py — Engine._dispatch: add branch
    def _dispatch(self, payload: object) -> None:
        if isinstance(payload, _ArrivalPayload):
            self._on_arrival(payload)
        elif isinstance(payload, _ReservationActivatePayload):
            self._on_reservation_active(payload)
        else:
            raise TypeError(f"unknown event payload type: {type(payload)!r}")
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_engine_reservation.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/core/engine.py tests/core/test_engine_reservation.py
git commit -m "feat: engine path allocation and switch-reservation lifecycle"
```

### Task 3: Heralding attempt loop

**Files:**
- Modify: `qsim/core/engine.py`
- Test: `tests/core/test_engine_heralding.py`

**Interfaces:**
- Consumes: `qsim.core.rng.draw_uniform`/`Draw`, `qsim.models.protocols.HeraldingModel.success_probability`/`heralded_fidelity`, `qsim.entities.EntanglementLease`/`LeaseState`.
- Produces: task-local `_HeraldAttemptPayload`, `Engine._start_heralding`, `Engine._on_herald_attempt`, `Engine._release_reservation`.

- [ ] **Step 1: Write the failing test**
```python
# tests/core/test_engine_heralding.py
from tests.core.test_engine import make_config, make_models, make_workload, make_epoch
from qsim.core.trace import TraceBus
from qsim.core.invariants import InvariantChecker
from qsim.core.state import ModelBundle
from qsim.core.engine import Engine
from qsim.core.rng import draw_uniform
from qsim.policies.s0 import S0Scheduler
from qsim.entities import LeaseState, ReservationState
from qsim.models.decay import NoDecayModel
from qsim.models.memory_access import ZeroCostMemoryAccessModel
from qsim.models.heralding import BernoulliHeraldingModel
from qsim.models.round_success import LogisticRoundSuccessModel
from qsim.models.decoder_service import ExponentialDecoderServiceModel


def _epoch_with_full_heralding():
    epoch = make_epoch()
    # Path is unknown until allocate_path runs; BernoulliHeraldingModel reads
    # epoch.heralding_p_per_path[path], so a p=1.0 default is required for
    # any path. We patch epoch via a defaultdict-like wrapper instead of
    # guessing the exact path key the scheduler will pick.
    from collections import defaultdict
    object.__setattr__(epoch, "heralding_p_per_path", defaultdict(lambda: 1.0))
    object.__setattr__(epoch, "heralded_fidelity_per_path", defaultdict(lambda: 0.9))
    return epoch


def test_heralding_succeeds_on_first_attempt_when_probability_is_one():
    workload = make_workload()
    first_round = workload.next_arrival(0.0, 1)
    config = make_config(switch_capacity_c=2)
    config = config.__class__(**{**config.__dict__, "epoch": _epoch_with_full_heralding()})

    models = ModelBundle(
        decay=NoDecayModel(), memory_access=ZeroCostMemoryAccessModel(),
        heralding=BernoulliHeraldingModel(), round_success=LogisticRoundSuccessModel(),
        decoder_service=ExponentialDecoderServiceModel(),
    )

    events = []
    trace = TraceBus(run_id="test-run")
    trace.subscribe(events.append)
    engine = Engine(config=config, scheduler=S0Scheduler(), models=models,
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
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_engine_heralding.py -v`
Expected: FAIL — `lease.heralded` never appears in `types` (heralding not wired up)
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/core/engine.py — add import
from qsim.core.rng import Draw, draw_uniform

HERALD_RETRY_INTERVAL_S = 1e-4  # task-local: gap between failed attempts

# qsim/core/engine.py — add task-local payload type
@dataclass(frozen=True)
class _HeraldAttemptPayload:
    round_id: str
    lease_id: str
    path_id: PathId
    endpoints: tuple[PortId, PortId]
    attempt_no: int
    causal_parent_id: EventId | None

# qsim/core/engine.py — Engine._on_reservation_active: replace trailing comment with a call
    def _on_reservation_active(self, payload: "_ReservationActivatePayload") -> None:
        reservation = self._state.active_reservations[payload.path_id]
        reservation.state = ReservationState.ACTIVE
        entity_id = f"{payload.path_id[0].module_id}:{payload.path_id[0].port_index}->{payload.path_id[1].module_id}:{payload.path_id[1].port_index}"
        active_id = self._publish("reservation.active", entity_id, payload.causal_parent_id,
                                  {"round_id": payload.round_id, "lease_id": payload.lease_id})
        round_ = self._round_contexts[payload.round_id].round
        lease = self._round_contexts[payload.round_id].leases.get(payload.lease_id)
        endpoints = lease.endpoints if lease is not None else None
        self._start_heralding(round_, payload.lease_id, payload.path_id, endpoints, active_id)

    def _start_heralding(self, round_: SyndromeRound, lease_id: str, path_id: PathId,
                         endpoints: tuple[PortId, PortId] | None, causal_parent_id: EventId) -> None:
        if endpoints is None:
            # First attempt: recover endpoints from the reservation's path_id
            # (round-trip through PortId pair, since PathId is that pair).
            endpoints = path_id
        attempt = _HeraldAttemptPayload(
            round_id=round_.round_id, lease_id=lease_id, path_id=path_id,
            endpoints=endpoints, attempt_no=1, causal_parent_id=causal_parent_id,
        )
        self._heap.push(self._state.now, attempt)

    def _on_herald_attempt(self, payload: "_HeraldAttemptPayload") -> None:
        round_ = self._round_contexts.get(payload.round_id)
        if round_ is None:
            return  # round already failed/cancelled; §5 cascade already released the path
        round_ = round_.round
        if self._state.now > round_.deadline:
            self._fail_round(round_, "heralding_deadline_exceeded", payload.causal_parent_id)
            return

        key = ("herald", round_.round_id, payload.endpoints, payload.attempt_no)
        u = draw_uniform(self._config.run_seed, "herald", key)
        draw_id = self._publish("draw.sampled", payload.lease_id, payload.causal_parent_id,
                                {"stream": "herald", "key": key, "uniform": u})
        p = self._state.models.heralding.success_probability(payload.path_id, self._state.epoch)

        if u < p:
            fidelity = self._state.models.heralding.heralded_fidelity(payload.path_id, self._state.epoch)
            lease = EntanglementLease(
                lease_id=payload.lease_id, endpoints=payload.endpoints, path_id=payload.path_id,
                created_at=round_.arrival_time, freshness_bound_s=round_.deadline - round_.arrival_time,
                fidelity_at_herald=fidelity, heralded_at=self._state.now, state=LeaseState.HERALDED,
            )
            self._round_contexts[round_.round_id].leases[payload.lease_id] = lease
            heralded_id = self._publish("lease.heralded", payload.lease_id, draw_id,
                                        {"round_id": round_.round_id, "fidelity_at_herald": fidelity})
            self._scheduler.on_lease_heralded(lease, self._state)
            self._release_reservation(payload.path_id, heralded_id)
        else:
            next_attempt = _HeraldAttemptPayload(
                round_id=payload.round_id, lease_id=payload.lease_id, path_id=payload.path_id,
                endpoints=payload.endpoints, attempt_no=payload.attempt_no + 1, causal_parent_id=draw_id,
            )
            self._heap.push(self._state.now + HERALD_RETRY_INTERVAL_S, next_attempt)

    def _release_reservation(self, path_id: PathId, causal_parent_id: EventId) -> None:
        if self._state.hold_until_consumption:
            return
        reservation = self._state.active_reservations.pop(path_id, None)
        if reservation is None:
            return
        reservation.state = ReservationState.RELEASED
        reservation.released_at = self._state.now
        entity_id = f"{path_id[0].module_id}:{path_id[0].port_index}->{path_id[1].module_id}:{path_id[1].port_index}"
        self._publish("reservation.released", entity_id, causal_parent_id, {})

# qsim/core/engine.py — Engine._dispatch: add branch
        elif isinstance(payload, _HeraldAttemptPayload):
            self._on_herald_attempt(payload)
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_engine_heralding.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/core/engine.py tests/core/test_engine_heralding.py
git commit -m "feat: engine heralding attempt loop with keyed Bernoulli draws"
```

### Task 4: Round assembly — decay aging and memory-access cost charging

**Files:**
- Modify: `qsim/core/engine.py`
- Test: `tests/core/test_engine_assembly.py`

**Interfaces:**
- Consumes: `qsim.models.protocols.DecayModel.retention`, `MemoryAccessModel.access_cost` (`AccessCost.electron_channel_s`, `.retention_factor`), `qsim.entities.QubitHandle`.
- Produces: task-local `Engine._on_lease_heralded_check_assembly`, `Engine._assemble_round` (returns `(lease_fidelities: list[float], memory_retentions: list[float])`), extends `_RoundContext` with `qubit_handles: dict[str, QubitHandle]`. Since `SyndromeRound.qubit_ids` gives ids but not `QubitHandle` objects or `coherence_class`/module assignment, this task synthesizes one `QubitHandle` per `qubit_id` at round-arrival time (module = the lease endpoint's module, `coherence_class=CoherenceClass.MEMORY`) — flagged as another contract gap (no `QubitHandle` source is wired anywhere else) and recorded as a task-local convention.

- [ ] **Step 1: Write the failing test**
```python
# tests/core/test_engine_assembly.py
from tests.core.test_engine import make_config, make_workload, make_epoch
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
    workload = make_workload()
    first_round = workload.next_arrival(0.0, 1)
    epoch = make_epoch()
    from collections import defaultdict
    object.__setattr__(epoch, "heralding_p_per_path", defaultdict(lambda: 1.0))
    object.__setattr__(epoch, "heralded_fidelity_per_path", defaultdict(lambda: 0.8))
    object.__setattr__(epoch, "memory_access_channel_s", 0.01)
    object.__setattr__(epoch, "memory_access_wear_rate", 0.1)
    config = make_config(switch_capacity_c=2)
    config = config.__class__(**{**config.__dict__, "epoch": epoch})

    models = ModelBundle(
        decay=NoDecayModel(), memory_access=LinearMemoryAccessModel(),
        heralding=BernoulliHeraldingModel(), round_success=LogisticRoundSuccessModel(),
        decoder_service=ExponentialDecoderServiceModel(),
    )

    trace = TraceBus(run_id="test-run")
    engine = Engine(config=config, scheduler=S0Scheduler(), models=models,
                    workload=make_workload(), trace=trace, invariants=InvariantChecker())
    engine.run_to(first_round.arrival_time + config.reconfig_delay_s + 1e-6)

    ctx = engine._round_contexts[first_round.round_id]
    lease = ctx.leases[first_round.lease_ids[0]]
    qubit = ctx.qubit_handles[first_round.qubit_ids[0]]

    lease_fidelities, memory_retentions = engine._assemble_round(ctx.round)

    decay_factor = engine._state.models.decay.retention(
        engine._state.now - lease.heralded_at, qubit.coherence_class, config.epoch,
    )
    expected_fidelity = lease.fidelity_at_herald * decay_factor
    access_cost = engine._state.models.memory_access.access_cost(qubit, config.epoch)
    expected_retention = decay_factor * access_cost.retention_factor

    assert lease_fidelities == [expected_fidelity]
    assert memory_retentions == [expected_retention]
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_engine_assembly.py -v`
Expected: FAIL with `AttributeError: 'Engine' object has no attribute '_assemble_round'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/core/engine.py — add import
from qsim.entities import CoherenceClass, QubitHandle

# qsim/core/engine.py — extend _RoundContext
@dataclass
class _RoundContext:
    round: SyndromeRound
    causal_parent_id: EventId | None
    reservations: dict[str, SwitchPathReservation] = field(default_factory=dict)
    leases: dict[str, EntanglementLease] = field(default_factory=dict)
    qubit_handles: dict[str, QubitHandle] = field(default_factory=dict)

# qsim/core/engine.py — Engine._on_arrival: after building ctx, synthesize qubit handles
    def _on_arrival(self, payload: _ArrivalPayload) -> None:
        round_ = payload.round
        arrived_id = self._publish(
            "round.arrived", round_.round_id, payload.causal_parent_id,
            {"deadline": round_.deadline, "retry_ordinal": round_.retry_ordinal},
        )
        self._schedule_next_arrival(round_.arrival_time)
        ctx = _RoundContext(round_, arrived_id)
        for qubit_id in round_.qubit_ids:
            ctx.qubit_handles[qubit_id] = QubitHandle(
                qubit_id=qubit_id, module_id=self._ports[0].module_id,
                coherence_class=CoherenceClass.MEMORY, calibration_epoch=self._state.epoch,
            )
        self._round_contexts[round_.round_id] = ctx
        decision = self._scheduler.on_round_request(round_, self._state)
        if decision.admit:
            round_.state = RoundState.ADMITTED
            admitted_id = self._publish("round.admitted", round_.round_id, arrived_id,
                                        {"reason": decision.reason})
            self._begin_lease_acquisition(round_, admitted_id)
        else:
            round_.state = RoundState.DEFERRED
            deferred_id = self._publish("round.deferred", round_.round_id, arrived_id,
                                        {"reason": decision.reason})
            self._retry_or_drop(round_, deferred_id)

    def _assemble_round(self, round_: SyndromeRound) -> tuple[list[float], list[float]]:
        ctx = self._round_contexts[round_.round_id]
        lease_fidelities: list[float] = []
        memory_retentions: list[float] = []
        for lease_id, qubit_id in zip(round_.lease_ids, round_.qubit_ids):
            lease = ctx.leases[lease_id]
            qubit = ctx.qubit_handles[qubit_id]
            age_s = self._state.now - lease.heralded_at
            decay_factor = self._state.models.decay.retention(
                age_s, qubit.coherence_class, self._state.epoch,
            )
            decayed_fidelity = lease.fidelity_at_herald * decay_factor
            access_cost = self._state.models.memory_access.access_cost(qubit, self._state.epoch)
            qubit.access_count += 1
            lease_fidelities.append(decayed_fidelity)
            memory_retentions.append(decay_factor * access_cost.retention_factor)
        return lease_fidelities, memory_retentions
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_engine_assembly.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/core/engine.py tests/core/test_engine_assembly.py
git commit -m "feat: engine round assembly with decay aging and memory-access costing"
```

### Task 5: Decoder job lifecycle

**Files:**
- Modify: `qsim/core/engine.py`
- Test: `tests/core/test_engine_decoder.py`

**Interfaces:**
- Consumes: `qsim.entities.DecoderJob`, `qsim.models.protocols.DecoderServiceModel.service_time_s(job, backlog, draw)`, `qsim.core.rng.Draw`/`draw_uniform`.
- Produces: task-local `_DecoderCompletionPayload`, `Engine._enqueue_decoder_job`, `Engine._on_decoder_completion`. Extends `_RoundContext` with `decoder_job_id: str | None = None`. All leases heralded triggers assembly+enqueue: `Engine._on_lease_heralded_check_assembly` replaces the direct call site in `_on_herald_attempt` (Task 3) that published `lease.heralded` — modified here to check whether all of the round's leases are now heralded before calling `_enqueue_decoder_job`.

- [ ] **Step 1: Write the failing test**
```python
# tests/core/test_engine_decoder.py
from tests.core.test_engine import make_config, make_workload, make_epoch
from qsim.core.trace import TraceBus
from qsim.core.invariants import InvariantChecker
from qsim.core.state import ModelBundle
from qsim.core.engine import Engine
from qsim.core.rng import draw_uniform
from qsim.policies.s0 import S0Scheduler
from qsim.models.decay import NoDecayModel
from qsim.models.memory_access import ZeroCostMemoryAccessModel
from qsim.models.heralding import BernoulliHeraldingModel
from qsim.models.round_success import LogisticRoundSuccessModel
from qsim.models.decoder_service import ExponentialDecoderServiceModel


def _full_success_epoch():
    epoch = make_epoch()
    from collections import defaultdict
    object.__setattr__(epoch, "heralding_p_per_path", defaultdict(lambda: 1.0))
    object.__setattr__(epoch, "heralded_fidelity_per_path", defaultdict(lambda: 0.95))
    object.__setattr__(epoch, "decoder_service_rate", 1000.0)
    return epoch


def test_decoder_job_enqueued_and_completes_after_all_leases_herald():
    workload = make_workload()
    first_round = workload.next_arrival(0.0, 1)
    config = make_config(switch_capacity_c=2)
    config = config.__class__(**{**config.__dict__, "epoch": _full_success_epoch()})
    models = ModelBundle(
        decay=NoDecayModel(), memory_access=ZeroCostMemoryAccessModel(),
        heralding=BernoulliHeraldingModel(), round_success=LogisticRoundSuccessModel(),
        decoder_service=ExponentialDecoderServiceModel(),
    )

    events = []
    trace = TraceBus(run_id="test-run")
    trace.subscribe(events.append)
    engine = Engine(config=config, scheduler=S0Scheduler(), models=models,
                    workload=make_workload(), trace=trace, invariants=InvariantChecker())
    engine.run_to(first_round.arrival_time + config.reconfig_delay_s + 10.0)

    types = [e.event_type for e in events]
    assert "decoder.enqueued" in types
    assert "decoder.completed" in types
    enqueued = events[types.index("decoder.enqueued")]
    completed = events[types.index("decoder.completed")]
    assert completed.sim_time > enqueued.sim_time
    assert completed.causal_parent_id is not None

    ctx = engine._round_contexts.get(first_round.round_id)
    # round context is only cleared on terminal outcome (Task 6); decoder
    # job id must have been recorded on it while present
    assert enqueued.entity_id == completed.entity_id
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_engine_decoder.py -v`
Expected: FAIL — `decoder.enqueued` never appears (lease-heralded assembly trigger not wired)
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/core/engine.py — add import
from qsim.entities import DecoderJob

# qsim/core/engine.py — extend _RoundContext
@dataclass
class _RoundContext:
    round: SyndromeRound
    causal_parent_id: EventId | None
    reservations: dict[str, SwitchPathReservation] = field(default_factory=dict)
    leases: dict[str, EntanglementLease] = field(default_factory=dict)
    qubit_handles: dict[str, QubitHandle] = field(default_factory=dict)
    decoder_job: DecoderJob | None = None

# qsim/core/engine.py — add task-local payload type
@dataclass(frozen=True)
class _DecoderCompletionPayload:
    job_id: str
    round_id: str
    causal_parent_id: EventId | None

# qsim/core/engine.py — Engine._on_herald_attempt: after publishing lease.heralded
# and releasing the reservation, check for round assembly readiness instead
# of returning directly. Replace the success branch's tail with:
        if u < p:
            fidelity = self._state.models.heralding.heralded_fidelity(payload.path_id, self._state.epoch)
            lease = EntanglementLease(
                lease_id=payload.lease_id, endpoints=payload.endpoints, path_id=payload.path_id,
                created_at=round_.arrival_time, freshness_bound_s=round_.deadline - round_.arrival_time,
                fidelity_at_herald=fidelity, heralded_at=self._state.now, state=LeaseState.HERALDED,
            )
            self._round_contexts[round_.round_id].leases[payload.lease_id] = lease
            heralded_id = self._publish("lease.heralded", payload.lease_id, draw_id,
                                        {"round_id": round_.round_id, "fidelity_at_herald": fidelity})
            self._scheduler.on_lease_heralded(lease, self._state)
            self._release_reservation(payload.path_id, heralded_id)
            self._check_assembly(round_, heralded_id)
        else:

# qsim/core/engine.py — Engine: add assembly-trigger and decoder methods
    def _check_assembly(self, round_: SyndromeRound, causal_parent_id: EventId) -> None:
        ctx = self._round_contexts[round_.round_id]
        if len(ctx.leases) < len(round_.lease_ids):
            return  # still waiting on other leases to herald
        if not all(lease.state == LeaseState.HERALDED for lease in ctx.leases.values()):
            return
        self._enqueue_decoder_job(round_, causal_parent_id)

    def _enqueue_decoder_job(self, round_: SyndromeRound, causal_parent_id: EventId) -> None:
        ctx = self._round_contexts[round_.round_id]
        job = DecoderJob(job_id=f"{round_.round_id}:D", round_id=round_.round_id,
                         priority=0, enqueue_time=self._state.now)
        ctx.decoder_job = job
        self._state.decoder_backlog += 1
        enqueued_id = self._publish("decoder.enqueued", job.job_id, causal_parent_id,
                                    {"round_id": round_.round_id})
        key = ("decode", job.job_id)
        u = draw_uniform(self._config.run_seed, "decode", key)
        self._publish("draw.sampled", job.job_id, enqueued_id,
                      {"stream": "decode", "key": key, "uniform": u})
        service_time_s = self._state.models.decoder_service.service_time_s(
            job, self._state.decoder_backlog, Draw(u=u),
        )
        job.dequeue_time = self._state.now
        self._heap.push(self._state.now + service_time_s, _DecoderCompletionPayload(
            job_id=job.job_id, round_id=round_.round_id, causal_parent_id=enqueued_id,
        ))

    def _on_decoder_completion(self, payload: "_DecoderCompletionPayload") -> None:
        ctx = self._round_contexts.get(payload.round_id)
        if ctx is None or ctx.decoder_job is None or ctx.decoder_job.job_id != payload.job_id:
            return  # round already failed/cancelled; §5 cascade already cancelled the job
        ctx.decoder_job.completion_time = self._state.now
        self._state.decoder_backlog -= 1
        self._publish("decoder.completed", payload.job_id, payload.causal_parent_id,
                      {"round_id": payload.round_id})
        # Task 6 attaches round-success scoring here.

# qsim/core/engine.py — Engine._dispatch: add branch
        elif isinstance(payload, _DecoderCompletionPayload):
            self._on_decoder_completion(payload)
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_engine_decoder.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/core/engine.py tests/core/test_engine_decoder.py
git commit -m "feat: engine decoder job enqueue and completion scheduling"
```

### Task 6: Round-success scoring, terminal outcomes, and workload retry hookup

**Files:**
- Modify: `qsim/core/engine.py`
- Test: `tests/core/test_engine_outcome.py`

**Interfaces:**
- Consumes: `qsim.models.protocols.RoundSuccessModel.success_probability(lease_fidelities, memory_retentions, decoder_latency_s, deadline_slack_s)`, `qsim.workload.generator.WorkloadGenerator.on_outcome(round, succeeded) -> SyndromeRound | None`, `qsim.entities.RoundState`.
- Produces: `Engine._score_round` (replaces the trailing comment in `_on_decoder_completion` from Task 5), task-local RNG stream name `"round_outcome"` for the success-threshold draw (not one of §10's two named examples but consistent with its "e.g." framing — documented here as the binding convention for this stream).

- [ ] **Step 1: Write the failing test**
```python
# tests/core/test_engine_outcome.py
from tests.core.test_engine import make_config, make_workload, make_epoch
from qsim.core.trace import TraceBus
from qsim.core.invariants import InvariantChecker
from qsim.core.state import ModelBundle
from qsim.core.engine import Engine
from qsim.core.rng import draw_uniform
from qsim.policies.s0 import S0Scheduler
from qsim.entities import RoundState
from qsim.models.decay import NoDecayModel
from qsim.models.memory_access import ZeroCostMemoryAccessModel
from qsim.models.heralding import BernoulliHeraldingModel
from qsim.models.round_success import LogisticRoundSuccessModel
from qsim.models.decoder_service import ExponentialDecoderServiceModel


def _epoch_guaranteed_success():
    epoch = make_epoch()
    from collections import defaultdict
    object.__setattr__(epoch, "heralding_p_per_path", defaultdict(lambda: 1.0))
    object.__setattr__(epoch, "heralded_fidelity_per_path", defaultdict(lambda: 1.0))
    object.__setattr__(epoch, "decoder_service_rate", 10000.0)
    object.__setattr__(epoch, "round_success_logistic_midpoint", 0.0)
    object.__setattr__(epoch, "round_success_logistic_slope", 50.0)
    object.__setattr__(epoch, "round_success_slack_penalty_per_s", 0.0)
    return epoch


def test_round_completes_in_deadline_and_no_retry_is_scheduled():
    workload = make_workload()
    first_round = workload.next_arrival(0.0, 1)
    config = make_config(switch_capacity_c=2)
    config = config.__class__(**{**config.__dict__, "epoch": _epoch_guaranteed_success(),
                                 "deadline_slack_s": 1000.0})
    models = ModelBundle(
        decay=NoDecayModel(), memory_access=ZeroCostMemoryAccessModel(),
        heralding=BernoulliHeraldingModel(), round_success=LogisticRoundSuccessModel(),
        decoder_service=ExponentialDecoderServiceModel(),
    )

    events = []
    trace = TraceBus(run_id="test-run")
    trace.subscribe(events.append)
    engine = Engine(config=config, scheduler=S0Scheduler(), models=models,
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
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_engine_outcome.py -v`
Expected: FAIL — no `round.completed_in_deadline` (or any outcome) event is ever published
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/core/engine.py — Engine._on_decoder_completion: replace trailing comment
    def _on_decoder_completion(self, payload: "_DecoderCompletionPayload") -> None:
        ctx = self._round_contexts.get(payload.round_id)
        if ctx is None or ctx.decoder_job is None or ctx.decoder_job.job_id != payload.job_id:
            return
        ctx.decoder_job.completion_time = self._state.now
        self._state.decoder_backlog -= 1
        completed_id = self._publish("decoder.completed", payload.job_id, payload.causal_parent_id,
                                     {"round_id": payload.round_id})
        self._score_round(ctx.round, ctx.decoder_job, completed_id)

    def _score_round(self, round_: SyndromeRound, job: DecoderJob, causal_parent_id: EventId) -> None:
        lease_fidelities, memory_retentions = self._assemble_round(round_)
        decoder_latency_s = job.completion_time - job.enqueue_time
        deadline_slack_s = round_.deadline - job.completion_time
        p = self._state.models.round_success.success_probability(
            lease_fidelities, memory_retentions, decoder_latency_s, deadline_slack_s,
        )
        key = ("round_outcome", round_.round_id)
        u = draw_uniform(self._config.run_seed, "round_outcome", key)
        draw_id = self._publish("draw.sampled", round_.round_id, causal_parent_id,
                                {"stream": "round_outcome", "key": key, "uniform": u})
        succeeded = u < p
        if succeeded and deadline_slack_s >= 0.0:
            round_.state = RoundState.COMPLETED_IN_DEADLINE
            outcome_id = self._publish("round.completed_in_deadline", round_.round_id, draw_id,
                                       {"success_probability": p})
        elif succeeded:
            round_.state = RoundState.COMPLETED_LATE
            outcome_id = self._publish("round.completed_late", round_.round_id, draw_id,
                                       {"success_probability": p})
        else:
            round_.state = RoundState.FAILED
            outcome_id = self._publish("round.failed", round_.round_id, draw_id,
                                       {"success_probability": p})
        self._retry_or_drop(round_, outcome_id)
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_engine_outcome.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/core/engine.py tests/core/test_engine_outcome.py
git commit -m "feat: engine round-success scoring and terminal outcome events"
```

### Task 7: §5 failure-cleanup cascade

**Files:**
- Modify: `qsim/core/engine.py`
- Test: `tests/core/test_engine_cascade.py`

**Interfaces:**
- Consumes: `qsim.entities.LeaseState`/`ReservationState`, `RunConfig.pregen_low_water_mark` (presence signals pooling-vs-round-bound disposal per §5), `EngineState.pool`.
- Produces: `Engine._run_cleanup_cascade` (invoked from `_fail_round`, replacing its Task-2 minimal body, and from a new `Engine._cancel_round` used identically for cancellation).

- [ ] **Step 1: Write the failing test**
```python
# tests/core/test_engine_cascade.py
from tests.core.test_engine import make_config, make_workload, make_epoch
from qsim.core.trace import TraceBus
from qsim.core.invariants import InvariantChecker
from qsim.core.state import ModelBundle
from qsim.core.engine import Engine
from qsim.policies.s0 import S0Scheduler
from qsim.entities import LeaseState, ReservationState
from qsim.models.decay import NoDecayModel
from qsim.models.memory_access import ZeroCostMemoryAccessModel
from qsim.models.heralding import BernoulliHeraldingModel
from qsim.models.round_success import LogisticRoundSuccessModel
from qsim.models.decoder_service import ExponentialDecoderServiceModel


def _epoch_heralding_always_fails():
    epoch = make_epoch()
    from collections import defaultdict
    object.__setattr__(epoch, "heralding_p_per_path", defaultdict(lambda: 0.0))
    object.__setattr__(epoch, "heralded_fidelity_per_path", defaultdict(lambda: 0.9))
    return epoch


def test_round_bound_cascade_cancels_reservation_when_heralding_never_succeeds():
    workload = make_workload()
    first_round = workload.next_arrival(0.0, 1)
    config = make_config(switch_capacity_c=2)
    # deadline_slack_s controls round.deadline; keep it small so heralding
    # (which always fails, p=0.0) exceeds the deadline quickly.
    config = config.__class__(**{**config.__dict__, "epoch": _epoch_heralding_always_fails(),
                                 "deadline_slack_s": 0.01})
    models = ModelBundle(
        decay=NoDecayModel(), memory_access=ZeroCostMemoryAccessModel(),
        heralding=BernoulliHeraldingModel(), round_success=LogisticRoundSuccessModel(),
        decoder_service=ExponentialDecoderServiceModel(),
    )

    events = []
    trace = TraceBus(run_id="test-run")
    trace.subscribe(events.append)
    engine = Engine(config=config, scheduler=S0Scheduler(), models=models,
                    workload=make_workload(), trace=trace, invariants=InvariantChecker())
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
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_engine_cascade.py -v`
Expected: FAIL — no `lease.cancelled` event and `reservation.released` appears (if at all) after `round.failed`, not before, since the cascade is not yet wired
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/core/engine.py — replace _fail_round (Task 2) and add _cancel_round, _run_cleanup_cascade
    def _fail_round(self, round_: SyndromeRound, reason: str, causal_parent_id: EventId) -> None:
        causal_parent_id = self._run_cleanup_cascade(round_, causal_parent_id)
        round_.state = RoundState.FAILED
        failed_id = self._publish("round.failed", round_.round_id, causal_parent_id, {"reason": reason})
        self._retry_or_drop(round_, failed_id)

    def _cancel_round(self, round_: SyndromeRound, reason: str, causal_parent_id: EventId) -> None:
        causal_parent_id = self._run_cleanup_cascade(round_, causal_parent_id)
        round_.state = RoundState.FAILED
        cancelled_id = self._publish("round.failed", round_.round_id, causal_parent_id,
                                     {"reason": reason, "cancelled": True})
        self._retry_or_drop(round_, cancelled_id)

    def _run_cleanup_cascade(self, round_: SyndromeRound, causal_parent_id: EventId) -> EventId:
        """§5's cleanup cascade: cancel decoder jobs, release reservations,
        dispose unconsumed leases (round-bound cancel for S0; pooling
        return/expire when pregen is configured), each a distinct event."""
        ctx = self._round_contexts.get(round_.round_id)
        if ctx is None:
            return causal_parent_id
        last_id = causal_parent_id

        if ctx.decoder_job is not None and ctx.decoder_job.completion_time is None:
            self._state.decoder_backlog -= 1
            last_id = self._publish("decoder.cancelled", ctx.decoder_job.job_id, last_id,
                                    {"round_id": round_.round_id})

        for path_id, reservation in list(self._state.active_reservations.items()):
            if reservation.holder_id != round_.round_id:
                continue
            reservation.state = ReservationState.RELEASED
            reservation.released_at = self._state.now
            entity_id = f"{path_id[0].module_id}:{path_id[0].port_index}->{path_id[1].module_id}:{path_id[1].port_index}"
            last_id = self._publish("reservation.released", entity_id, last_id, {})
            del self._state.active_reservations[path_id]

        pregen_active = self._config.pregen_low_water_mark is not None
        for lease in ctx.leases.values():
            if lease.state != LeaseState.HERALDED:
                continue
            age_s = self._state.now - lease.heralded_at
            if pregen_active and age_s < lease.freshness_bound_s:
                lease.state = LeaseState.CANCELLED  # frozen enum has no POOLED state; CANCELLED
                                                     # marks it non-consumable by this round while
                                                     # the pool dict holds the live reference
                self._state.pool.setdefault((lease.path_id, None), []).append(lease)
                last_id = self._publish("lease.pool_returned", lease.lease_id, last_id,
                                        {"round_id": round_.round_id})
            else:
                lease.state = LeaseState.EXPIRED if pregen_active else LeaseState.CANCELLED
                event_type = "lease.expired" if pregen_active else "lease.cancelled"
                last_id = self._publish(event_type, lease.lease_id, last_id,
                                        {"round_id": round_.round_id})

        del self._round_contexts[round_.round_id]
        return last_id
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_engine_cascade.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/core/engine.py tests/core/test_engine_cascade.py
git commit -m "feat: engine section-5 failure-cleanup cascade"
```

### Task 8: End-to-end integration test with real S0Scheduler and real v1 models

**Files:**
- Test: `tests/core/test_engine_integration.py`

**Interfaces:**
- Consumes: everything produced by Tasks 1–7 plus `qsim.core.invariants.InvariantChecker` (subclassed only to count `observe` calls, never to fake its logic).
- Produces: nothing new; this task is pure verification of the fully wired `Engine`.

- [ ] **Step 1: Write the failing test**
```python
# tests/core/test_engine_integration.py
from tests.core.test_engine import make_config, make_workload, make_epoch
from qsim.core.trace import TraceBus
from qsim.core.invariants import InvariantChecker
from qsim.core.state import ModelBundle
from qsim.core.engine import Engine
from qsim.core.rng import draw_uniform
from qsim.policies.s0 import S0Scheduler
from qsim.entities import LeaseState, ReservationState, RoundState
from qsim.models.decay import NoDecayModel
from qsim.models.memory_access import ZeroCostMemoryAccessModel
from qsim.models.heralding import BernoulliHeraldingModel
from qsim.models.round_success import LogisticRoundSuccessModel
from qsim.models.decoder_service import ExponentialDecoderServiceModel


class CountingInvariantChecker(InvariantChecker):
    def __init__(self):
        super().__init__()
        self.observed = 0

    def observe(self, event, state):
        self.observed += 1
        super().observe(event, state)


def _epoch_guaranteed_success():
    epoch = make_epoch()
    from collections import defaultdict
    object.__setattr__(epoch, "heralding_p_per_path", defaultdict(lambda: 1.0))
    object.__setattr__(epoch, "heralded_fidelity_per_path", defaultdict(lambda: 1.0))
    object.__setattr__(epoch, "decoder_service_rate", 10000.0)
    object.__setattr__(epoch, "round_success_logistic_midpoint", 0.0)
    object.__setattr__(epoch, "round_success_logistic_slope", 50.0)
    object.__setattr__(epoch, "round_success_slack_penalty_per_s", 0.0)
    return epoch


def test_single_round_single_path_full_causal_chain_with_fixed_seed():
    run_seed = 7
    workload = make_workload()
    first_round = workload.next_arrival(0.0, 1)
    config = make_config(switch_capacity_c=1)
    config = config.__class__(**{**config.__dict__, "run_seed": run_seed,
                                 "epoch": _epoch_guaranteed_success(),
                                 "deadline_slack_s": 1000.0, "reconfig_delay_s": 0.25})
    models = ModelBundle(
        decay=NoDecayModel(), memory_access=ZeroCostMemoryAccessModel(),
        heralding=BernoulliHeraldingModel(), round_success=LogisticRoundSuccessModel(),
        decoder_service=ExponentialDecoderServiceModel(),
    )

    events = []
    trace = TraceBus(run_id="integration-run")
    trace.subscribe(events.append)
    invariants = CountingInvariantChecker()
    engine = Engine(config=config, scheduler=S0Scheduler(), models=models,
                    workload=make_workload(), trace=trace, invariants=invariants)

    engine.run_to(first_round.arrival_time + config.reconfig_delay_s + 5.0)

    expected_order = [
        "round.arrived", "round.admitted", "reservation.acquired", "reservation.configuring",
        "reservation.active", "draw.sampled", "lease.heralded", "reservation.released",
        "decoder.enqueued", "draw.sampled", "decoder.completed", "draw.sampled",
        "round.completed_in_deadline",
    ]
    round_events = [e for e in events if e.entity_id == first_round.round_id
                    or e.payload.get("round_id") == first_round.round_id]
    # entity_id differs per stage (round/path/lease/job); filter to this
    # round's own causal thread by walking parent links instead of entity_id.
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
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/core/test_engine_integration.py -v`
Expected: FAIL only if any prior task's wiring is incomplete — with Tasks 1–7 done, this should already pass; if it fails, the failure pinpoints exactly which causal link (`chain` mismatch) or invariant-call count is wrong
- [ ] **Step 3: Write minimal implementation**
```python
# No new implementation: this task asserts on the Engine built by Tasks 1-7.
# If Step 2 fails, the fix belongs to whichever task's method produced the
# broken link in `chain` (e.g. a missing causal_parent_id threading) —
# amend that task's code in qsim/core/engine.py, not this test.
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/core/test_engine_integration.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tests/core/test_engine_integration.py
git commit -m "test: end-to-end causal-chain integration test for the engine"
```
---

## Section 8 of 8 — experiments/ (RunConfig, single-run driver, limit checks, determinism tests)

### Task 1: RunConfig

**Files:**
- Create: `qsim/experiments/__init__.py`
- Create: `qsim/experiments/config.py`
- Test: `tests/experiments/test_config.py`

**Interfaces:**
- Consumes: `CalibrationEpoch` (`qsim.entities`, frozen dataclass per contract: `epoch_id: str`, `decay_rate_per_class: dict[CoherenceClass, float]`, `memory_access_channel_s: float`, `memory_access_wear_rate: float`, `heralding_p_per_path: dict[PathId, float]`, `heralded_fidelity_per_path: dict[PathId, float]`, `round_success_logistic_midpoint: float`, `round_success_logistic_slope: float`, `round_success_slack_penalty_per_s: float`, `decoder_service_rate: float`); `CoherenceClass`, `PortId`, `make_path_id` (`qsim.entities`, for test fixtures only).
- Produces: `RunConfig` — `@dataclass(frozen=True)` with fields verbatim from the frozen contract: `run_seed: int`, `scheduler: str`, `epoch: CalibrationEpoch`, `arrival_rate_hz: float`, `leases_per_round: int`, `deadline_slack_s: float`, `switch_capacity_c: int`, `reconfig_delay_s: float`, `max_sim_time_s: float`, `hold_until_consumption: bool = False`, `admission_theta: float | None = None`, `pregen_low_water_mark: int | None = None`, `decay_control_enabled: bool = True`, `memory_cost_control_enabled: bool = True`; plus task-local `__post_init__` validation (raises `ValueError` for an unknown `scheduler` tag, or for `scheduler == "S1"` missing `admission_theta`/`pregen_low_water_mark`, per spec §8.1/§8.2).

- [ ] **Step 1: Write the failing test**
```python
# tests/experiments/test_config.py
import pytest
from dataclasses import FrozenInstanceError

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig


def _epoch() -> CalibrationEpoch:
    a = PortId(module_id="mod-a", port_index=0)
    b = PortId(module_id="mod-b", port_index=0)
    path = make_path_id(a, b)
    return CalibrationEpoch(
        epoch_id="test-epoch",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.01, CoherenceClass.MEMORY: 0.001},
        memory_access_channel_s=0.001,
        memory_access_wear_rate=0.01,
        heralding_p_per_path={path: 0.5},
        heralded_fidelity_per_path={path: 0.95},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=10.0,
        round_success_slack_penalty_per_s=1.0,
        decoder_service_rate=5.0,
    )


def _base_kwargs(**overrides) -> dict:
    kwargs = dict(
        run_seed=1,
        scheduler="S0",
        epoch=_epoch(),
        arrival_rate_hz=1.0,
        leases_per_round=2,
        deadline_slack_s=1.0,
        switch_capacity_c=2,
        reconfig_delay_s=0.01,
        max_sim_time_s=100.0,
    )
    kwargs.update(overrides)
    return kwargs


def test_runconfig_valid_s0_construction_has_expected_defaults():
    config = RunConfig(**_base_kwargs())
    assert config.hold_until_consumption is False
    assert config.admission_theta is None
    assert config.pregen_low_water_mark is None
    assert config.decay_control_enabled is True
    assert config.memory_cost_control_enabled is True


def test_runconfig_valid_s1_construction_requires_admission_and_pregen_params():
    config = RunConfig(
        **_base_kwargs(scheduler="S1", admission_theta=0.8, pregen_low_water_mark=3)
    )
    assert config.admission_theta == 0.8
    assert config.pregen_low_water_mark == 3


def test_runconfig_s1_missing_admission_theta_raises():
    with pytest.raises(ValueError, match="admission_theta"):
        RunConfig(**_base_kwargs(scheduler="S1", pregen_low_water_mark=3))


def test_runconfig_s1_missing_pregen_low_water_mark_raises():
    with pytest.raises(ValueError, match="pregen_low_water_mark"):
        RunConfig(**_base_kwargs(scheduler="S1", admission_theta=0.8))


def test_runconfig_rejects_unknown_scheduler_tag():
    with pytest.raises(ValueError, match="scheduler"):
        RunConfig(**_base_kwargs(scheduler="S2"))


def test_runconfig_is_frozen():
    config = RunConfig(**_base_kwargs())
    with pytest.raises(FrozenInstanceError):
        config.run_seed = 2
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/experiments/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.experiments.config'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/experiments/config.py
from dataclasses import dataclass

from qsim.entities import CalibrationEpoch

_VALID_SCHEDULERS = ("S0", "S1")


@dataclass(frozen=True)
class RunConfig:
    run_seed: int
    scheduler: str  # "S0" | "S1"
    epoch: CalibrationEpoch
    arrival_rate_hz: float
    leases_per_round: int
    deadline_slack_s: float
    switch_capacity_c: int
    reconfig_delay_s: float
    max_sim_time_s: float
    hold_until_consumption: bool = False
    admission_theta: float | None = None       # required if scheduler == "S1" (§8.1)
    pregen_low_water_mark: int | None = None   # required if scheduler == "S1" (§8.2)
    decay_control_enabled: bool = True         # False => NoDecayModel (§6, §15)
    memory_cost_control_enabled: bool = True   # False => ZeroCostMemoryAccessModel (§6, §15)

    def __post_init__(self) -> None:
        if self.scheduler not in _VALID_SCHEDULERS:
            raise ValueError(
                f"scheduler must be one of {_VALID_SCHEDULERS}, got {self.scheduler!r}"
            )
        if self.scheduler == "S1":
            if self.admission_theta is None:
                raise ValueError(
                    "admission_theta is required when scheduler == 'S1' (spec §8.1)"
                )
            if self.pregen_low_water_mark is None:
                raise ValueError(
                    "pregen_low_water_mark is required when scheduler == 'S1' (spec §8.2)"
                )
```
```python
# qsim/experiments/__init__.py
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/experiments/test_config.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/experiments/__init__.py qsim/experiments/config.py tests/experiments/test_config.py
git commit -m "feat: add RunConfig with S1 admission/pregen validation"
```

### Task 2: Single-run driver

**Files:**
- Create: `qsim/experiments/run.py`
- Test: `tests/experiments/test_run.py`

**Interfaces:**
- Consumes: `RunConfig` (Task 1); `qsim.core.engine.Engine.__init__(self, config: RunConfig, scheduler: Scheduler, models: ModelBundle, workload: WorkloadGenerator, trace: TraceBus, invariants: InvariantChecker)` and `.run_to(self, max_sim_time_s: float) -> None`; `qsim.core.trace.TraceBus.subscribe(self, fn: Callable[[Event], None]) -> None`; `qsim.core.invariants.InvariantChecker`; `qsim.core.state.ModelBundle(decay, memory_access, heralding, round_success, decoder_service)`; `qsim.models.decay.{ExponentialDecayModel, NoDecayModel}`; `qsim.models.memory_access.{LinearMemoryAccessModel, ZeroCostMemoryAccessModel}`; `qsim.models.heralding.BernoulliHeraldingModel`; `qsim.models.round_success.LogisticRoundSuccessModel`; `qsim.models.decoder_service.ExponentialDecoderServiceModel`; `qsim.policies.s0.S0Scheduler`; `qsim.policies.s1.S1Scheduler`; `qsim.workload.generator.WorkloadGenerator.__init__(self, run_seed: int, arrival_rate_hz: float, leases_per_round: int, deadline_slack_s: float)`; `qsim.observe.run_dir.RunDirWriter.__init__(self, root: Path, run_id: str)`, `.write_header(self, config: RunConfig, run_seed: int, git_sha: str, filtering_declared: dict | None = None) -> None`, `.append_event(self, event: Event) -> None`.
- Produces: `run(config: RunConfig, out_dir: Path) -> Path` — verbatim from the frozen contract. Task-local: `build_model_bundle(config: RunConfig) -> ModelBundle`, `build_scheduler(config: RunConfig) -> Scheduler`, `git_sha() -> str`.

- [ ] **Step 1: Write the failing test**
```python
# tests/experiments/test_run.py
import json

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.experiments.run import build_model_bundle, build_scheduler, run
from qsim.models.decay import ExponentialDecayModel, NoDecayModel
from qsim.models.memory_access import LinearMemoryAccessModel, ZeroCostMemoryAccessModel
from qsim.policies.s0 import S0Scheduler
from qsim.policies.s1 import S1Scheduler


def _epoch() -> CalibrationEpoch:
    a = PortId(module_id="mod-a", port_index=0)
    b = PortId(module_id="mod-b", port_index=0)
    path = make_path_id(a, b)
    return CalibrationEpoch(
        epoch_id="run-test-epoch",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.01, CoherenceClass.MEMORY: 0.001},
        memory_access_channel_s=0.001,
        memory_access_wear_rate=0.01,
        heralding_p_per_path={path: 0.7},
        heralded_fidelity_per_path={path: 0.95},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=10.0,
        round_success_slack_penalty_per_s=1.0,
        decoder_service_rate=5.0,
    )


def _s0_config(**overrides) -> RunConfig:
    fields = dict(
        run_seed=42,
        scheduler="S0",
        epoch=_epoch(),
        arrival_rate_hz=1.0,
        leases_per_round=1,
        deadline_slack_s=5.0,
        switch_capacity_c=1,
        reconfig_delay_s=0.01,
        max_sim_time_s=20.0,
    )
    fields.update(overrides)
    return RunConfig(**fields)


def test_run_produces_a_run_directory_with_header_and_events(tmp_path):
    config = _s0_config()
    run_dir = run(config, tmp_path)

    assert run_dir.is_dir()
    header_path = run_dir / "header.json"
    events_path = run_dir / "events.jsonl"
    assert header_path.exists()
    assert events_path.exists()

    header = json.loads(header_path.read_text())
    assert header["run_seed"] == 42

    lines = events_path.read_text().strip().splitlines()
    assert len(lines) > 0
    first_event = json.loads(lines[0])
    assert "event_type" in first_event
    assert "sim_time" in first_event


def test_run_with_s1_scheduler_wires_admission_and_pregen_params(tmp_path):
    config = _s0_config(scheduler="S1", admission_theta=0.5, pregen_low_water_mark=2)
    run_dir = run(config, tmp_path)
    events_path = run_dir / "events.jsonl"
    assert events_path.exists()
    assert len(events_path.read_text().strip().splitlines()) > 0


def test_build_scheduler_returns_s0_scheduler_for_s0_tag():
    assert isinstance(build_scheduler(_s0_config()), S0Scheduler)


def test_build_scheduler_returns_s1_scheduler_for_s1_tag():
    config = _s0_config(scheduler="S1", admission_theta=0.5, pregen_low_water_mark=2)
    assert isinstance(build_scheduler(config), S1Scheduler)


def test_build_model_bundle_honors_decay_control_flag():
    on = build_model_bundle(_s0_config(decay_control_enabled=True))
    off = build_model_bundle(_s0_config(decay_control_enabled=False))
    assert isinstance(on.decay, ExponentialDecayModel)
    assert isinstance(off.decay, NoDecayModel)


def test_build_model_bundle_honors_memory_cost_control_flag():
    on = build_model_bundle(_s0_config(memory_cost_control_enabled=True))
    off = build_model_bundle(_s0_config(memory_cost_control_enabled=False))
    assert isinstance(on.memory_access, LinearMemoryAccessModel)
    assert isinstance(off.memory_access, ZeroCostMemoryAccessModel)
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/experiments/test_run.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'qsim.experiments.run'`
- [ ] **Step 3: Write minimal implementation**
```python
# qsim/experiments/run.py
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

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
from qsim.policies.s0 import S0Scheduler
from qsim.policies.s1 import S1Scheduler
from qsim.workload.generator import WorkloadGenerator


def build_model_bundle(config: RunConfig) -> ModelBundle:
    """Wires the §6/§15 control flags to concrete model-surface implementations."""
    decay = ExponentialDecayModel() if config.decay_control_enabled else NoDecayModel()
    memory_access = (
        LinearMemoryAccessModel()
        if config.memory_cost_control_enabled
        else ZeroCostMemoryAccessModel()
    )
    return ModelBundle(
        decay=decay,
        memory_access=memory_access,
        heralding=BernoulliHeraldingModel(),
        round_success=LogisticRoundSuccessModel(),
        decoder_service=ExponentialDecoderServiceModel(),
    )


def build_scheduler(config: RunConfig):
    """Constructs the Scheduler named by config.scheduler (§8's ablation ladder tag)."""
    if config.scheduler == "S0":
        return S0Scheduler()
    if config.scheduler == "S1":
        return S1Scheduler(
            admission_theta=config.admission_theta,
            pregen_low_water_mark=config.pregen_low_water_mark,
        )
    raise ValueError(f"unknown scheduler tag: {config.scheduler!r}")


def git_sha() -> str:
    """Best-effort current commit SHA for header.json provenance (§12)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def run(config: RunConfig, out_dir: Path) -> Path:
    """Builds the engine, wires models/policies/workload/observe per config,
    executes to max_sim_time_s or exhaustion, returns the run directory path."""
    run_id = str(uuid.uuid4())

    trace = TraceBus()
    invariants = InvariantChecker()
    run_dir_writer = RunDirWriter(root=Path(out_dir), run_id=run_id)
    trace.subscribe(run_dir_writer.append_event)

    scheduler = build_scheduler(config)
    models = build_model_bundle(config)
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
        filtering_declared=None,
    )

    engine.run_to(config.max_sim_time_s)

    return Path(out_dir) / run_id
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/experiments/test_run.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add qsim/experiments/run.py tests/experiments/test_run.py
git commit -m "feat: add single-run driver wiring models/policies/workload/observe"
```

### Task 3: M/M/1 decoupled-limit check (decoder queue)

**Files:**
- Create: `tests/limit_checks/test_mm1_decoupled_limit.py`
- Test: `tests/limit_checks/test_mm1_decoupled_limit.py`

**Interfaces:**
- Consumes: `run(config: RunConfig, out_dir: Path) -> Path` (Task 2); `qsim.observe.views.decoder_backlog_series(events_path: Path) -> list[tuple[float, int]]`; `RunConfig`, `CalibrationEpoch`, `CoherenceClass`, `PortId`, `make_path_id`; `Event` JSON fields `event_type`, `entity_id`, `sim_time` on `decoder.enqueued`/`decoder.completed`.
- Produces: task-local test helpers only (not part of any package's public surface): `_decoder_sojourn_times`, `_time_average_backlog`, `_load_events`, `_mm1_config`.

- [ ] **Step 1: Write the failing test**
```python
# tests/limit_checks/test_mm1_decoupled_limit.py
import json
from pathlib import Path

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.experiments.run import run
from qsim.observe.views import decoder_backlog_series

TOLERANCE = 0.15  # relative-error tolerance for stochastic M/M/1 comparisons


def _decoder_sojourn_times(events: list[dict]) -> list[float]:
    raise NotImplementedError


def _time_average_backlog(series: list[tuple[float, int]], warmup_s: float) -> float:
    raise NotImplementedError


def _load_events(events_path: Path) -> list[dict]:
    return [json.loads(line) for line in events_path.read_text().strip().splitlines()]


def _mm1_config(run_seed: int, lam: float, mu: float, max_sim_time_s: float) -> RunConfig:
    a = PortId(module_id="mod-a", port_index=0)
    b = PortId(module_id="mod-b", port_index=0)
    path = make_path_id(a, b)
    epoch = CalibrationEpoch(
        epoch_id="mm1-decoupled-limit",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.0, CoherenceClass.MEMORY: 0.0},
        memory_access_channel_s=0.0,
        memory_access_wear_rate=0.0,
        heralding_p_per_path={path: 1.0},
        heralded_fidelity_per_path={path: 1.0},
        round_success_logistic_midpoint=-10.0,
        round_success_logistic_slope=1.0,
        round_success_slack_penalty_per_s=0.0,
        decoder_service_rate=mu,
    )
    return RunConfig(
        run_seed=run_seed,
        scheduler="S0",  # no admission control (§8: S0 is the un-augmented baseline)
        epoch=epoch,
        arrival_rate_hz=lam,
        leases_per_round=1,  # one qubit interaction per round (RunConfig has no
                             # separate qubit-count field; qubit topology is
                             # provisioned outside experiments/ scope)
        deadline_slack_s=10_000.0,  # deadlines never bind, so failures never retry
        switch_capacity_c=1,  # single path
        reconfig_delay_s=0.0,
        max_sim_time_s=max_sim_time_s,
        decay_control_enabled=False,  # NoDecayModel: no decay
        memory_cost_control_enabled=False,
    )


def test_mm1_decoder_queue_matches_analytic_wait_in_decoupled_limit(tmp_path):
    """§16.2 decoupled-limit check — named as such, NOT validation of the
    coupled regime: single path, one qubit, decay disabled, memory cost
    disabled, certain heralding. The decoder subsystem alone degenerates to a
    plain M/M/1 queue; its mean sojourn time must match the closed-form
    W = 1/(mu-lambda)."""
    lam, mu = 0.5, 1.0
    config = _mm1_config(run_seed=999, lam=lam, mu=mu, max_sim_time_s=20_000.0)
    run_dir = run(config, tmp_path)
    events = _load_events(run_dir / "events.jsonl")

    sojourns = _decoder_sojourn_times(events)
    assert len(sojourns) > 500, "need enough completed decoder jobs for a stable estimate"

    empirical_w = sum(sojourns) / len(sojourns)
    analytic_w = 1.0 / (mu - lam)
    relative_error = abs(empirical_w - analytic_w) / analytic_w

    assert relative_error < TOLERANCE, (
        f"empirical mean decoder sojourn time {empirical_w:.4f}s deviates from "
        f"M/M/1 analytic W={analytic_w:.4f}s by {relative_error:.2%}"
    )


def test_mm1_decoder_queue_matches_littles_law_in_decoupled_limit(tmp_path):
    """§16.2 decoupled-limit check: Little's Law L = lambda*W, checked against
    this same decoupled M/M/1 run's own measurements, and against the
    closed-form L = rho/(1-rho)."""
    lam, mu = 0.5, 1.0
    max_sim_time_s = 20_000.0
    warmup_s = 2_000.0
    config = _mm1_config(run_seed=999, lam=lam, mu=mu, max_sim_time_s=max_sim_time_s)
    run_dir = run(config, tmp_path)
    events_path = run_dir / "events.jsonl"
    events = _load_events(events_path)

    sojourns = _decoder_sojourn_times(events)
    assert len(sojourns) > 500
    empirical_w = sum(sojourns) / len(sojourns)

    series = decoder_backlog_series(events_path)
    empirical_l = _time_average_backlog(series, warmup_s)

    predicted_l = lam * empirical_w
    analytic_l = lam / (mu - lam)

    relative_error_littles_law = abs(empirical_l - predicted_l) / predicted_l
    relative_error_analytic = abs(empirical_l - analytic_l) / analytic_l

    assert relative_error_littles_law < TOLERANCE, (
        f"L={empirical_l:.4f} vs lambda*W={predicted_l:.4f}: Little's Law "
        f"violated by {relative_error_littles_law:.2%}"
    )
    assert relative_error_analytic < TOLERANCE, (
        f"L={empirical_l:.4f} vs analytic M/M/1 L={analytic_l:.4f}: deviates "
        f"by {relative_error_analytic:.2%}"
    )
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/limit_checks/test_mm1_decoupled_limit.py -v`
Expected: FAIL with `NotImplementedError` raised from `_decoder_sojourn_times`
- [ ] **Step 3: Write minimal implementation**
```python
# tests/limit_checks/test_mm1_decoupled_limit.py (helper bodies, replacing the stubs)
def _decoder_sojourn_times(events: list[dict]) -> list[float]:
    enqueued_at: dict[str, float] = {}
    sojourns: list[float] = []
    for event in events:
        if event["event_type"] == "decoder.enqueued":
            enqueued_at[event["entity_id"]] = event["sim_time"]
        elif event["event_type"] == "decoder.completed":
            start = enqueued_at.get(event["entity_id"])
            if start is not None:
                sojourns.append(event["sim_time"] - start)
    return sojourns


def _time_average_backlog(series: list[tuple[float, int]], warmup_s: float) -> float:
    windowed = [(t, backlog) for t, backlog in series if t >= warmup_s]
    if len(windowed) < 2:
        return 0.0
    area = 0.0
    for (t0, b0), (t1, _b1) in zip(windowed, windowed[1:]):
        area += b0 * (t1 - t0)
    duration = windowed[-1][0] - windowed[0][0]
    return area / duration if duration > 0 else 0.0
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/limit_checks/test_mm1_decoupled_limit.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tests/limit_checks/test_mm1_decoupled_limit.py
git commit -m "test: add M/M/1 decoupled-limit check for decoder queue (Little's Law, analytic wait)"
```

### Task 4: Heralding attempts vs Bernoulli/Poisson decoupled-limit check

**Files:**
- Create: `tests/limit_checks/test_heralding_bernoulli_poisson_decoupled_limit.py`
- Test: `tests/limit_checks/test_heralding_bernoulli_poisson_decoupled_limit.py`

**Interfaces:**
- Consumes: `run(config: RunConfig, out_dir: Path) -> Path` (Task 2); `RunConfig`, `CalibrationEpoch`, `CoherenceClass`, `PortId`, `make_path_id`; `Event` JSON fields on `draw.sampled` (`payload: {stream, key, uniform}`), `lease.heralded`, `round.arrived`.
- Produces: task-local test helpers only: `_bernoulli_success_stats`, `_arrival_interarrival_times`, `_load_events`, `_decoupled_config`.

- [ ] **Step 1: Write the failing test**
```python
# tests/limit_checks/test_heralding_bernoulli_poisson_decoupled_limit.py
import json
import statistics
from pathlib import Path

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.experiments.run import run

BERNOULLI_TOLERANCE_SIGMAS = 4.0  # generous normal-approximation CI multiplier
POISSON_RELATIVE_TOLERANCE = 0.15


def _load_events(events_path: Path) -> list[dict]:
    return [json.loads(line) for line in events_path.read_text().strip().splitlines()]


def _bernoulli_success_stats(events: list[dict]) -> tuple[int, int]:
    raise NotImplementedError


def _arrival_interarrival_times(events: list[dict]) -> list[float]:
    raise NotImplementedError


def _decoupled_config(
    run_seed: int, arrival_rate_hz: float, herald_p: float, max_sim_time_s: float
) -> RunConfig:
    a = PortId(module_id="mod-a", port_index=0)
    b = PortId(module_id="mod-b", port_index=0)
    path = make_path_id(a, b)
    epoch = CalibrationEpoch(
        epoch_id="herald-decoupled-limit",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.0, CoherenceClass.MEMORY: 0.0},
        memory_access_channel_s=0.0,
        memory_access_wear_rate=0.0,
        heralding_p_per_path={path: herald_p},
        heralded_fidelity_per_path={path: 1.0},
        round_success_logistic_midpoint=-10.0,
        round_success_logistic_slope=1.0,
        round_success_slack_penalty_per_s=0.0,
        decoder_service_rate=1000.0,  # decoder never bottlenecks: isolates heralding
    )
    return RunConfig(
        run_seed=run_seed,
        scheduler="S0",  # no admission control (§8)
        epoch=epoch,
        arrival_rate_hz=arrival_rate_hz,
        leases_per_round=1,
        deadline_slack_s=10_000.0,
        switch_capacity_c=4,  # generous capacity: minimizes switch-contention confound
        reconfig_delay_s=0.0,
        max_sim_time_s=max_sim_time_s,
        decay_control_enabled=False,
        memory_cost_control_enabled=False,
    )


def test_heralding_attempts_match_bernoulli_success_rate_in_decoupled_limit(tmp_path):
    """§16.2 decoupled-limit check — NOT coupled-regime validation: per-attempt
    heralding success is a Bernoulli(p) trial by construction (§10: the engine
    thresholds a keyed uniform against the model's probability). The measured
    success rate over many attempts must match the configured p regardless of
    switch/decoder timing, since success-given-an-attempt does not depend on
    when attempts happen to occur."""
    p = 0.3
    config = _decoupled_config(
        run_seed=555, arrival_rate_hz=0.5, herald_p=p, max_sim_time_s=20_000.0
    )
    run_dir = run(config, tmp_path)
    events = _load_events(run_dir / "events.jsonl")

    n_attempts, n_successes = _bernoulli_success_stats(events)
    assert n_attempts > 1000, "need enough herald attempts for a stable estimate"

    phat = n_successes / n_attempts
    stderr = (p * (1 - p) / n_attempts) ** 0.5
    assert abs(phat - p) < BERNOULLI_TOLERANCE_SIGMAS * stderr, (
        f"empirical heralding success rate {phat:.4f} over {n_attempts} attempts "
        f"deviates from configured p={p} by more than "
        f"{BERNOULLI_TOLERANCE_SIGMAS} standard errors ({stderr:.4f})"
    )


def test_workload_arrivals_match_poisson_process_theory_in_decoupled_limit(tmp_path):
    """§16.2 decoupled-limit check: the closed-loop workload's arrival process
    is, per §9, a Poisson process (exponential interarrival times). Its sample
    mean must match 1/arrival_rate_hz, and its coefficient of variation must be
    close to 1 — the defining signature of the exponential interarrival
    distribution."""
    arrival_rate_hz = 2.0
    config = _decoupled_config(
        run_seed=555, arrival_rate_hz=arrival_rate_hz, herald_p=0.3, max_sim_time_s=5_000.0
    )
    run_dir = run(config, tmp_path)
    events = _load_events(run_dir / "events.jsonl")

    interarrivals = _arrival_interarrival_times(events)
    assert len(interarrivals) > 1000, "need enough arrivals for a stable estimate"

    empirical_mean = statistics.mean(interarrivals)
    analytic_mean = 1.0 / arrival_rate_hz
    relative_error = abs(empirical_mean - analytic_mean) / analytic_mean
    assert relative_error < POISSON_RELATIVE_TOLERANCE, (
        f"empirical mean interarrival time {empirical_mean:.4f}s deviates from "
        f"1/lambda={analytic_mean:.4f}s by {relative_error:.2%}"
    )

    coefficient_of_variation = statistics.stdev(interarrivals) / empirical_mean
    assert abs(coefficient_of_variation - 1.0) < POISSON_RELATIVE_TOLERANCE, (
        f"interarrival coefficient of variation {coefficient_of_variation:.4f} "
        f"deviates from the exponential distribution's CV=1 by more than "
        f"{POISSON_RELATIVE_TOLERANCE:.2%} - arrivals may not be a Poisson process"
    )
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/limit_checks/test_heralding_bernoulli_poisson_decoupled_limit.py -v`
Expected: FAIL with `NotImplementedError` raised from `_bernoulli_success_stats`
- [ ] **Step 3: Write minimal implementation**
```python
# tests/limit_checks/test_heralding_bernoulli_poisson_decoupled_limit.py (helper bodies)
def _bernoulli_success_stats(events: list[dict]) -> tuple[int, int]:
    n_attempts = sum(
        1
        for e in events
        if e["event_type"] == "draw.sampled" and e["payload"]["stream"] == "herald"
    )
    n_successes = sum(1 for e in events if e["event_type"] == "lease.heralded")
    return n_attempts, n_successes


def _arrival_interarrival_times(events: list[dict]) -> list[float]:
    arrival_times = sorted(
        e["sim_time"] for e in events if e["event_type"] == "round.arrived"
    )
    return [t1 - t0 for t0, t1 in zip(arrival_times, arrival_times[1:])]
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/limit_checks/test_heralding_bernoulli_poisson_decoupled_limit.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tests/limit_checks/test_heralding_bernoulli_poisson_decoupled_limit.py
git commit -m "test: add heralding-attempts Bernoulli/Poisson decoupled-limit check"
```

### Task 5: Determinism — identical trace hash for same config + run_seed

**Files:**
- Create: `tests/determinism/test_trace_hash_determinism.py`
- Test: `tests/determinism/test_trace_hash_determinism.py`

**Interfaces:**
- Consumes: `run(config: RunConfig, out_dir: Path) -> Path` (Task 2); `RunConfig`, `CalibrationEpoch`, `CoherenceClass`, `PortId`, `make_path_id`; `Event` JSON fields `run_id`, `causal_parent_id` (per §13's `EventId = (run_id, seq)`).
- Produces: task-local test helpers only: `_canonical_trace_hash`, `_config`.

- [ ] **Step 1: Write the failing test**
```python
# tests/determinism/test_trace_hash_determinism.py
import hashlib
import json
from pathlib import Path

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.experiments.run import run


def _canonical_trace_hash(events_path: Path) -> str:
    raise NotImplementedError


def _config(run_seed: int) -> RunConfig:
    a = PortId(module_id="mod-a", port_index=0)
    b = PortId(module_id="mod-b", port_index=0)
    path = make_path_id(a, b)
    epoch = CalibrationEpoch(
        epoch_id="determinism-epoch",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.02, CoherenceClass.MEMORY: 0.005},
        memory_access_channel_s=0.002,
        memory_access_wear_rate=0.01,
        heralding_p_per_path={path: 0.6},
        heralded_fidelity_per_path={path: 0.9},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=8.0,
        round_success_slack_penalty_per_s=0.5,
        decoder_service_rate=4.0,
    )
    return RunConfig(
        run_seed=run_seed,
        scheduler="S0",
        epoch=epoch,
        arrival_rate_hz=2.0,
        leases_per_round=2,
        deadline_slack_s=3.0,
        switch_capacity_c=2,
        reconfig_delay_s=0.02,
        max_sim_time_s=200.0,
    )


def test_same_config_and_run_seed_produce_identical_trace_hash(tmp_path):
    config = _config(run_seed=2024)

    run_dir_a = run(config, tmp_path / "run-a")
    run_dir_b = run(config, tmp_path / "run-b")

    hash_a = _canonical_trace_hash(run_dir_a / "events.jsonl")
    hash_b = _canonical_trace_hash(run_dir_b / "events.jsonl")

    assert hash_a == hash_b


def test_different_run_seed_produces_a_different_trace_hash(tmp_path):
    # Sanity check on the canonicalization itself: it must not be trivially
    # constant (e.g. hashing away everything that varies between runs).
    run_dir_a = run(_config(run_seed=1), tmp_path / "run-a")
    run_dir_b = run(_config(run_seed=2), tmp_path / "run-b")

    hash_a = _canonical_trace_hash(run_dir_a / "events.jsonl")
    hash_b = _canonical_trace_hash(run_dir_b / "events.jsonl")

    assert hash_a != hash_b
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/determinism/test_trace_hash_determinism.py -v`
Expected: FAIL with `NotImplementedError` raised from `_canonical_trace_hash`
- [ ] **Step 3: Write minimal implementation**
```python
# tests/determinism/test_trace_hash_determinism.py (helper body, replacing the stub)
def _canonical_trace_hash(events_path: Path) -> str:
    """SHA-256 over a run's events, normalized so the guarantee (§13's
    trace-hash scope) is independent of the fresh run_id every run gets:
    run_id is replaced by a fixed placeholder wherever it appears, including
    inside causal_parent_id's (run_id, seq) pair, before hashing. Content must
    be identical across runs with the same config+run_seed - not the file's
    mtime or its embedded run_id."""
    digest = hashlib.sha256()
    for line in events_path.read_text().splitlines():
        if not line:
            continue
        event = json.loads(line)
        event["run_id"] = "RUN_ID"
        parent = event.get("causal_parent_id")
        if parent is not None:
            event["causal_parent_id"] = ["RUN_ID", parent[1]]
        canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
        digest.update(canonical.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/determinism/test_trace_hash_determinism.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tests/determinism/test_trace_hash_determinism.py
git commit -m "test: add run_id-normalized trace-hash determinism check"
```

### Task 6: Determinism — paired runs share identical keyed draws

**Files:**
- Create: `tests/determinism/test_paired_keyed_draw_determinism.py`
- Test: `tests/determinism/test_paired_keyed_draw_determinism.py`

**Interfaces:**
- Consumes: `run(config: RunConfig, out_dir: Path) -> Path` (Task 2); `RunConfig` (including `scheduler`, `admission_theta`, `pregen_low_water_mark`); `Event` JSON field `payload` on `draw.sampled` events (`{stream, key, uniform}`, per §10's key-addressed randomness contract).
- Produces: task-local test helpers only: `_extract_keyed_draws`, `_epoch`.

- [ ] **Step 1: Write the failing test**
```python
# tests/determinism/test_paired_keyed_draw_determinism.py
import json
from pathlib import Path

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.experiments.run import run


def _extract_keyed_draws(events_path: Path) -> dict[tuple, float]:
    raise NotImplementedError


def _epoch() -> CalibrationEpoch:
    a = PortId(module_id="mod-a", port_index=0)
    b = PortId(module_id="mod-b", port_index=0)
    path = make_path_id(a, b)
    return CalibrationEpoch(
        epoch_id="paired-draw-epoch",
        decay_rate_per_class={CoherenceClass.MESSENGER: 0.02, CoherenceClass.MEMORY: 0.005},
        memory_access_channel_s=0.002,
        memory_access_wear_rate=0.01,
        heralding_p_per_path={path: 0.6},
        heralded_fidelity_per_path={path: 0.9},
        round_success_logistic_midpoint=0.5,
        round_success_logistic_slope=8.0,
        round_success_slack_penalty_per_s=0.5,
        decoder_service_rate=4.0,
    )


def test_paired_s0_and_s1_runs_agree_on_every_shared_semantic_draw(tmp_path):
    """§10's common-random-numbers contract: two runs sharing run_seed but using
    different policies (S0 vs S1) must draw the *same* uniform for any semantic
    key (stream, key) both runs happen to touch, even though the policies make
    different numbers of draws in different orders (§16.4)."""
    run_seed = 7
    epoch = _epoch()

    s0_config = RunConfig(
        run_seed=run_seed,
        scheduler="S0",
        epoch=epoch,
        arrival_rate_hz=1.0,
        leases_per_round=1,
        deadline_slack_s=5.0,
        switch_capacity_c=2,
        reconfig_delay_s=0.01,
        max_sim_time_s=100.0,
    )
    s1_config = RunConfig(
        run_seed=run_seed,
        scheduler="S1",
        epoch=epoch,
        arrival_rate_hz=1.0,
        leases_per_round=1,
        deadline_slack_s=5.0,
        switch_capacity_c=2,
        reconfig_delay_s=0.01,
        max_sim_time_s=100.0,
        admission_theta=0.0,  # admit everything: keeps S1's admission decisions
                              # identical to S0's over this light load, so the
                              # two runs' round processing stays aligned and the
                              # shared-key fraction (§10) stays high enough to
                              # give this test a non-trivial sample.
        pregen_low_water_mark=1,
    )

    s0_dir = run(s0_config, tmp_path / "s0")
    s1_dir = run(s1_config, tmp_path / "s1")

    draws_s0 = _extract_keyed_draws(s0_dir / "events.jsonl")
    draws_s1 = _extract_keyed_draws(s1_dir / "events.jsonl")

    shared_keys = set(draws_s0) & set(draws_s1)
    assert len(shared_keys) > 0, "paired runs shared no semantic draw keys at all"

    mismatches = [
        (key, draws_s0[key], draws_s1[key])
        for key in shared_keys
        if draws_s0[key] != draws_s1[key]
    ]
    assert mismatches == [], (
        f"{len(mismatches)}/{len(shared_keys)} shared semantic keys received "
        f"different uniforms across paired S0/S1 runs: {mismatches[:5]}"
    )
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/determinism/test_paired_keyed_draw_determinism.py -v`
Expected: FAIL with `NotImplementedError` raised from `_extract_keyed_draws`
- [ ] **Step 3: Write minimal implementation**
```python
# tests/determinism/test_paired_keyed_draw_determinism.py (helper body, replacing the stub)
def _extract_keyed_draws(events_path: Path) -> dict[tuple, float]:
    """Maps every draw.sampled event to its semantic (stream, key) identity and
    the uniform it drew, so paired runs can be compared key-by-key (§10)."""
    draws: dict[tuple, float] = {}
    for line in events_path.read_text().splitlines():
        if not line:
            continue
        event = json.loads(line)
        if event["event_type"] != "draw.sampled":
            continue
        payload = event["payload"]
        semantic_key = (payload["stream"], tuple(payload["key"]))
        draws[semantic_key] = payload["uniform"]
    return draws
```
- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/determinism/test_paired_keyed_draw_determinism.py -v`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add tests/determinism/test_paired_keyed_draw_determinism.py
git commit -m "test: add paired-run keyed-draw determinism check for shared semantic events"
```