# Design: field-battery analysis tooling

**Date:** 2026-07-07
**Status:** DESIGN — approved in session, pre-implementation.
**Prereg:** `docs/superpowers/specs/2026-07-06-field-battery-prereg.md`, stamped in
commit `06b0bd4feb0ca97d5b8f0245b8cbdf5bda10721d`. This tooling is instrument-side
and non-gating: it builds the analyses the prereg requires without touching engine,
policies, models, or trace semantics.
**Posture (Tony, 2026-07-07):** the battery is an exploratory instrument for
understanding which physics aspects matter to a quantum OS; swept values likely sit
outside real hardware bounds, and the deliverable is better questions. Prereg
discipline binds where it prevents self-deception (the blind open regime; the
write-then-look attribution order). Everywhere else, mechanical definitions in this
design are **disclosed conventions, not derived truths** — the full-fidelity record
always dominates any single windowed reading. Pre-run, pre-build amendment of the
prereg to close gaps identified while reasoning about the tooling is legitimate: it
injects no bias because nothing has been measured yet.

---

## 1. Layering and placement

Existing split, preserved: `qsim/observe/` owns trace→series reconstruction (views
reading `events.jsonl` from disk); nothing yet owns series→statistic→verdict.

- **New reconstructions** join `qsim/observe/` as ordinary views (same
  `events_path: Path` contract, streaming via `iter_events`, delta-derived with
  payload fields reserved as self-checks — the existing `pool_depth_series`
  convention).
- **New package `qsim/analysis/`** owns statistics, surrogates, attribution,
  artifacts, and verdict assembly. It consumes views; it never parses
  `events.jsonl` itself.
- Rejected: statistics inside `observe/` (verdict logic reads the prereg, not the
  trace); standalone scripts (untested instrument code).

Dependencies stay stdlib-only. All series arithmetic lives in one module
(`analysis/numerics.py`) so numpy can replace the internals later without touching
gate or verdict logic.

## 2. New observe views

