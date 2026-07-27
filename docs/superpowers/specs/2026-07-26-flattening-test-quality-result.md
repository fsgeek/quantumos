# Quality-channel flattening result: the theorem holds where it's a theorem, and rho_q is not the knob it looks like

**Date:** 2026-07-26
**Prereg:** `2026-07-26-flattening-test-quality-prereg.md` (commit ab44285,
stamped b82dd21), frozen blind. **Instrument:**
`scripts/flattening_test_quality.py`; JSON at
`runs/hedged-stage1/flattening_test_quality.json` (local).
**Data:** quality.csv, 540 cells (sensitivity: 270 activated); exact
enumeration, no p-values.

## Scoreboard — one loss each

**P1 (analyst's blindness-theorem generalization): FAILED as frozen.**
Seven of nine predicted cells held, including four EXACT zeros
(single/a_1, single/delta_clone, prebound/a_1 at 0.0e+00; prebound/a_e at
1e-16 descriptively). Both failures are the same cell pair: single/rho_q
and prebound/rho_q, predicted exact-flat, measured range 0.030 — and
IDENTICAL for both blind arms (0.015 in the activated set, again identical).

**P2 (Tony's relative-flatness rescue): FAILED. P2-rival: CONFIRMED.**
CV(late) = 0.167, CV(prebound) = 0.160, CV(single) = 0.0199. The blind arm
is ~8× flatter in relative terms; the rescue does not generalize to the
quality currency. On this channel blindness is flatness in both
denominators, as the rival predicted.

## The third thing: rho_q leaks into arms that cannot see it

The P1 failure is informative, not noise. If rho_q were a pure correlation
knob (copula-only, marginal-preserving), a one-site arm's delivered quality
could not move with it — that flatness would be the same marginal-invariance
theorem that held exactly on the survival channel's correlation axis. It
moved, by the same amount in both blind arms. So in the authored model,
rho_q is NOT marginal-preserving: it changes something that flows through
every arm's delivered quality (candidate mechanisms — marginal quality
distribution shifting with the common/idiosyncratic mix, or selection
through the materialization/q_min conditioning — are NOT adjudicated here;
either requires statistics this prereg did not license. Follow-up needs its
own prereg or a direct code read of the quality generator.)

Design plank earned for the second simulator (Chertov register): **every
knob must declare its invariance contract** — what it holds fixed while it
varies what it varies — and the battery must test the declaration. rho_q
looked like "correlation only" from its name and broke that reading under
a preregistered exactness test. A parameter surface whose knobs leak is
uninferable one level up: the profiler attributes structure to the wrong
axis.

## Descriptive readings (licensed statistics only)

- delta_clone's main-effect range is EXACTLY 0.200 in both plural arms —
  the clone penalty passes through to delivered quality at coefficient 1,
  and identically across arms, confirming the run note's shared-penalty
  invariance from a second direction.
- late is the only arm carrying a_1 (0.041) and a_e (0.006 primary / 0.012
  activated) — the selector's information axes fingerprint only the arm
  whose decision reads them. The theorem's spirit survives its formal loss.
- Mean delivered quality INVERTS the survival result: single 0.615 > late
  0.526 > prebound 0.515. The layer delivers MORE OFTEN (survival channel)
  at LOWER conditional quality (clone tax). The custody trade in one line:
  the option's price is paid in the quality currency, its payoff collected
  in the delivery currency.

## Standing after two channels

The layer neither absorbs nor uniformly redistributes structure; it couples
outcomes to the axes its decision reads, in whatever currency that decision
spends. Exact flatness marks either a decision that reads nothing there or
a knob that truly preserves the relevant marginal — and distinguishing
those two from flat data alone is impossible, which is the inferability
lesson §8 should carry: an OS that never spends a decision reading axis X
cannot infer X, and a flat outcome map never tells you whether X is absent
or merely unread.
