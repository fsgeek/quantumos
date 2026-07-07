# Pre-registration: the field battery (temporal + spatial)

**Date:** 2026-07-06
**Status:** PRE-REGISTERED. No test in this battery has been run. To be OTS-stamped
before any run per the Ayllu falsification discipline.
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

## Common discipline (standing method lessons)

- Verify steady state before reading any statistic.
- Knob-motion check before trusting any FLAT result.
- Every verdict stamped with operating point + policy in force.
- **Source-of-structure label on every test:** ENDOGENOUS structure → a finding about
  the modeled system, transfers as a hardware question. AUTHORED structure → a
  dose-response curve only, feeding a physicist question; never a verdict about the
  world.

---

## Temporal battery

### T1 — pool depth (GRADIENT-CONSTITUTIVE; endogenous under controls)

**Statistic:** autocorrelation of d(pool)/dt per tracked (path, coherence) pool, at
pregen-relevant lags. Lags are defined empirically first: measure the
replenishment-latency distribution (POOL_REPLENISH issued → lease HELD;
`qsim/policies/pregen.py:53`) and take its central mass as the relevant lag range.

**Controls:**
- (S) *Sensitivity:* the S0 unbounded-retry churn regime must show detectable
  autocorrelation. If the test cannot see structure that loud, all its results are
  uninterpretable — stop and fix the instrument.
- (P) *Provenance:* frozen single epoch + Poisson arrivals — both already true by
  construction (audit item 1). Under (P), any observed structure is mechanism-made
  (retry lineages, contention queueing, low-water replenishment cycles), i.e.
  endogenous.

**Precommitted readings:** churn regime shows structure → control passes (not a
finding). De-rigged regime (retry_cap set, sub-capacity load): genuinely open — this
run decides. Structure present under (P) → field-earned at this operating point;
transfers as Simmons Q4. White noise at relevant lags → FIELD-BLOCKED at this
operating point; **no estimator rescue** absent measurable temporal structure.

**Run first — T1's result conditions T2's interpretation.**

### T2 — decoder backlog slope (GRADIENT-CONSTITUTIVE; downstream of T1)

**Statistic:** same autocorrelation, on backlog slope. Syndrome arrivals inherit the
quantum pool's noise, so interpretation is conditional: T1 blocked & T2 blocked →
consistent inheritance. T1 blocked & T2 earned → independent classical structure
(service dynamics). T1 earned → decompose inherited vs. intrinsic structure before
crediting T2 independently.

**Boundary:** measuring slope autocorrelation is instrument-side observation. Wiring
backlog slope into any scheduler decision remains forbidden until the Register-3
coupling question returns from physics (parked note, 2026-07-05).

### T3 — lease-freshness rank inversion (GRADIENT-ORDERING)

**Statistic:** inversion rate between (a) order-by-current-fidelity and (b)
order-by-projected-fidelity-at-consumption, over co-pending lease sets at scheduling
decision points.

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
- **NOT licensed:** deadline-semantics rebuild, backlog-coupling model, duration
  separation — all still parked per the 2026-07-05 note. Naming the perishable-good
  abstraction is not decided by this battery.

## Dependency and run order

T1 → T2. T3 independent (cheap). S1 independent (config only). S2 after B1. T4 after
B2. The endgame question — is anything actionably predictable independent of the
heralding floor — decomposes cleanly: temporal half = T1/T2; spatial half = S2+B2
dose-response plus Simmons Q6. **A clean temporal FIELD-BLOCKED sweep is positive
evidence for the spatial hypothesis, not a global null.**

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
- Q1–Q3 (parked note, 2026-07-05) unchanged and still owed to Simmons.

## What this battery does not decide

The name of the perishable-good abstraction; cliff-vs-slope; the backlog coupling.
The three-register discipline of the parked note continues to apply.