| View | Reconstruction | Event basis |
|---|---|---|
| `pool_flux_series(path, bin_s)` | binned d(pool)/dt per (path, coherence) key, deltas only | `pool.deposited/withdrawn/expired` |
| `replenishment_latency_samples(path)` | replenish-issue → deposit latency samples | replenish-sourced lease lineage (`pool.deposited` with `source="replenish"` + its lease's request/herald events) |
| `inter_withdrawal_times(path)` | per-pool-key gaps between withdrawals | `pool.withdrawn` |
| `retry_cadence_samples(path)` | retry lineage cycle times | `round.arrived` (`retry_ordinal`), `round.retried` |
| `backlog_slope_series(path, bin_s)` | binned slope of decoder backlog | existing `decoder_backlog_series` |
| `t3_decision_points(path)` | co-pending lease sets at scheduling decision points, with per-lease (current fidelity, projected fidelity at consumption) | lease lifecycle events; episodes segmented by envelope `seq` because lease_ids recur across retries (feasibility CONFIRMED in prereg) |

Exact payload-field bindings are verified test-first at implementation; the trace
is the sole source of truth.

## 3. `qsim/analysis/` modules

- **`numerics.py`** — ACF, white-noise band `1.96/√n_bins`, binning. Pure stdlib
  functions; the numpy-swap seam. Nothing else does series arithmetic.
- **`surrogates.py`** — permutation surrogate band: 1000 shuffles of the binned
  series via `random.Random(seed)` (seed recorded in the artifact); band = per-lag
  2.5/97.5 percentiles of surrogate ACF. Permutation, never phase randomization
  (prereg: phase randomization preserves the ACF by construction).
- **`attribution.py`** — predicted-lag derivation per named mechanism cycle.
  T1: replenishment cycle (from the latency distribution — measured from events
  that are not the ACF); low-water oscillation (per-pool mean inter-withdrawal
  time × L); retry cadence where retries are active. T2: decoder service time
  (1/rate); M/M/1 busy-period relaxation at the operating point's utilization.
  Assignment tolerance: one bin.
- **`artifacts.py`** — the write-once gate and report writer (§4, §9).
- **`t1.py`, `t2.py`, `t3.py`** — verdict assembly per prereg criteria.
- **CLI:** `quantumos analyze t1|t2|t3 <run_dir> [...]` and `quantumos sweep s1`.

## 4. T1/T2 pipeline (strict order)

1. **Steady-state gate.** If the run header's `steady_state` verdict failed, the
   analysis records TRANSIENT and withholds any verdict. A transient is not read.
2. **Lag window.** Measure the replenishment-latency distribution from non-ACF
   events; window = bins covering its central mass (§5). Control bin 0.1 s per
   prereg; open regime bins by the same rule on its measured latency.
3. **Predicted lags (write-then-look).** Derive predicted lags for every named
   cycle and write `analysis/predicted_lags.json` **write-once**: if the file
   exists it is reused verbatim, never rewritten. Re-running can never re-derive
   predictions after the ACF has been seen; deleting the file leaves a hole the
   git/OTS discipline makes visible.
4. **Statistics.** Compute the ACF at **all estimable lags** — lags 1 through
   ⌊n_bins/4⌋, the standard reliability bound for the ACF estimator — with the
   white-noise band and the permutation-surrogate band. The full curve is always
   the artifact; the window is an annotation over it.
5. **Attribution.** Assign significant in-window lags to predicted cycles within
   one bin.
6. **Report.** Emit `analysis/t1_report.json` embedding: sha256 of
   `predicted_lags.json`, full operating point + policy from the header, `git_sha`
   plus a stamped-commit ancestry check (§9), every criterion component,
   window-sensitivity disclosure (§5), and the verdict.

T2 runs identical machinery on `backlog_slope_series` with its own named cycles.
Its report carries the prereg's inheritance-conditional note verbatim: recorded,
not interpreted against the inheritance question, until T1 runs.

## 5. Lag window — disclosed convention

Window = bins covering **[p25, p75] of the measured replenishment-latency
distribution, minimum width 3 bins, minimum lag 1**.

Reasoning, on the record: the window is a support-coverage question, not a
confidence interval — a pregen action issued now completes after a latency drawn
from the whole distribution, so structure at any lag with appreciable latency mass
is exploitable. A median-sliver window (e.g. [p49, p51]) treats latency as a
constant and would systematically miss exploitable lags when contention spreads
the distribution (open regime); a very wide window inflates the multiple-comparison
false-positive budget (pointwise 95% band ⇒ expected false exceedances ≈ 0.05 ×
window size, reported alongside the verdict). The 3-bin floor exists because a
one-bin window hinges on bin phase alignment — a reconstruction artifact, not
physics. 50% coverage is a convention; the report therefore also states the
significant-lag set under [p10, p90] so any window-dependence of the reading is
visible on its face.

## 6. Verdict logic

Tool computes and prints the verdict; every component is in the JSON artifact so
the arithmetic is auditable. The human owns interpretation and transfer.

- **T1 control PASS** iff every tracked pool shows |ACF| exceeding the white-noise
  band at ≥1 in-window lag, sign consistent with the low-water replenishment cycle
  (negative near one replenishment latency), and the structure survives the
  surrogate test (observed |ACF| outside the surrogate 95% band at those lags).
  Anything less → **T1 INSENSITIVE**; the report states in bold: do not run the
  open regime.
- **T1 open:** significant in-window structure with every significant lag
  attributed → **FIELD-EARNED** (report carries the attribution-before-transfer
  caveat verbatim). Any significant lag no named cycle predicts →
  **ATTRIBUTION-FAILED**: transfer blocked, mandatory adversarial mechanism probe
  (the 75206ce playbook). No significant in-window structure → **FIELD-BLOCKED**,
  finalized only with the knob-motion companion (§7).
- **T2:** same criteria on backlog slope; verdict recorded with the inheritance
  condition attached.
- **T3** (four-outcome space per prereg): nondegenerate set = ≥2 co-pending
  leases. **INVERSIONS FREQUENT** iff >10% of nondegenerate decision points show
  ≥1 pairwise inversion between order-by-current-fidelity and
  order-by-projected-fidelity (`exp(−rate_class·(t_consume − heralded_at))`,
  analytic from trace, projected never observed) AND median projected retention
  delta across inverted pairs > 0.01. (a) fails → INVERSIONS RARE. (a) passes,
  (b) fails → frequent-but-immaterial, demotion stands. Degenerate-dominated →
  NON-FIELD at this operating point, retest under higher concurrency.

## 7. Knob-motion companion — always run

The T1-open protocol is **two runs**: the stamped primary
(`examples/t1-open.toml`) plus a companion identical except
`arrival_rate_hz = 0.5` — the knob the prereg itself names for the knob-motion
check. `analyze t1` takes both run dirs and emits one verdict; no PROVISIONAL
state exists. Rationale: the companion is informative even when the primary shows
structure (a two-point dose-response of pool dynamics on load — exploratory value),
and the honesty mechanism and the exploration mechanism become the same run.
The knob-motion comparison itself emits statistics only (depth/flux summaries side
by side) — the prereg pins no threshold for "visibly moved," so no verdict word
attaches to it; a flat primary with a flat comparison is reported as
FIELD-BLOCKED-with-caveat, quoting the flat-sweep lesson.

**Amendment note:** the companion config differs from the stamped primary only in
the prereg's own named knob-motion knob, so this reads as within the stamped text.
If preferred, a one-paragraph prereg amendment recording the two-run protocol can
be stamped before the T1 runs — legitimate pre-run gap-closing (posture note above).

## 8. S1 sweep runner

`qsim/experiments/sweep.py`, minimal and battery-specific (no generic framework —
grid-sweep stays M1 work): builds the four pinned configs (δ ∈ {0, 0.1, 0.2, 0.4}
heralding_p spread across the four-path fabric at fixed p̄ = 0.7, otherwise T1-open
physics), runs each through the existing single-run driver, and writes a sweep
manifest (δ → run_id → config hash) plus a dose-response table of deadline
compliance and fidelity-at-outcome per δ from existing views. δ=0 is asserted as
the homogeneity anchor: any effect there is flagged as a bug, not a curve.
Non-monotonicity is reported, not failed (prereg: it triggers a mechanism audit
under the attribution rule).

## 9. Artifacts and provenance

Each analyzed run gains `<run_dir>/analysis/`:

- `predicted_lags.json` — write-once (§4 step 3).
- `<test>_report.json` — full ACF curve + both bands, window + sensitivity
  disclosure, criterion components, verdict, operating point + policy, surrogate
  seed, sha256 of `predicted_lags.json`, `git_sha`, and an ancestry check:
  whether the run's `git_sha` is a descendant of the stamped commit
  (`git merge-base --is-ancestor`, best-effort, recorded either way) —
  operationalizing the prereg's forward-provability rule.
- Sweep runs additionally get a sweep-level manifest + dose-response artifact.

Stdout gets a human-readable summary; the JSON artifact is the record.

## 10. Error handling — refusals are data

Empty/missing series → "insufficient data," no verdict. Undefined lag window (no
replenishment samples) → hard error with explanation. Steady-state failure →
TRANSIENT, verdict withheld. Write-once collision → reuse, noted in report. Every
refusal is recorded in the report artifact, not just stderr.

## 11. Testing

TDD throughout. Unit: numerics against synthetic ground truths (white noise inside
band ~95% of lags; alternating series → known negative lag-1; period-k series →
peak at lag k); surrogate determinism (same seed → identical band); write-once
semantics; attribution tolerance (planted lags inside/outside one bin); T3 on
hand-built traces with known inversion counts and known projected deltas.
Integration gate (existing style, full-taxonomy lesson applied to the consumer
side): one real short-horizon S1-with-pool run piped through the complete
`analyze t1` pipeline, asserting the artifact chain (predictions file, hash embed,
report) and that every event type the pipeline consumes occurs in the gate run.

## 12. Out of scope

T4 tooling (blocked on B2, which is blocked on Q7/Q8); any scheduler/engine/model
change; plotting; generic sweep framework; the perishable-good naming (parked).
