# Quantum OS Simulator — Design Spec

**Date:** 2026-07-04 (revised same day after two review rounds; see
`2026-07-04-quantum-os-simulator-design-review.md` (Codex) and
`2026-07-04-quantum-os-simulator-design-gemini-review.md` (Antigravity/Gemini))
**Status:** Draft for review
**Companion document:** `docs/quantum_os_.md` (the constraint-first quantum OS position document; this simulator is its executable counterpart)

## 1. Purpose and success criterion

A discrete-event simulator of a Photonic-style entanglement-first quantum computer's
resource-management layer. It is a **sensitivity instrument, not a predictor**: its
output is not "the machine will behave like X" but "the systems conclusions are
sensitive to physics parameters A and C and insensitive to B."

**Success criterion:** the simulator is working if it enables us to formulate the
right questions to ask physicists, ranked by how much their answers change the
behavior of the system layer above them.

This mirrors the HSD optical-storage methodology: sweep the media/physics parameters
you cannot know, and map where the management layer's behavior changes qualitatively.
Questions that require privileged hardware access become parameter axes, not blockers.

## 2. Non-goals

- Point predictions of any real machine's performance.
- Physically grounded logical-error rates (deferred to a future stabilizer backend).
- Production-quality throughput. The instrument is bounded by iteration speed of the
  researcher, not events/second. Single-threaded core; process-level parallelism for
  sweeps later if needed.
- Publishable statistical rigor in v1. Observability and correct dynamics first.

## 3. Locked design decisions

1. **Understanding instrument first**; reusable research platform is a stretch goal.
   Evolvability is achieved through interfaces, not up-front generality.
2. **Scalar-fidelity core with pluggable model surfaces.** Quantum state is
   represented by scalar fidelity/freshness values evolving under parameterized
   models. Every model surface is a Protocol so a Pauli-frame/stabilizer backend
   (or a physicist-supplied model) can replace the analytic v1 implementation later.
3. **Closed-loop synthetic workload.** Demand responds to system state (retries,
   stalls, backlog). Open-loop traces and circuit-derived workloads are later
   additions behind the same generator interface.
4. **V1 = minimal observability + minimal sweep, observability first**, sequenced as
   two milestones (§17).
5. **Bespoke event-heap DES core** (Approach A). No simulation framework dependency.
   Key-addressed randomness for common-random-number paired policy comparisons (§10).
6. **Python ≥3.14 is a repository toolchain constraint** (owner's decision, already
   in `pyproject.toml`), not a simulator design requirement. The design uses no
   3.14-only features; nothing below depends on the version.

## 4. Architecture

Single package `qsim/` with seven sub-packages; dependency arrows point downward only:

| Package | Responsibility |
|---|---|
| `experiments/` | Run configs, single-run driver, thin grid-sweep driver, negative-control harness |
| `workload/` | Closed-loop synthetic demand generator |
| `policies/` | Scheduler protocol and implementations; admission, pre-generation, path allocation as separable mechanisms |
| `models/` | Pluggable physics surfaces (Protocols + v1 analytic implementations) |
| `entities/` | The OS object model as inert dataclasses |
| `observe/` | Trace sink, post-hoc metric views, run summaries, work accounting |
| `core/` | Event heap, clock, keyed RNG (§10), trace bus, invariant checker, checkpointing (§13) |

**Separation rule:** entities are inert state, policies make decisions, models answer
physics questions. Anything one needs to know while implementing a `models/` surface
is by construction a physicist question; everything in `policies/` is systems work.

**Data flow for one syndrome round:** workload emits round request → scheduler
admits/defers (S1 consults freshness projections; S0 does not) → lease requests
trigger switch-path reservations → heralding attempts fire stochastically until
success or deadline → successful leases age under the decay model while the round
assembles → memory-qubit interrogations charge costs via the memory-access model →
round executes, enqueues a decoder job → decoder completion + lease fidelities feed
the round-success model → outcome returns to the workload generator, which retries
failures. Every transition publishes to the trace bus.

## 5. Entity model

Plain dataclasses mirroring the position document's object model, with explicit
lifecycle state machines and no embedded decisions:

