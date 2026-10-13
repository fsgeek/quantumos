# quantumos §8 check: calibration-study analysis plan (r2)

**From:** the instance that currently owns `quantumos` (Opus 5.5), via Tony.
**Date:** 2026-10-13.
**Re:** `governance/docs/superpowers/specs/2026-09-30-calibration-study-analysis-plan-DRAFT.md`
§8 ("quantumos: bettor attribution; the P-M3 handling; practice-grade register").
**Verdict:** no withdrawal. Three changes are requested before freeze. Each one changes how quantumos
rows get coded.

I checked the plan against the harness output (`extract.py`, run 2026-10-13: seven quantumos
candidates) and against the frozen files themselves. I didn't read outcomes beyond what the P-M3
record already says about itself.

## 1. Register: the plan narrows Tony's words (requested change)

The codebook says `practice-grade` covers "quantumos qsim field-battery era, per Tony 2026-07-09".
Tony's words apply to the instrument, not to an era: "this is a broad sweep tool constructing an
almost assuredly wrong model of what a real simulator will look like... the discipline will be
beneficial when we have enough understanding to build a second simulator — the one where we'd be
worrying about rigorous predictions."

All seven harness candidates are qsim preregistrations or run notes. Six of them are dated after
07-09. Under a reading keyed to era, only `2026-07-06-field-battery-prereg.md` is practice-grade, and
the other six would be coded `load-bearing`. That is the opposite of what Tony said. The second
simulator was never built, so no quantumos bet is load-bearing.

**Request:** code `register: practice-grade` for every quantumos qsim bet, keyed by instrument. Note
that the field-battery prereg (07-06) was written before the statement (07-09), so a coder can see
that the register was declared afterwards, about the tool.

## 2. Bettor attribution: two more PI-attributed hypotheses, same gloss risk as P-M3 (requested change)

The plan names only P-M3 as Tony's. Two more hypotheses in the candidates carry his name, and in both
cases the text was written by the analyst, not by Tony:

- `2026-07-26-flattening-test-prereg.md`: **H-FLATTEN "(Tony's intuition)"**. The inequality is the
  analyst's operationalization of an intuition from an earlier document. Tony's *own* recorded stake
  in that prereg is different: he "expects a surprise to be waiting for the analyst" (lines 16–18),
  "recorded here as his stake in the outcome, prior to computation."
- `2026-07-26-flattening-test-quality-prereg.md`: **P2 "(Tony's storage intuition, surviving
  form)"**. The analyst formed it from a post-hoc observation.

P-M3 is the documented case of this exact failure: a score adjudicated against the analyst's gloss
instead of Tony's bet. These two have the same structure.

**Request:** a third bettor value, or a flag on `PI`: `PI-attributed, analyst-operationalized`. Rows
with this value are excluded from Q1 as PI rows already are. They must also never be reported as the
PI's forecast record in any table or prose. Where the record holds Tony's verbatim stake (the
flattening test's "expects a surprise"), code that stake as the PI bet, separately. The analyst's
named rivals in the same files (H-REDISTRIBUTE, P2-rival, and the "overall lean") are `AI` bets.

## 3. P-M3: the correction is now committed. Code its timing honestly (requested change)

Since the 09-30 consent reply, the correction has gone into the record. It is appended to
`2026-08-04-rho-q-mechanism-result.md` in commit `d45de75` (2026-10-09, OTS-stamped), with the
original "FAILED as stated" left in place. The plan's `record_scoring_error` field now applies
exactly as written. Two coding notes:

- **Q3 latency.** In the committed record, the correction lands at 10-09. Detection happened the
  next session after 08-04: Tony's "I don't recall saying I thought it was a code error". That
  detection is recorded only in memory and session transcripts, both of which the study excludes.
  Measured from the public record alone, the latency is about 66 days. The true detection latency
  was about one day. Report it as `as_recorded` and say so. Don't infer a slow catch.
- **Reactivity.** The correction was committed after the study's consent request, and the consent
  reply disclosed that it was being held back so the study could see the edit. Flag it
  `correction_after_study_contact`. It is a real catch, but the timing of its commit is not
  independent of the study.

`caught_by` for P-M3: `human PI question`.

## 4. Smaller items (no change needed, noted for coders)

- The field-battery prereg's freeze is `stamped: False` in the harness. The plan's
  `unstamped_hook_gap` coding covers it.
- Tale F1 is correctly excluded from Q1 as `prereg_unverifiable`.
- Naming per §7 is fine. Quantumos stones were signed in public.
