# Pre-open-run decisions: attribution scope + numerics backend

**Date:** 2026-07-09
**Status:** Recorded BEFORE any T1-open run exists (T1 control: PASS, run
`f230668e`, git `264b684`, same day). Pre-run commitment per the prereg's
write-then-look discipline: analysis scope is part of the prediction surface.

## Decision 1 — attribution scope (prereg clarification)

**The gap:** the prereg's attribution amendment says FIELD-EARNED requires
"every significant ACF lag" to be assignable to a named cycle. At pointwise
95% bands over all estimable lags (~n_bins/4, i.e. hundreds), ~0.05×max_lag
false exceedances are expected — a verbatim reading makes ATTRIBUTION-FAILED
near-certain and the criterion vacuous. The prereg's own significance concept
is window-scoped throughout (statistic "at pregen-relevant lags"; pass
criteria "in the window").

**The decision (implemented in commit 57fc2fa):**
- Verdict PRESENCE (FIELD-EARNED vs FIELD-BLOCKED) gates on the primary
  [p25, p75] latency window (unchanged).
- Verdict ATTRIBUTION gates on the wider [p10, p90] sensitivity window —
  unattributed significant structure anywhere in the plausible latency
  support forces ATTRIBUTION-FAILED.
- The FULL curve's unattributed significant lags are always DISCLOSED in the
  report artifact, non-gating, alongside the expected-false-exceedance
  arithmetic. Nothing is hidden; the gate simply operates where the
  statistics are well-posed.
- Recorded in every report at `conventions.attribution_scope`.

**Asymmetric-loss note:** a false FIELD-EARNED corrupts (false confidence
propagates toward the position paper); a false ATTRIBUTION-FAILED merely
costs a mechanism probe. The residual load therefore lands on the human
reading the full-curve disclosure before any transfer. PENDING (next
session): append one sentence to the FIELD-EARNED caveat string making this
explicit — "the verdict word alone is not transferable; read the full-curve
disclosure first."

**Authority:** presented to Tony 2026-07-09 with the reasoning above; not
vetoed. The veto window closes when the first T1-open ACF is computed — a
scope ruling made after seeing open data is contaminated regardless of its
merits.

## Decision 2 — numerics backend: numpy (and only numpy)

**The problem:** T1-open analysis is ~10^11 multiply-adds (bin rule adapts to
the open config's 0.01 s reconfig → 4k–20k bins; 1000 surrogate shuffles are
prereg-pinned, not a knob). Measured pure-Python throughput puts that at
1–20 h; the control's ~3 min is fine.

**The decision:** swap `qsim/analysis/numerics.py` internals to numpy — the
seam the design cut for exactly this, by name. Sizing against alternatives:
the workload is once-per-analysis, CPU, no gradients, no iteration — JAX
(autodiff/XLA), CuPy (GPU), and Numba (LLVM JIT of the naive loop) each buy
capability this problem cannot use, at the price of install fragility,
float-semantics variance, and version drift a research instrument pays for
in trust. Numpy is the least-novel numerical dependency in existence and
executes a decision a past instance already recorded in the module docstring.

**Implementation contract (next session):**
1. Direct correlation (`np.correlate`), NOT FFT — numerically closest to the
   pure-Python loops that produced the control PASS.
2. Hoist shuffle-invariant mean/denominator out of the surrogate loop.
3. Keep the pure-Python implementations as reference; cross-validation test
   asserts numpy path agrees to ~1e-12 on random series.
4. **Calibration bridge:** re-run the control analysis post-swap; assert the
   verdict and per-pool ACF values reproduce; record both artifacts. The
   instrument change between control and open runs is thereby measured, not
   assumed.
5. Benchmark one open-scale synthetic series and record the actual wall
   time (the 1–20 h estimate had 20× variance; the next instance inherits a
   fact, not a range).

**Authority:** internal implementation choice behind a designed seam —
Claude's decision, recorded here for provenance, endorsed in discussion
2026-07-09.

## Sequencing

Next session, fresh instance: (1) numpy swap + bridge + benchmark; (2) the
caveat-sentence addition; (3) T1-open + companion runs (blind, stamped
configs verbatim); (4) `analyze t1 --mode open`. The S1 sweep's δ=0.4
amendment (→ δ=0.3) remains recommended and unstamped; the sweep runner
records the infeasible arm as a refusal either way.