- `Module` / `PortId` — each module exposes a fixed set of optical ports,
  identified as `(module_id, port_index)`. Ports are the unit of endpoint
  exclusivity in §7; lease endpoints and switch reservations reference `PortId`s,
  not bare modules.
- `QubitHandle` — location (module), role class (messenger/memory), coherence
  class, calibration epoch, and fidelity-tracking state: `state_held_since` plus
  fidelity at that instant. Passive decay of held state is materialized lazily —
  the engine evaluates the closed-form `DecayModel.retention` from these
  timestamps at access and evaluation instants; nothing updates per tick.
- `EntanglementLease` — endpoints, creation time, freshness bound, fidelity estimate,
  path identity, heralding metadata, retry policy. Lifecycle:
  requested → heralded → (consumed | expired | cancelled), exactly one terminal state.
- `SyndromeRound` — constituent leases, participating qubits, completion deadline,
  outcome.
- `DecoderJob` — service demand, priority, enqueue/dequeue/completion times.
- `SwitchPathReservation` — path, holder, acquire/release times.
- `CalibrationEpoch` — versioned parameter snapshot the scheduler consults.
- `PauliFrameToken` — deferred-correction marker (v1: counted, not semantically
  modeled; exists so fast-path pressure relief is observable later).

**Failure cleanup (normative):** when a `SyndromeRound` fails or is cancelled, its
resources are released in a defined cascade, immediately at the failure event:
decoder jobs for the round are cancelled; switch-path reservations held on its
behalf are released; unconsumed leases are disposed per policy — round-bound
policies (S0) cancel them, pooling policies (pre-generation) return still-fresh
leases to the pool and expire the rest. Every disposition is a distinct trace event,
and the work accounting (§11) records pool returns separately so reuse is visible
rather than silent.

