# rho_q mechanism result: the knob kept its contract — the arms were never blind

**Date:** 2026-08-04
**Prereg:** `2026-08-04-rho-q-mechanism-prereg.md` (frozen 9e4fdb5, rival
amendment e64d29c, both pre-read). **Instrument:** code read of the full
quality pipeline (`scripts/hedged_placement_stage1.py`,
`scripts/flattening_test_quality.py`) at HEAD, which carries the Stage-1
implementation unchanged for the quality path. No new statistics computed;
everything below is code trace plus the already-published numbers.

## Scoreboard — the house wins again

**P-M1 (analyst: linear blend of draws, marginal not preserved): FAILED.**
`mix3_pmf` (line 24) is a common-mode mixture of *distributions*, not a
blend of draws: `rho * common + (1-rho) * iid` over the 8-vector pmf, with
the common component putting mass p on 0b111 and 1-p on 0b000. Each site's
marginal is Bernoulli(p) at every rho. The docstring says
"preserving each site marginal" and the code does exactly that. rho_q's
invariance contract was honored by construction.

**P-M3 (Tony: experimental error, we'll fix it): FAILED as stated.** The
pipeline is correct end to end: the generator computes exact enumerations,
the CSV carries distinct per-arm columns, the analysis script
(`flattening_test_quality.py`) computes plain marginal ranges per arm with
no shared-column or aggregation defect. There is nothing to fix in the
code. (Partial credit in spirit, recorded honestly: something WAS wrong and
does need fixing — but it is a sentence in the 07-26 result doc, not a line
in the pipeline. See "Correction" below.)

**P-M2 (unclaimed: marginal-preserving + selection-side leak): NEAREST,
but its named mechanisms are also wrong.** The leak is not materialization
censoring and not q_min interplay.

## The actual mechanism: the anchor is chosen by looking

`evaluate_arms` line 221:

```python
b = anchor_table[v["Z0"]] if quality_pass else np.full(len(ehat), pi[0], ...)
```

In the quality pass, EVERY arm — single and prebound included — anchors on
`b = anchor_of_z0(Z0)`: the first site under pi whose bit of Z0 (the
initial quality forecast, a noisy observation of the true quality vector H
with accuracy a_0 = 0.60, fixed per the manifest) is maximal. The single
arm's delivered quality is `Q_HIGH if H[b] else Q_LOW` — and **b was chosen
by reading quality information**. Selecting the argmax of a noisy signal
concentrates H = 1 at the chosen site when sites are independent
(rho_q = 0) and confers no site-differential advantage when all sites share
one draw (rho_q = 1). The value of picking-the-best-looking-site depends on
the joint, and rho_q is the joint knob. That is the whole 0.030.

**Why the effect is IDENTICAL in single and prebound, to the last decimal:**
both arms propose the very same anchored site b. Prebound differs only by
(i) subtracting delta_clone — a constant shift, and main-effect range is
shift-invariant under the grid's factorial balance (no clamp bites:
Q_LOW − max delta_clone = 0.2 > 0); and (ii) requiring k_complete — a
condition on K, which is independent of (H, Z0), and conditioning on an
independent event cannot move the conditional mean of q. Constant shift
plus independent extra gate ⇒ exactly equal ranges. The identity that
looked like a bug's fingerprint (P-M3) or a shared marginal (P-M1) is the
structural signature of a shared *decision*.

**Why the survival channel's zeros were exact:** in the survival pass the
anchor is the constant pi[0] — no Z0 read — so one-site arms truly read
nothing there. The theorem's exact zeros were real; the quality pass
switched on a quality-reading decision inside every arm.

## Correction to 984f52e (supersedes its mechanism claim)

The 07-26 result doc concluded "in the authored model, rho_q is NOT
marginal-preserving." **That sentence is falsified by the code read.**
rho_q preserves every site marginal exactly. What was wrong was the P1
table's classification of the arms: "single (reads nothing)" is false in
the quality pass — single reads one Z0-derived bit through its anchor
choice. The blindness theorem did not break; blindness was misdeclared.
Flatness-is-blindness survives intact: the arm that moved with rho_q was,
in fact, looking.

## Design plank, refined (Chertov register)

The earned plank stands but sharpens. It is not enough for a knob to
declare its invariance contract (rho_q's was declared, honored, and STILL
surprised us). **The battery must also declare each decision's information
diet** — every signal a decision reads, including reads hidden inside
site-selection rules like argmax-of-forecast. A selection is a read of the
joint; a joint-knob therefore reaches every arm whose site was chosen by
looking, no matter how blind the arm's later gates are. The uninferability
lesson lands one step deeper: the profiler misattributed structure not
because a knob lied, but because an arm's diet was misdeclared.

## Follow-ups (each needs its own prereg; none run here)

- Quantitative decomposition: anchor-selection gain vs rho_q at a_0 sweep
  values (a_0 = 0.5 should extinguish the effect — the frozen-able
  prediction if anyone wants it).
- Re-audit the survival-channel prereg's arm classifications under the
  same information-diet rule.

## Correction to the P-M3 score (2026-10-09; supersedes "FAILED as stated")

The P-M3 verdict above scored the wrong text. Tony's frozen bet, verbatim
in the prereg, is: "My bet: this is an experimental error, and we'll figure
out what it was and fix it." The sentence that follows it in the prereg
("I.e. ... a defect somewhere in the experimental pipeline (generator
wiring, CSV production, or analysis script)") is the analyst's
operationalization, not Tony's words, and the verdict adjudicated that gloss.
Tony, the next session: "I don't recall saying I thought it was a code
error... I just wasn't willing to bet on anything that clean surviving
analysis."

Scored against his sentence, P-M3 is a **partial win**. Something was wrong
with the experiment: the arms' blindness was misdeclared in the 07-26 result
doc. It was found, and it was fixed (the correction to 984f52e above, plus
the information-diet rule). It is not a clean win because the pipeline code
was sound and the 0.030 is a real authored property of the model, not an
artifact. The paragraph above already gave "partial credit in spirit", but
it reached that by grading the gloss.

This correction was disclosed but held back in the 2026-09-30 consent reply
to the governance calibration study
(`docs/requests/2026-09-30-reply-to-governance-consent-request.md`, §1b).
It is committed now as an append, so the study can see both the original
score and this one.

Lesson recorded for future preregs: freeze a claimant's bet verbatim. Either
have the claimant own any operationalization before the read, or mark the
gloss as the adjudicator's and score both texts at result time.
