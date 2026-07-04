# Quantum OS Simulator — Design Spec

**Date:** 2026-07-04
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
  researcher, not events/second. Python 3.14, single-threaded core; process-level
  parallelism for sweeps later if needed.
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
4. **V1 = minimal observability + minimal sweep, observability first.**
5. **Bespoke event-heap DES core** (Approach A). No simulation framework dependency.
   Seeded, named RNG streams for common-random-number paired policy comparisons.

## 4. Architecture

Single package `qsim/` with seven sub-packages; dependency arrows point downward only:

| Package | Responsibility |
|---|---|
| `experiments/` | Run configs, single-run driver, thin grid-sweep driver, negative-control harness |
| `workload/` | Closed-loop synthetic demand generator |
| `policies/` | Scheduler protocol and implementations; admission, pre-generation, path allocation as separable mechanisms |
| `models/` | Pluggable physics surfaces (Protocols + v1 analytic implementations) |
| `entities/` | The OS object model as inert dataclasses |
| `observe/` | Trace sink, post-hoc metric views, run summaries |
| `core/` | Event heap, clock, named RNG registry, trace bus, invariant checker, checkpointing |

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

- `QubitHandle` — location, role class (messenger/memory), coherence class,
  calibration epoch.
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

If simulation forces an entity or field the position document lacks, that is a
finding about the OS design and gets recorded as such.

## 6. Model surfaces

All are Protocols in `models/`; v1 ships one analytic, config-parameterized
implementation of each.

| Surface | Answers | v1 implementation | Control setting |
|---|---|---|---|
| `DecayModel` | fidelity(age, coherence class) | exponential decay, per-class constants | **no-decay** (perishability off) |
| `MemoryAccessModel` | cost of interrogating a memory qubit (electron-channel time + fidelity spend) | linear per-access charge | **zero-cost** (free reads) |
| `HeraldingModel` | per-attempt entanglement success | Bernoulli(p) per attempt | — |
| `RoundSuccessModel` | round outcome given lease fidelities, memory ages, decoder latency | threshold/logistic on aggregate fidelity | — |
| `DecoderServiceModel` | service time vs. backlog | distribution + optional backlog penalty | — |

**Two surfaces are required to exist in v1 with controls, not merely planned:**

1. **`DecayModel` with a no-decay control.** The congestion → aging → retry coupling
   is the document's central claim. It must be a switchable surface, not an implicit
   property of the entity code, so the thesis can be tested against its own absence.
2. **`MemoryAccessModel` with a zero-cost control.** Free memory reads are a
   structural omission in the scheduling literature (nobody models read wear), not a
   mis-set parameter. The knob must be deliberately built or no sweep can ever find
   it. Entangled-state coherence (T2* ≈ 2.6 ms in the Song et al. register, vs.
   67–112 ms single-spin) says access costs are plausibly first-order.

## 7. Policies

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

## 8. Workload

Closed-loop synthetic generator: emits `SyndromeRound` demand parameterized by
arrival rate, entanglement demand per round, and deadline tightness; consumes
completion/failure feedback; failed rounds retry per policy. Draws only from the
`workload` RNG stream.

## 9. Observability and data capture

**Norm (standing, from the researcher): capture everything; metrics are derived,
never a substitute.** The trace is the deliverable; re-running because data wasn't
saved is the expensive mistake. Opposite of production logging practice.

Each run produces a **run directory**:

- `header.json` — full resolved config, every RNG stream seed, code git SHA, schema
  version, and an explicit declaration of any filtering in effect (default: none).
  A capped or filtered run must say so here; silent truncation is prohibited.
- `events.jsonl` — every state transition of every entity, timestamped, with event id
  and **causal parent id**. "Why did round N miss its deadline" is a backward walk
  through the trace, never a re-run with more logging.
- `checkpoints/` — full simulator state snapshots including serialized RNG stream
  states; a restored run continues bit-identically. Long warm-ups to steady state are
  snapshotted once and sweeps fork from the warmed state. V1 steady-state detection is
  manual (warmup cutoff recorded in the header).