If simulation forces an entity or field the position document lacks, that is a
finding about the OS design and gets recorded as such. (`Module`/`PortId` is the
first such finding: §7's endpoint-exclusivity rule is not expressible in the
position document's object model, which names switch paths but not ports.)

## 6. Model surfaces

All are Protocols in `models/`; v1 ships one analytic, config-parameterized
implementation of each.

**Conventions (binding on all surfaces):** all times are simulation seconds
(`float`); fidelities and retention factors are dimensionless in [0, 1]; models are
pure functions of their arguments plus the `CalibrationEpoch` — they hold no mutable
state and perform no random draws. All randomness is drawn by the engine through the
keyed-RNG contract (§10): models return probabilities (or take an engine-supplied
`Draw` where a sample is unavoidable), and the engine thresholds keyed uniforms
against them.

```python
class DecayModel(Protocol):
    def retention(self, age_s: float, coherence: CoherenceClass,
                  epoch: CalibrationEpoch) -> float:
        """Multiplicative retention in [0,1].
        fidelity(t) = fidelity_at_herald * retention(t - t_herald, class, epoch)."""

class MemoryAccessModel(Protocol):
    def access_cost(self, qubit: QubitHandle,
                    epoch: CalibrationEpoch) -> AccessCost:
        """AccessCost = (electron_channel_s: float, retention_factor: float).
        Composes AFTER passive decay is applied up to the access instant:
        f_after = f_decayed_to_now * retention_factor."""

class HeraldingModel(Protocol):
    def success_probability(self, path: PathId,
                            epoch: CalibrationEpoch) -> float:
        """Per-attempt heralding success probability."""

    def heralded_fidelity(self, path: PathId,
                          epoch: CalibrationEpoch) -> float:
        """Initial fidelity of a successfully heralded pair on this path —
        the `fidelity_at_herald` term consumed by DecayModel."""

class RoundSuccessModel(Protocol):
    def success_probability(self, lease_fidelities: Sequence[float],
                            memory_retentions: Sequence[float],
                            decoder_latency_s: float,
                            deadline_slack_s: float) -> float:
        """Round success given inputs at execution time. decoder_latency_s is the
        raw duration; deadline_slack_s = deadline - completion time (may be
        negative). The v1 implementation is threshold/logistic on aggregate
        fidelity with a slack penalty."""

class DecoderServiceModel(Protocol):
    def service_time_s(self, job: DecoderJob, backlog: int,
                       draw: Draw) -> float:
        """Sampled service time; `draw` is an engine-supplied keyed source."""
```

| Surface | v1 implementation | Control setting |
|---|---|---|
| `DecayModel` | exponential decay, per-class constants | **no-decay** (retention ≡ 1) |
| `MemoryAccessModel` | linear per-access charge | **zero-cost** (free reads) |
| `HeraldingModel` | Bernoulli(p) per attempt | — |
| `RoundSuccessModel` | threshold/logistic on aggregate fidelity | — |
| `DecoderServiceModel` | distribution + optional backlog penalty | — |

**Two surfaces are required to exist in v1 with controls, not merely planned:**

1. **`DecayModel` with a no-decay control.** The congestion → aging → retry coupling
   is the document's central claim. It must be a switchable surface, not an implicit
   property of the entity code, so the thesis can be tested against its own absence.
2. **`MemoryAccessModel` with a zero-cost control.** Free memory reads are a
   structural omission in the scheduling literature (nobody models read wear), not a
   mis-set parameter. The knob must be deliberately built or no sweep can ever find
   it. Entangled-state coherence (T2* ≈ 2.6 ms in the Song et al. register, vs.
   67–112 ms single-spin) says access costs are plausibly first-order.

## 7. Switch fabric — v1 semantics

One any-to-any crossbar connecting all modules. A path conflicts with the system
state iff any of the following holds, and these are the *only* conflicts modeled:

1. **Endpoint port exclusivity** — each module optical port carries at most one
   active path; a second path touching an occupied port blocks.
2. **Global concurrent-path capacity** — at most `C` simultaneously configured
   paths fabric-wide.
3. **Reconfiguration delay** — a newly configured path is unusable for δ seconds
   after acquisition (heralding attempts may not start during δ); other paths are
   unaffected.

**Reservation lifecycle:** acquired → configuring (δ, path unusable) → active
(heralding attempts run) → released. Release occurs at the first of: heralding
success (the entangled state now lives in spins; the optical path is free),
attempt-window/deadline expiry, or round cancellation (§5 cleanup cascade). A
config flag (`hold_until_consumption`, default off) instead holds the path until
the lease reaches a terminal state, for architectures where the path is needed
beyond heralding — deliberately a parameter, because it drastically changes
effective fabric concurrency.

No per-link capacities, no partial-path blocking, no wavelength constraints in v1.
Any scheduler conclusion about path allocation or pre-generation is conditional on
this abstraction; the switch model is itself a sensitivity surface, and richer
topologies are deferred behind `SwitchPathReservation`'s interface.

## 8. Policies

`Scheduler` Protocol; implementations composed from separable mechanisms so the
ablation ladder is configuration, not code:

- **S0** — competent baseline: deadline scheduling, priorities, entanglement retry.
  Everything a good real-time engineer builds without the perishability insight.
  Explicitly not a strawman.
- **S0 + freshness-aware admission control**
- **S0 + lease pre-generation**
- **S1** — both mechanisms.

The claim under test is that S1's advantage is attributable to the named mechanisms.
The ladder isolates each.

## 9. Workload

Closed-loop synthetic generator: emits `SyndromeRound` demand parameterized by
arrival rate, entanglement demand per round, and deadline tightness; consumes
completion/failure feedback; failed rounds retry per policy. All stochastic choices
use `workload`-stream keyed draws (§10).

## 10. Randomness and the common-random-numbers contract

Named streams alone are insufficient for paired policy comparisons: policies make
different numbers of draws in different orders, so sequential shared streams diverge
structurally. The engine therefore uses **key-addressed randomness**:

- Every draw is `draw(stream, key)` where `key` is a stable semantic identity —
  e.g. `("herald", round_id, endpoint_pair, attempt_no)` or
  `("decode", job_id)` — and the generator is seeded from a **deterministic**
  hash: SHA-256 (or an equivalent stable hash) over a canonical serialization of
  `(run_seed, stream, key)`. Python's builtin `hash()` is prohibited here — it is
  salted per-process, which would silently break determinism across runs, forks,
  and sweep workers.
- The same semantic event receives the same randomness in every run with the same
  `run_seed`, regardless of policy-induced differences in draw order or count.
- Draws that exist under only one policy (e.g. pre-generation attempts S0 never
  makes) simply have no counterpart; the comparison remains fair on all shared
  semantic events. This is the accepted, expected form of divergence.
- Success probabilities are realized by thresholding the keyed uniform against the
  model's probability, so raising a probability parameter flips outcomes
  monotonically — several metamorphic tests (§16) rely on this coupling.

Round ids, job ids, and attempt numbers must therefore be assigned from semantic
context (workload arrival index, retry ordinal), never from draw order or event-heap
order.

## 11. Work accounting and comparison metrics

Because the workload is closed-loop, policy changes alter the demand actually
presented to the system. Every run therefore records, as distinct quantities:
**offered** logical rounds (first arrivals), **retries**, **attempts**
(offered + retries), **admitted**, **deferred**, **dropped**,
**completed-in-deadline**, **completed-late**, **failed**.

**Primary cross-policy metrics are normalized by offered work:** goodput =
completed-in-deadline / offered; logical-error proxy = round failures scored by
`RoundSuccessModel`, aggregated over offered work. Compliance-among-admitted and
similar conditional metrics are reported but are never primary — an admission
controller can trivially improve them by rejecting work.

## 12. Observability and data capture

**Norm (standing, from the researcher): capture everything; metrics are derived,
never a substitute.** The trace is the deliverable; re-running because data wasn't
saved is the expensive mistake. Opposite of production logging practice.

Each run produces a **run directory**:

- `header.json` — full resolved config, `run_seed`, run identity and provenance
  (§13), code git SHA, schema version, and an explicit declaration of any filtering
  in effect (default: none). A capped or filtered run must say so here; silent
  truncation is prohibited.
- `events.jsonl` — every state transition of every entity, timestamped, with event id
  and **causal parent id**. "Why did round N miss its deadline" is a backward walk
  through the trace, never a re-run with more logging.
- `checkpoints/` — full simulator state snapshots (§13).

Metrics — freshness-at-consumption distributions, decoder backlog series, deadline
compliance, per-resource utilization, the work-accounting table (§11), and the
logical-error proxy — are all post-hoc views over `events.jsonl` in
`observe/views.py`. New question ⇒ new view over old traces. When volume bites:
zstd compression, never sampling.

## 13. Run identity, checkpointing, and replay semantics

- **Run identity:** every run has a fresh `run_id`. Event ids are
  `(run_id, seq)` with `seq` monotonically increasing within the run.
- **Checkpoints** serialize the complete simulator state: entities, queues, clock,
  and pending event heap. Keyed randomness (§10) is stateless given `run_seed`, so
  no generator state needs saving — a restored run redraws identically by key.
- **Restore semantics: the checkpoint is authoritative.** A run forked from a
  checkpoint gets a fresh `run_id`; its header records provenance
  `{parent_run_id, checkpoint_id, parent_seq}`. Its `events.jsonl` contains only
  post-fork events. Causal parent ids may reference pre-fork events as
  `(parent_run_id, seq)`, resolvable through the provenance chain.
- **Trace-hash scope:** the determinism guarantee (§16) is over a run's own
  `events.jsonl` — for a forked run, the post-fork stream given the same checkpoint
  and `run_seed`. Paired comparisons across forks of the same warmed checkpoint are
  valid because state and keyed randomness are both shared at the fork point.
- Long warm-ups to steady state are snapshotted once; sweeps fork many runs from the
  warmed state. V1 steady-state detection is manual (a warmup cutoff recorded in the
  header).

## 14. Invariants — and the explicit limit of what they prove

`core/` continuously checks **mechanical** correctness: event-time monotonicity,
lease lifecycle legality (no consumption after expiry, no double consumption),
conservation (every lease reaches exactly one terminal state; queue and work
accounting balance), fidelity within [0, 1], and resource-leak freedom (no
`SwitchPathReservation` outlives its holding attempt or round — the §5 cleanup
cascade is checked, not assumed; a leaked port or path slot fails the run). Violation ⇒ flush trace, crash with the
causal chain of the offending event. Fail-stop, loudly: a silently wrong run poisons
conclusions downstream.

**Scope statement (deliberate):** these invariants prove the bookkeeping is legal.
They provide *zero* protection against a wrong physics model — a backwards coupling
model satisfies every one of them. Model-level correctness is the job of the
negative-control harness (§15) and the metamorphic checks (§16), not the invariant
layer. Passing invariants must never be cited as evidence the conclusions are right.

## 15. Negative-control harness

First-class in `experiments/`, run as part of any result we intend to rely on. The
controls use the ablation ladder (§8), because S1's mechanisms can help through
congestion management even when perishability is absent — a full-gap-collapse claim
would overreach:

- **No-decay control:** identical config and `run_seed`, `DecayModel` = no-decay,
  reported across the full ladder. Required assertions: (a) the increment of
  freshness-aware admission — (S0+admission) − S0 — collapses under no-decay, since
  its input signal is constant; (b) the **perishability-attributable quantity**,
  the difference-in-differences [(S1−S0) under decay-on] − [(S1−S0) under
  decay-off], is large by a stated factor on the primary metrics (§11).
  Pre-generation's residual congestion benefit under no-decay is expected and
  reported, not asserted away.
- **Zero-read-cost control:** identical config and `run_seed`,
  `MemoryAccessModel` = zero-cost. Report how conclusions about memory-resident
  scheduling move across the ladder.

Purpose: positive evidence that conclusions depend on the physics we claim they
depend on, rather than on something baked into entities or policies. The engine
invariants prove the bookkeeping; the controls prove the thesis isn't self-fulfilling.

## 16. Testing strategy

1. **Unit tests** (TDD): entity state machines, model implementations against their
   closed-form curves, policy decisions against constructed scenarios.
2. **Limit checks** — named as such, deliberately not called "validation of the
   coupled regime": configure the simulator down to an M/M/1 decoder queue and match
   Little's Law and analytic waits; heralding attempts against Bernoulli/Poisson
   theory. These establish engine correctness *in the decoupled limit only* — the
   regime where the thesis's coupling is absent by construction.
3. **Metamorphic checks in the coupled regime** — oracle-free properties, each
   qualified to **fixed policy, same `run_seed`, primary (offered-normalized)
   metrics** (§11), because adaptive admission can otherwise game conditional
   metrics (e.g. stricter decay improving compliance-among-admitted by rejecting
   more work): faster decay must not increase goodput; the no-decay limit must
   reproduce the standard queueing result; tightening deadlines must not increase
   goodput; raising heralding success must not decrease goodput. (An earlier draft
   asserted raising heralding success must not increase lease-expiry counts; that
   relation is false under congestion — more heralded leases waiting on a
   backlogged decoder means more candidates to expire — and is recorded here as a
   rejected property so it is not reintroduced.) The monotone keyed-draw coupling
   (§10) makes these near-deterministic per seed.
4. **Determinism tests:** same config + `run_seed` ⇒ identical trace hash (scope per
   §13). Paired runs receive identical keyed draws on shared semantic events —
   guaranteed by test, not by assumption.

## 17. V1 scope and milestones

**M0 — acceptance milestone (trace contract proven):** `core/` (event heap, keyed
RNG, trace bus, invariants), `entities/`, the five model surfaces with analytic
implementations, S0 and S1 only, closed-loop workload, run directories with full
traces and work accounting, the §12 metric views, determinism tests, limit checks.
The trace schema is frozen at the end of M0.

**M1 — completes v1:** the two intermediate ladder rungs, negative-control harness,
checkpoint/fork/replay (§13), thin grid-sweep driver, metamorphic checks.

Out of v1 (deferred behind existing interfaces): stabilizer backend, circuit-derived
and trace-replay workloads, automated steady-state detection, sensitivity-ranking
automation, multi-process sweep execution, switch topologies beyond §7.

## 18. Seed question backlog (physicist-facing)

Maintained in the repo as findings accumulate; initial entries:

1. What does interrogating a nuclear-spin memory actually cost (electron-channel
   time, register fidelity), and how does entangled-state T2* (~2.6 ms reported)
   constrain the usable memory window under repeated access?
2. What is the shape (not just the rate) of fidelity decay for heralded pairs held
   in the fabric — exponential, threshold, other?
3. How does decoder latency couple to round success for SHYPS-class codes — hard
   deadline, soft degradation, or absorbable into the Pauli frame?
