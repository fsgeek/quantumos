# Flattening-test result: structure is the signature of a decision that reads the axis

**Date:** 2026-07-26
**Prereg:** `2026-07-26-flattening-test-prereg.md` (commit 1d7eb6a, stamped
b10ff68), frozen before any outcome value was read.
**Instrument:** `scripts/flattening_test.py` (this commit); full JSON at
`runs/hedged-stage1/flattening_test.json` (local, per run-artifact convention).
**Data:** `runs/hedged-stage1/survival.csv`, exact deterministic enumeration —
no sampling error; all statements are about the authored model on its grid.

## Verdict: H-REDISTRIBUTE, both grids

Primary (all 1,620 cells): Var(late) = 0.03624 vs Var(prebound) = 0.03115 —
total structure went UP, not down, and late's main-effect range exceeds
prebound's by more than ε = 0.01 on three axes: rho_c_rho_l (+0.188),
q_k (+0.031), g (+0.017). Sensitivity (1,296 activated): same verdict,
same axes (+0.092, +0.036, +0.019). The analyst's two named candidate axes
(q_k, g) both exceeded; the DOMINANT axis (correlation structure) was named
by neither hypothesis.

H-FLATTEN as frozen (absolute variance, uniform per-axis) is REFUTED in this
model. See the post-hoc flag below before concluding the storage intuition
itself is dead.

## The finding under the verdict: flatness is blindness, exactly

The striking rows are exact zeros, not small numbers:

- prebound's marginal mean is 0.431424 at EVERY correlation structure
  (range 0.000000). An arm that commits before observing has delivery
  determined by the site marginals alone; correlation moves the joint, not
  the marginals. The flatness is a theorem, and the enumeration confirms it
  to six decimals.
- single's marginal mean is 0.463125 at EVERY q_k (range 0.000000). No key
  apparatus, no key exposure — the trivial case, as preregistered.

Meanwhile late binding — the correctly-sited layer — is the ONLY arm whose
outcomes carry the correlation axis (0.681 independent → 0.493 common-mode),
and it carries the key and wait-hazard axes more strongly than prebound
carries them, while being flatter on site/path availability (p_c, p_l, a_e).

So the layer does not absorb environmental structure and does not merely
shuffle it: **an environmental axis appears in an arm's outcome structure
precisely when that arm's decision reads it.** Late binding's selector reads
the realized joint (which sites survived together), so the joint's shape
surfaces in its outcomes. Prebound's non-decision reads nothing, so its
outcomes are flat — not because a layer protected it, but because blindness
is flat. Flatness in an outcome map is not robustness; it is the signature
of a decision that reads nothing there.

This is the object-model admission rule ("a represented quantity must name
the decision that reads it" — DECISION-EARNED) encountered empirically, from
the far side: the t3 degeneracy result (86% of rank decision points
degenerate → field not earned) is the same statement in the other
direction. Axes earn their place in outcomes through decisions; decisions
that read nothing leave no fingerprint. Q2/Q6's framing gains a corollary
worth carrying to §8's inferability story: adding a correctly-sited layer
does not simplify the hardware's visible physics — it CHANGES WHICH physics
the outcomes are sensitive to, from the axes beneath the layer to the axes
the layer's own decision reads.

## Post-hoc observation — FLAGGED, not a verdict, needs its own prereg

Late's mean delivery is far above the other arms' (≈0.60 vs 0.43/0.46, read
off the preregistered marginals). In RELATIVE terms (sd/mean, from the
already-computed variance and implied means): late ≈ 0.32, prebound ≈ 0.41,
single ≈ 0.39 — on that non-preregistered statistic, late is the FLATTEST
arm. The storage intuition may be correct in relative structure while wrong
in absolute: the layer lifts the floor faster than it widens the spread.
Per the prereg's own rule this is a new hypothesis, not a result; it gets
its own preregistration or it gets nothing.

## Scope and honesty

- Authored three-clone model, one frozen grid, survival channel only.
  Nothing here is a hardware claim.
- The prereg's H-REDISTRIBUTE succeeded on its named axes, but the analyst
  did not predict the dominant axis; the win is partial credit, recorded as
  such.
- The correlation-axis magnitude comparison (0.188 "dwarfs" the named axes)
  is a reading of preregistered statistics, but the ORDERING of axes was not
  itself preregistered.
