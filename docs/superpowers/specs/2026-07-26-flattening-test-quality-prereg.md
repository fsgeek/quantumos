# Flattening test, quality channel: does the relative-flatness rescue generalize, and does the blindness theorem?

**Date:** 2026-07-26
**Status:** PREREGISTERED, not yet computed. The survival-channel test
(prereg 1d7eb6a, result ce5f439) is settled and BURNED for the relative
statistic — the analyst read the CV values while flagging them post-hoc.
The quality channel is the last blind data in this run for these questions.
**Register:** practice-grade per standing qsim discipline.

## Frozen questions

Two hypotheses from the survival-channel result, each with a named owner:

**P1 — blindness theorem generalizes (analyst).** An arm's outcome map is
EXACTLY flat (main-effect range = 0 up to numerical tolerance 1e-9) on every
axis its decision does not read, and structured (range > ε) on axes it does:

| arm | rho_q | a_1 | delta_clone |
|---|---|---|---|
| single (reads nothing) | exact-flat | exact-flat | exact-flat |
| prebound (commits blind; pays clone penalty) | exact-flat | exact-flat | structured |
| late (selector reads the late signal over the spread) | structured | structured | structured |

a_e is left unspecified for all arms (no mechanism story frozen for it).

**P2 — relative-flatness rescue (Tony's storage intuition, surviving form).**
On the survival channel, late was flattest in sd/mean terms (≈0.32 vs
0.41/0.39; post-hoc there, hence this test). If the rescue is a general
property of a correctly-sited layer, CV(late) < CV(prebound) − ε_cv AND
CV(late) < CV(single) − ε_cv on the quality channel too.

**P2-rival (analyst).** The rescue does NOT generalize: CV(late) >
CV(single) + ε_cv, because single is blind to every quality axis and
blindness is flatness in both denominators — a blind arm's CV collapses
toward zero and a seeing arm cannot beat it. (If P1 holds for single on all
four axes, Var(single) ≈ 0 and this follows almost mechanically; the run
note gives no information either way about single's a_e sensitivity, which
is the one escape hatch.)

Analyst's overall lean, stated for the record: P1 holds in full; P2 fails,
P2-rival holds. A P1 failure would be the bigger surprise and the more
valuable one — it would mean the survival-channel zeros were an artifact of
that channel's structure, not a theorem about decisions.

## Data and definitions (frozen)

`runs/hedged-stage1/quality.csv`, 540 cells; quality axes a_1, a_e,
delta_clone, rho_q (others fixed per manifest). Same immutable Stage-1
artifacts (implementation 5b8a936, prereg ca26217).

- **Outcome variable:** `{arm}.q_mean_given_materialized` for arm in
  {late, prebound, single}.
- **Statistics** (the only ones licensed): per-arm mean, population
  variance, CV = sd/mean, and per-axis main-effect range (max − min of
  marginal means over the axis's levels), on primary = all 540 cells and
  sensitivity = the activated 270.
- **Margins:** exact-flat: range < 1e-9. Structured: range > ε = 0.005
  (quality effects live at the 0.01–0.12 scale per the run note, so half
  the smallest reported effect). CV comparisons: ε_cv = 0.005.

## Exposure disclosure

Read before this prereg: the Stage-1 run note's quality paragraphs (V_Q
extrema +0.0100 to +0.120 and their locations; refusal boundaries — 180
cells at rho_q = 1, 90 at a_1 = 0.5; the shared-penalty invariance clause
"delta_clone moves absolute plural quality, never selection"); CSV headers;
manifest grid structure. That invariance clause is the source of P1's
prebound/delta_clone = structured entry. NOT read: any q_mean value, any
quality aggregate, any row of quality.csv.

## Procedure

1. Commit this document (hook stamps).
2. `scripts/flattening_test_quality.py` computes exactly the statistics
   above. 3. Run once; record verdicts for P1 (per-cell of the table) and
   P2 vs P2-rival; results note; anything further is a new prereg.
