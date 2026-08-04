# rho_q mechanism prereg: how does the knob leak into arms that cannot see it?

**Date:** 2026-08-04
**Status:** PREREGISTERED, generator source unread. This is the follow-up the
quality-channel result (prereg ab44285, result 984f52e) explicitly deferred:
"Follow-up needs its own prereg or a direct code read of the quality
generator." This document freezes a mechanism prediction BEFORE that code
read. **Register:** practice-grade per standing qsim discipline.
**Adjudication instrument:** a read of the quality-generation code in
`scripts/hedged_placement_stage1.py` (implementation commit 5b8a936; if HEAD
has drifted from 5b8a936 in the quality generator, read the 5b8a936 version
and note the drift). No new statistics are licensed; the verdict is purely
"which mechanism does the authored code implement."

## The anomaly being explained (already public in 984f52e)

rho_q, predicted exact-flat for both blind arms under the blindness theorem,
moved `q_mean_given_materialized` with main-effect range 0.030 in BOTH
single and prebound — IDENTICAL in the two arms (0.015 in the activated
subset, again identical). The result doc named two candidate mechanisms
without adjudicating:

- **(a)** the marginal quality distribution shifts with the
  common/idiosyncratic mix (rho_q is not marginal-preserving by
  construction);
- **(b)** selection through the materialization / q_min conditioning
  (rho_q changes which cells/sites survive into the conditional mean).

## Frozen prediction — P-M1 (this thread, "the analyst" seat)

**The generator implements mechanism (a):** per-site quality is authored as
an explicit convex/linear mixture of a common component and an idiosyncratic
component with weights linear in rho_q (schematically
`q_site = f(rho_q)·C + g(rho_q)·E_site` with f, g linear and f + g = 1, or
an equivalent linear-blend construction) — **not** variance-preserving
weights (`sqrt(rho)`, `sqrt(1−rho)` on symmetric components) and **not** a
copula with pinned marginals. A convex blend of independent draws shrinks
the per-site marginal's spread as the weights move off the corners, so the
marginal — and therefore its mean after the q ≥ q_min conditioning — depends
on rho_q at every site identically, and every arm inherits it no matter what
its decision reads.

**Why this and not (b), frozen for the record:** the effect is IDENTICAL in
single and prebound on both the primary and activated sets. Those arms have
different decision structures and different materialization exposure (the
prebound arm carries the clone penalty; the run note's shared-penalty clause
says delta_clone moves absolute plural quality, never selection). A
selection-side mechanism (b) flows through arm-specific materialization and
should fingerprint the arms differently, at least at the fourth decimal. A
shared upstream marginal consumed by both arms produces exact identity for
free. Identity is the tell.

**P-M1a (secondary, severable, lower confidence):** the rho_q dependence of
the blind-arm conditional mean is monotone across the swept levels, with the
largest marginal difference adjacent to rho_q = 1 (the level where the run
note already records a refusal boundary: 180 refused cells at rho_q = 1).
P-M1a can lose while P-M1 wins; they adjudicate separately.

**Named rival — P-M2 (default owner: the result doc's candidate (b); Tony
may claim or replace this rival in his next message before the read, and his
version then supersedes this paragraph):** the mixture/copula preserves the
per-site marginal, and the 0.030 enters through rho_q-dependent selection —
materialization probability, q_min interplay, or refusal-boundary censoring
— that happens to act identically on both blind arms.

## Exposure disclosure

Read before this prereg: result docs 2026-07-26 (both channels), prereg
ab44285, the Stage-1 exposure notes quoted therein (V_Q extrema, refusal
boundaries, shared-penalty clause), memory-store summaries of both
flattening tests, `flattening_test_quality.py`'s role as CSV reader (not its
source). NOT read: `hedged_placement_stage1.py` (any version), any row of
quality.csv, any quality aggregate beyond those published in 984f52e.

## Procedure

1. Commit this document (hook stamps).
2. One conversational turn is left open for Tony to claim/replace the rival
   prediction. His silence leaves P-M2 as written; nothing blocks on him.
3. Read the quality generator; write a result note naming the winning
   mechanism (or "neither — third thing," which both flattening tests teach
   us to expect); anything beyond the code-read verdict is a new prereg.