Metrics are post-hoc views over `events.jsonl` in `observe/views.py`:
freshness-at-consumption distributions, decoder backlog series, deadline compliance,
per-resource utilization, and the logical-error proxy (the aggregate round-failure
rate as scored by `RoundSuccessModel` — a proxy precisely because the scalar core
cannot compute a physical logical-error rate). New question ⇒ new view over old
traces. When volume bites: zstd compression, never sampling.

## 10. Invariants — and the explicit limit of what they prove

`core/` continuously checks **mechanical** correctness: event-time monotonicity,
lease lifecycle legality (no consumption after expiry, no double consumption),
conservation (every lease reaches exactly one terminal state; queue accounting
balances), fidelity within [0, 1]. Violation ⇒ flush trace, crash with the causal
chain of the offending event. Fail-stop, loudly: a silently wrong run poisons
conclusions downstream.

**Scope statement (deliberate):** these invariants prove the bookkeeping is legal.
They provide *zero* protection against a wrong physics model — a backwards coupling
model satisfies every one of them. Model-level correctness is the job of the
negative-control harness (§11) and the metamorphic checks (§12), not the invariant
layer. Passing invariants must never be cited as evidence the conclusions are right.

## 11. Negative-control harness

First-class in `experiments/`, run as part of any result we intend to rely on:

- **No-decay control:** identical config and seeds, `DecayModel` = no-decay. Assert
  the S1−S0 gap on the primary metrics (deadline compliance and logical-error proxy)
  collapses — directionally and quantitatively: report the gap under coupling-on vs.
  coupling-off; the claim is "the gap shrinks by a large, stated factor," not a
  binary pass/fail on a stochastic system.
- **Zero-read-cost control:** identical config and seeds, `MemoryAccessModel` =
  zero-cost. Report how conclusions about memory-resident scheduling move.

Purpose: positive evidence that conclusions depend on the physics we claim they
depend on, rather than on something baked into entities or policies. The engine
invariants prove the bookkeeping; the controls prove the thesis isn't self-fulfilling.

## 12. Testing strategy

1. **Unit tests** (TDD): entity state machines, model implementations against their
   closed-form curves, policy decisions against constructed scenarios.
2. **Limit checks** — named as such, deliberately not called "validation of the
   coupled regime": configure the simulator down to an M/M/1 decoder queue and match
   Little's Law and analytic waits; heralding attempts against Bernoulli/Poisson
   theory. These establish engine correctness *in the decoupled limit only* — the
   regime where the thesis's coupling is absent by construction.
3. **Metamorphic checks in the coupled regime** (oracle-free properties that must
   hold where no closed form exists): faster decay must not improve outcomes;
   no-decay limit must reproduce the standard queueing result; tightening deadlines
   must not increase compliance; increasing heralding success must not increase
   lease expiry counts.
4. **Determinism tests:** same config + seeds ⇒ identical trace hash. Paired S0/S1
   runs draw identical `links`/`decoder`/`workload` streams (common random numbers
   guaranteed by test, not by assumption).

## 13. V1 scope

In: `core/`, `entities/`, the five model surfaces with analytic implementations and
the two required controls, S0 + S1 + the two intermediate ladder rungs, closed-loop
workload, run directories with full traces, checkpointing, the metric views listed in
§9, negative-control harness, a thin grid-sweep driver, the four test tiers.

Out (deferred behind existing interfaces): stabilizer backend, circuit-derived and
trace-replay workloads, automated steady-state detection, sensitivity-ranking
automation, multi-process sweep execution, switch-fabric topologies beyond a single
contended any-to-any switch with capacity C and reconfiguration delay.

## 14. Seed question backlog (physicist-facing)

Maintained in the repo as findings accumulate; initial entries:

1. What does interrogating a nuclear-spin memory actually cost (electron-channel
   time, register fidelity), and how does entangled-state T2* (~2.6 ms reported)
   constrain the usable memory window under repeated access?
2. What is the shape (not just the rate) of fidelity decay for heralded pairs held
   in the fabric — exponential, threshold, other?
3. How does decoder latency couple to round success for SHYPS-class codes — hard
   deadline, soft degradation, or absorbable into the Pauli frame?
