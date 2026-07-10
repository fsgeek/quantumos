# Pre-registration: the field battery (temporal + spatial)

**Date:** 2026-07-06
**Status:** PRE-REGISTERED, amended 2026-07-06 post-build. No DECIDING run of any
test has been executed. One declared loss: the T1 sensitivity CONTROL was smoke-run
during build verification (see the T1 amendment's DECLARED LOSS block); the T1 open
regime is specified for the first time inside this document and has never run. To be
committed and OTS-stamped before any battery run, per the Ayllu falsification
discipline.
**Code state:** all file:line references against commit
`5132b870754de5f900988efd5d2fff9a33b39c81` (HEAD at drafting).
**Provenance:** three-reasoner exchange, 2026-07-06 — Codex (field taxonomy, first
precommit, lease-freshness demotion), Opus (three-tests separation, endogeneity
control, spatial-audit fork), Fable (spatial-domain scoping, fourth ORDERING verdict,
code audit below). Tony challenged the "spatial test cannot be run yet" assertion,
forcing the audit that restructured this document. The three tests' statistics are
DIFFERENT on purpose; testing all three by autocorrelation would erase the taxonomy's
content.

---

## The taxonomy under test (Codex, accepted)

- **GRADIENT-CONSTITUTIVE** — the decision disappears without rate-of-change.
- **GRADIENT-ORDERING** — ∇ could improve ordering, but slope may be derivable from
  simpler state.
- **GRADIENT-FORECASTING** — ∇ is useful only if it predicts future state.
- **FIELD-BLOCKED** — the gradient decision is well-posed but the measured derivative
  carries no actionable signal at decision lead time.
- **NON-FIELD** — no well-posed gradient decision exists.

Verdicts classify **(parameter, decision, regime) triples, not parameters**. Every
verdict is stamped with its operating point and the policy in force. FIELD-BLOCKED is
a regime label.

## Audit results this battery is grounded on (2026-07-06 session)

1. **All exogenous randomness within a run is memoryless by construction.** Arrivals
   are Poisson (`qsim/workload/generator.py:33`); heralding is i.i.d. Bernoulli given
   the epoch (`qsim/models/heralding.py`, thresholded at `qsim/core/engine.py:461`);
   decay is deterministic given the epoch. `RunConfig` carries exactly ONE
   `CalibrationEpoch` per run (`qsim/experiments/config.py:12`) — no epoch sequence
   exists, so within a run the epoch is frozen automatically.
2. **The spatial domain exists in representation, unread by any decision.**
   `PathId = (PortId, PortId)` (`qsim/entities/module.py:20`); per-path
   `heralding_p_per_path` / `heralded_fidelity_per_path` on the epoch
   (`qsim/entities/calibration.py:16-17`); heterogeneous per-path values declarable
   in config TOML today (`qsim/cli.py:69-74`). But path assignment is a round-robin
   counter (`qsim/core/engine.py:310-314`); the scheduler protocol has no path-choice
   hook; uncalibrated paths default to p=0.0 and rounds spin against them to deadline
   death (`qsim/core/engine.py:464-476`). The engine flags its own gap
   (`qsim/core/engine.py:72-75`). The sim's spatial thinness is by-accident, not
   by-design; the prior S1-crash / inert-pregen / uncalibrated-path findings are all
   instances of spatial-variation-present-and-unread.
3. **The pregen pool is inert at HEAD — T1's subject does not yet exist.**
   Documented in `qsim/experiments/run.py:24-30`: `tracked_keys` is empty in M0, the
   engine never deposits to the pool, `withdraw_from_pool` has no callers, and the
   engine drops POOL_REPLENISH requests (`round_id=None` finds no round context,
   `qsim/core/engine.py:324-329`). d(pool)/dt is identically zero at HEAD. This was
   caught during pre-registration verification, BEFORE stamping — the first draft of
   this document precommitted a sensitivity control (S0 churn regime) that was
   incoherent twice over: S0 has no pool by design, and S1's pool is inert. Recorded
   here unredacted as a worked example of why the stamp comes after verification.

## Common discipline (standing method lessons)

- Verify steady state before reading any statistic.
- Knob-motion check before trusting any FLAT result.
- Every verdict stamped with operating point + policy in force.
- **Source-of-structure label on every test:** ENDOGENOUS structure → a finding about
  the modeled system, transfers as a hardware question. AUTHORED structure → a
  dose-response curve only, feeding a physicist question; never a verdict about the
  world.
- **Attribution before transfer (added 2026-07-06, post-build).** "Endogenous" cannot
  distinguish mechanism-as-designed from mechanism-as-implemented: the B3 adversarial
  review caught a replenishment-serialization bug (fixed-order key scan + denial-ends-
  drain; fixed with a rotating cursor, commit 75206ce) that would have produced loud,
  fully endogenous, provenance-control-passing ACF structure that was nothing but a
  key-ordering artifact. No statistic in this battery separates substrate structure
  from bug structure. Therefore: no FIELD-EARNED verdict transfers (to a hardware
  question or a design claim) until the observed structure is attributed to a named,
  INTENDED mechanism cycle, and adversarial code probes against the mechanism are part
  of the instrument, not overhead.
- **Decision lead time is the common currency (added 2026-07-07, external review).**
  Every test names its lead-time variable — the interval between the moment a decision
  could read the signal and the moment that decision's consequences land: T1 = pool
  replenishment latency (the pregen action horizon); T2 = admission-to-decode latency
  (the horizon any backlog-reading decision would act over — instrument-side only,
  per the Register-3 boundary); T3 = scheduling-decision-to-consumption interval;
  T4 = queue lead time (estimate-to-execution); S2 = path-selection-to-herald
  interval and, across epochs, the epoch dwell time. The unified physics-facing
  question every one of Q4–Q6 instantiates: **does the relevant structure persist
  beyond the OS action horizon?**
- **Object-model admission rule (added 2026-07-07, external review).** No quantity
  enters the simulator ontology merely because it is physically meaningful,
  aesthetically natural, or already present in traceable form. Admission is a gate
  cascade, answered in order: (1) DECISION-EARNED — would some policy act
  differently for reading it? If no policy would, it does not enter, however
  physical. (2) REPRESENTATION-CHEAP — if a policy would act, can the action be
  supported by state already in the object model (scalars, timestamps, tables,
  deterministic projections)? If yes, the remedy is to read the object correctly,
  not to extend it. (3) FIELD-EARNED — only if the action requires promoting a
  physical derivative, persistence structure, or non-derivable state does the
  ontology grow, and the new entry must name the decision that reads it and the
  lead time it is read at. The object model contains precisely what decisions read,
  in the cheapest form that preserves the decision. This rule binds future builds,
  and it binds the eventual perishable-good abstraction itself: every fact proposed
  for that abstraction must answer *which decisions read this, at what lead time,
  and why is it not derivable from cheaper represented state?* A battery outcome of
  "the scheduler was leaving value on the table, but the remedy was to read the
  object correctly" is a SUCCESS of this rule, not a failure of the field
  hypothesis.

---

## Temporal battery

### T1 — pool depth (GRADIENT-CONSTITUTIVE; endogenous under controls) — BLOCKED ON B3

**Not runnable at HEAD** (audit item 3): the pool neither fills nor drains, so its
subject does not exist yet. Requires build B3 (wire the deposit/withdraw path — the
future work `run.py` already flags — plus pool trace events sufficient to reconstruct
a depth series: deposit, withdraw, expire, each with sim_time and (path, coherence)
key; the depth series must be derivable from the trace alone, per the
capture-everything norm).

**Statistic:** autocorrelation of d(pool)/dt per tracked (path, coherence) pool, at
pregen-relevant lags. Lags are defined empirically first: measure the
replenishment-latency distribution (POOL_REPLENISH issued → lease HELD;
`qsim/policies/pregen.py:53`) and take its central mass as the relevant lag range.

**Controls:**
- (S) *Sensitivity:* an operating point engineered to produce loud drain structure
  must show detectable autocorrelation, else the test is insensitive and all its
  results are uninterpretable. The first draft named the S0 churn regime here, which
  was incoherent (no pool under S0). The honest state: the sensitivity regime cannot
  be specified until B3 defines how the pool behaves under load; it MUST be amended
  into this document, and stamped, before T1 runs. Candidate: S1-with-pool at
  capacity exhaustion (pool-starved churn).
- (P) *Provenance:* frozen single epoch + Poisson arrivals — both already true by
  construction (audit item 1). Under (P), any observed structure is mechanism-made
  (retry lineages, contention queueing, low-water replenishment cycles), i.e.
  endogenous.

**Precommitted readings:** sensitivity regime shows structure → control passes (not a
finding). De-rigged regime (retry_cap set, sub-capacity load): genuinely open — this
run decides. Structure present under (P) → field-earned at this operating point;
transfers as Simmons Q4 (subject to the attribution requirement). White noise at
relevant lags → FIELD-BLOCKED at this operating point; **no estimator rescue** absent
measurable temporal structure.

#### T1 sensitivity-regime amendment (2026-07-06, post-B3 — supersedes the "cannot be
specified until B3" placeholder above)

B3 landed (branch feat/field-battery-builds, commit d6a8a21 + review fixes 75206ce);
pool behavior under load is now defined: per-key in-flight accounting, trigger
depth + in_flight < L, replenish attempts compete with round demand for §7 slots at
drain opportunities, denial-ends-drain with a rotating per-key scan cursor.
Maintenance is best-effort, not a depth guarantee.

**Control operating point (S1-with-pool, pool-starved churn at capacity exhaustion):**
scheduler="S1", path_policy="round_robin" (do not confound the control with B1),
run_seed=7, arrival_rate_hz=5.0, leases_per_round=1, deadline_slack_s=2.0,
switch_capacity_c=2, reconfig_delay_s=0.1, admission_theta=0.0 (admission inert, so
starvation is capacity-made), pregen_low_water_mark=2, retry_cap=4,
max_sim_time_s ≥ 400 for the stamped run. Epoch: the four capacity-2 adjacent-ring
paths (M0:0–M1:0, M1:0–M2:0, M2:0–M3:0, M0:0–M3:0), heralding_p=1.0 and
heralded_fidelity=0.9 on all four, round_success_logistic_midpoint=-10.0, slope=10.0,
slack_penalty=0.0, decay rates 0.0, memory_access 0.0, decoder_service_rate=1000.0.
Certain heralds + certain success mean deposits come exclusively from replenishment,
which loses the §7 contest often at 5 Hz on a 2-slot fabric holding 0.1 s reconfigs —
depth is held below L by contention.

**Lag definition:** measure the replenishment-latency distribution (POOL_REPLENISH
issued → lease HELD) from the run; its central mass defines the lag window. At this
point latency is dominated by reconfig_delay_s=0.1 s; bin d(pool)/dt at 0.1 s.

**Pass criterion:** reconstruct d(pool)/dt per tracked pool from
pool.deposited/withdrawn/expired deltas ALONE (payload depth fields reserved as an
independent self-check); the control PASSES iff EVERY tracked pool shows |ACF(lag)|
exceeding the 95% white-noise band 1.96/√n_bins at one or more lags in the window,
with sign consistent with the low-water replenishment cycle (negative near one
replenishment latency). If this engineered-loud regime shows no significant ACF,
T1 is insensitive and ALL its results are uninterpretable: do not run the open regime.

**Reconstruction negative control (added 2026-07-07, external review):** permutation
surrogate — shuffle the binned d(pool)/dt series (preserving the marginal delta
distribution) 1000 times; the observed ACF must vanish into the surrogate band,
confirming the structure lives in temporal ORDER, not in binning, reconstruction, or
event-alignment artifacts. Permutation, deliberately NOT phase randomization:
phase-randomized surrogates preserve the power spectrum and hence the ACF by
construction — they test nonlinearity beyond the ACF, not the ACF's reality. Applies
to both the control and open runs.

**Attribution check — operationalized (added 2026-07-07, external review round 2;
the attribution rule enters the pass criterion with the same rigor as the
reconstruction control, because the confound it targets already bit once and passed
every statistical control).** BEFORE the ACF is computed, the analysis derives and
records the predicted lag of every named, INTENDED mechanism cycle at the operating
point: (i) the replenishment cycle — reconfig_delay_s plus herald-service time,
predicted from the replenishment-latency distribution (measured from events that are
not the ACF); (ii) the low-water oscillation — per-pool mean inter-withdrawal time
× L; (iii) the retry cadence, where retries are active — the deadline/retry_cap
lineage cycle. The write-then-look order is binding: predicted lags are recorded in
the run's analysis notes before the ACF is evaluated. FIELD-EARNED additionally
requires every significant ACF lag to be assignable to a named cycle within bin
tolerance. Significant structure at a lag NO named cycle predicts → verdict
**ATTRIBUTION-FAILED**: transfer blocked, mandatory adversarial mechanism probe (the
serialization-bug playbook, commit 75206ce) before any interpretation. The same rule
binds T2, with its own named cycles (decoder service time 1/rate; M/M/1 busy-period
relaxation at the operating point's utilization).

**DECLARED LOSS — calibration by peeking (read before stamping):** this control
regime was smoke-run during build verification (2026-07-06, 40 s horizon, seed 7)
to confirm it is loud: lag-1 ACF between −0.25 and −0.35 in all four pools against a
±0.098 white-noise band. The control's expected reading is therefore informed by
observation, and the control passing carries even less evidential weight than a
control normally does — it is calibration, full stop. This is legitimate for a
control (a control that cannot fire is useless) and fatal for the open regime, which
is why the open regime is precommitted below, config-first, before any run of it
exists. The smoke run's existence is disclosed here so the OTS stamp covers the
disclosure.

**OPEN (de-rigged) operating point — precommitted blind (no run of this config has
ever been executed; it is specified for the first time in this amendment):**
scheduler="S1", path_policy="round_robin", run_seed=11, arrival_rate_hz=1.0
(sub-capacity), leases_per_round=1, deadline_slack_s=5.0, switch_capacity_c=2,
reconfig_delay_s=0.01, admission_theta per the S1 example convention,
pregen_low_water_mark=2, retry_cap=4, max_sim_time_s ≥ 400, decay ON
(decay_rate_per_class: messenger 0.01, memory 0.001), same four-path fabric with
heralding_p=0.7 and heralded_fidelity=0.95 on all paths (homogeneous — spatial
heterogeneity belongs to S1/S2, not T1), round_success midpoint=0.5, slope=10.0,
slack_penalty=1.0, decoder_service_rate=5.0. Same lag definition and ACF statistic
as the control. Standing discipline applies: steady-state check before reading;
knob-motion check (arrival_rate 1.0 → 0.5 must visibly move pool dynamics) before
trusting any flat result. Tony may amend these values BEFORE the stamp; after the
stamp they are fixed.

**Canonical config artifacts (added 2026-07-07, external review round 2):** both
operating points exist as canonical bytes committed in the same stamped tree:
`examples/t1-control.toml`
(sha256 `b3d2f4c7c7e77a1606e6e0524fa8755af5f7c1bee12ec3ece2568f326198ac2e`) and
`examples/t1-open.toml`
(sha256 `3fb44bc4d9255c4ba250fb23ebfc6d5ea1c5665f09dd60fc7756904e9454cd3c`).
Both were CLI-validated only (parse — validation executes nothing). Scope of proof,
stated honestly: no artifact can prove a past negative; the hash does NOT prove the
open config was never run pre-stamp — that residue remains trust, with a small
surface (the config was first specified hours before commit, in a recorded session).
What the artifact instruments is forward provability: run headers record git
provenance, so **every presentable T1-open result must come from a run whose
header.json git SHA is a descendant of the stamped commit** — a result that cannot
show that lineage is inadmissible under this pre-registration. Amending either file
after the stamp voids the corresponding run plan until re-stamped.

**Interpretive confound (pinned):** deadline_slack_s doubles as the pooled-lease
freshness bound (B3 deliberately introduced no new duration, honoring the parked
boundary), so any slack sweep moves round deadlines AND pool expiry together. T1
runs pin slack (2.0 s control / 5.0 s open) and count pool.expired as drain.

### T2 — decoder backlog slope (GRADIENT-CONSTITUTIVE; downstream of T1)

**Statistic:** same autocorrelation, on backlog slope. Observable at HEAD:
`decoder.enqueued` / `decoder.completed` / `decoder.cancelled` events exist and
`observe.views.decoder_backlog_series` already reconstructs the series (all three
event types handled, `qsim/observe/views.py:54-66`). T2 is therefore runnable before
T1. Its decomposition, however, is conditional on T1 (syndrome arrivals inherit the
quantum side's noise): T1 blocked & T2 blocked → consistent inheritance. T1 blocked &
T2 earned → independent classical structure (service dynamics). T1 earned → decompose
inherited vs. intrinsic structure before crediting T2 independently. A T2 result
obtained before T1 exists is recorded but not interpreted against the inheritance
question until T1 runs.

**Boundary:** measuring slope autocorrelation is instrument-side observation. Wiring
backlog slope into any scheduler decision remains forbidden until the Register-3
coupling question returns from physics (parked note, 2026-07-05).

### T3 — lease-freshness rank inversion (GRADIENT-ORDERING)

**Statistic:** inversion rate between (a) order-by-current-fidelity and (b)
order-by-projected-fidelity-at-consumption, over co-pending lease sets at scheduling
decision points.

**Precommitted thresholds (added 2026-07-07, external review):** a co-pending set is
nondegenerate iff it holds ≥ 2 leases. INVERSIONS FREQUENT iff (a) more than 10% of
nondegenerate decision points show at least one pairwise inversion, AND (b) the
median projected retention delta across inverted pairs exceeds 0.01 absolute —
computed analytically from the trace (exp(−rate·age) at projected consumption time).
The materiality bound is PROJECTED, deliberately not observed: measuring a realized
outcome delta would require running the alternative ordering, which is an
intervention study (S2's shape), not T3's read-only reconstruction. (a) fails →
INVERSIONS RARE. (a) passes, (b) fails → "frequent but immaterial": the demotion
stands, noted. The thresholds are round numbers fixed before any run; their
arbitrariness is the price of unarguability.

**Precommitted verdict space (four outcomes):**
1. Inversions rare → the enum+scalar demotion stands.
2. Inversions frequent → **DECISION-EARNED, REPRESENTATION-CHEAP**: the current
   scheduler leaves fidelity on the table, and the fix is a projection from existing
   scalars — `exp(-rate_class · (t_consume − heralded_at))` — NOT a field. This is
   the only outcome in the battery with a live operational payoff independent of the
   field question. Frequent inversions do NOT re-promote lease freshness to field.
3. Field re-entry requires decay-rate variation over an observable domain — out of
   scope for the current model (class-constant by construction) — re-enters only via
   the spatial battery or a hardware answer.
4. No well-posed ordering decision at the operating point (degenerate batches of
   size ≤ 1 dominate) → NON-FIELD at this operating point; retest under higher
   concurrency.

### T4 — calibration drift (GRADIENT-FORECASTING; 100% authored — dose-response ONLY)

**No in-sim verdict is possible, ever, for this one.** The epoch sequence does not
exist yet (audit item 1); once built (B2), its temporal structure is authored by us.
Design: author epoch-walk processes with parameterized persistence (e.g. AR(1) with
φ swept, plus reset events); out-of-sample backtest of drift-extrapolation vs.
drift-ignoring at queue lead times. Output: the persistence threshold φ* at which
forecasting starts to pay. Feeds Simmons Q5. **An autocorrelation surrogate is
explicitly disallowed** — smooth drift autocorrelates while resets carry the surprise
(false pass). Requires build B2; not runnable tonight.

---

## Spatial battery (unblocked by the audit)

### S1 — cost of spatial blindness (ZERO build; runnable tonight)

Author a multi-path epoch with heterogeneous `heralding_p` / `heralded_fidelity`
(config file only). Run the existing round-robin engine. Measure outcome degradation
vs. heterogeneity magnitude — the dose-response curve for quality-blind assignment.
The prior findings already showed the maximal-heterogeneity point (p=0 paths, total
cost); S1 fills in the curve. **Authored-structure label applies:** the heterogeneity
dial is ours; the curve is the deliverable; where real hardware sits on it is
Simmons's to supply (Q6).

**Precommitted grid (added 2026-07-06):** four-path fabric as in T1; heralding_p
spread δ ∈ {0, 0.1, 0.2, 0.4} across the four paths at fixed mean p̄=0.7 (e.g. δ=0.2
→ {0.5, 0.633, 0.767, 0.9}); otherwise the T1 open-regime physics. Outcome measures:
deadline compliance and fidelity-at-outcome distributions. δ=0 is the homogeneity
anchor (any effect at δ=0 is a bug, not a curve).

**Grid amendment (added 2026-07-10, before any S1 run exists):** the δ=0.4 arm is
infeasible at p̄=0.7 — by this document's own δ=0.2 example fixing δ as half-spread,
δ=0.4 yields heralding_p = 1.1 > 1. Amended grid: δ ∈ {0, 0.1, 0.2, 0.3}, where
δ=0.3 is the widest feasible half-spread at p̄=0.7 (→ {0.4, 0.6, 0.8, 1.0}). The
δ=0.4 arm stays in the sweep request and is recorded in the manifest as an
in-artifact refusal, so the original precommitment and its correction are both
visible in the run record. (Infeasibility found by the sweep-runner plan, recorded
in `qsim/experiments/sweep.py` and the 2026-07-09 open-run-decisions note, both
predating this amendment and any S1 data.)

**Dose-response reading (added 2026-07-07, external review):** expected direction is
degradation increasing with δ, but strict per-metric monotonicity is NOT required —
deadline compliance and fidelity interact nonlinearly (e.g. a starved path can shed
load in ways that help survivors). Requirement: the curve must be interpretable as a
dose-response; non-monotonicity triggers a mechanism audit under the attribution
rule, not automatic failure.

### S2 — spatial ORDERING test (requires build B1)

**B1:** promote path selection from engine counter (`engine.py:310`) to a policy
decision point — the contract change the code already flags for reconciliation.
Then: does route-by-comparative-path-quality change routing vs. round-robin, and what
does it buy? Verdict space mirrors T3, including DECISION-EARNED /
REPRESENTATION-CHEAP (comparative read of the existing epoch table, QOS-style; no new
state needed).

**Rigged-result warning (spatial edition):** with one frozen epoch, spatial quality
is trivially persistent, so any payoff here licenses conclusions about **comparative
reading at fixed quality only — not about prediction.** Prediction-proper requires B2
epoch sequences with the QOS property (heterogeneous across paths, autocorrelated in
time per path), and even then the result is a dose-response over authored persistence,
not a verdict.

---

## Builds licensed by this pre-registration (and no more)

- **B1** — path-choice policy hook (small; a flagged contract gap, not new concept).
- **B2** — epoch-sequence support (small).
- **B3** — wire the pregen pool deposit/withdraw path plus pool trace events
  (small; the flagged future work of `run.py:24-30`, not new concept). T1's
  sensitivity regime must be amended into this document after B3 lands and before
  T1 runs.
- **NOT licensed:** deadline-semantics rebuild, backlog-coupling model, duration
  separation — all still parked per the 2026-07-05 note. Naming the perishable-good
  abstraction is not decided by this battery.

## Dependency and run order

Status 2026-07-06 post-build: B3 and B1 are LANDED on feat/field-battery-builds
(365 tests green; S0 traces byte-identical to main under the repo's run-id
normalization convention; B2 remains blocked on Q7/Q8). T3's feasibility check came
back CONFIRMED — co-pending lease sets, consumption times, and failure-side
fidelities are reconstructible from existing events (lease.consumed carries
fidelity_at_consumption; lease.outcome_fidelity covers every terminal; lease_ids
recur across retries, so episodes segment by seq order).

Runnable once this document is committed and stamped: T1 (control first, then open),
T2, T3, S1, S2. T4 after B2, which waits on Q7/Q8. T2's inheritance decomposition
waits for T1's result even if T2 runs first. Nothing in this battery runs before the
stamp. The endgame question — is anything actionably predictable independent of the
heralding floor — decomposes cleanly: temporal half = T1/T2; spatial half = S2+B2
dose-response plus Simmons Q6. **A clean temporal FIELD-BLOCKED sweep, combined with
the QOS spatial prior (spatial estimation at 99% accuracy while temporal prediction
is disclaimed), redirects the search to the spatial battery.** The temporal battery
alone cannot distinguish "prediction lives in space" from "prediction lives
nowhere" — the QOS prior is the symmetry-breaker, credited here so the temporal
null is never read as directional evidence on its own; making that distinction is
what S2 + B2 + Q6 exist for.

## Physicist-facing questions this battery generates (the ayni payload)

- **Q4** (from T1): does the hardware heralding/demand process have temporal
  structure at pregen-relevant lags, or is it memoryless at every timescale an OS
  could exploit? Our model only rewards pre-generation if autocorrelation exists at
  lags ≥ replenishment latency.
- **Q5** (from T4): does calibration drift have persistence ≥ φ* at scheduling lead
  times? (Prior from QOS, superconducting, in the wild: "there is no way to predict
  a QPU's future calibration data.")
- **Q6** (from S1/S2): is T-centre path quality QOS-shaped — spatially heterogeneous
  and temporally stable at lead time — or does the switched photonic fabric reshuffle
  which path is best faster than a scheduler can read it?
- **Q7** (from B2 blocker D-A, added 2026-07-06): when calibration changes while a
  pair is in flight, how does its effective decay reprice — retroactively at the new
  calibration (the sim's current mechanical behavior), piecewise across the boundary,
  or frozen at birth-epoch calibration? These are three different physical models,
  not three code paths — the ruling defines the ontology of the resource (what an
  in-flight pair IS across a calibration boundary). B2's swap semantics wait on
  this; the sim will not invent it.
- **Q8** (from B2 blocker D-B, added 2026-07-06): do decoder-service and
  round-success characteristics drift on the same cycle as heralding/decay
  calibration, or are they stable across epochs? (Decides whether those two model
  surfaces must track the active epoch or may stay constructor-baked, documented.)
- Q1–Q3 (parked note, 2026-07-05) unchanged and still owed to Simmons.

## What this battery does not decide

The name of the perishable-good abstraction; cliff-vs-slope; the backlog coupling.
The three-register discipline of the parked note continues to apply.
