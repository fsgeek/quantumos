# Parked structure: the perishable-good lifecycle absence

**Date:** 2026-07-05 (session close, saturated tail — parked deliberately unfinished)
**Status:** STRUCTURE PARKED. The core abstraction is NOT named here. Naming it is the
highest-leverage act left and is deferred to a fresh instance + rested reader, on purpose.
Do not name it at the tail of a long recursive session — the abstraction is verified and
does not decay; it keeps.

This note is the durable artifact of a multi-instance wander (qsim exploration, 2026-07-05).
It is written in three registers so a later reader can tell what the instrument *verified*
from what only external physics (Simmons) can settle. Do not collapse the registers.

---

## Register 1 — VERIFIED, parameter-independent, in the code

The position paper's object model has **no first-class notion of the lifecycle and location
of a perishable good.** This absence surfaced four independent ways; they are four faces of
one missing abstraction, not four findings:

- **where it lives** — port/topology (the birth-map: Modules/Ports/Paths). Demanded ~3 ways
  earlier (S1 crash, inert pregen, uncalibrated-path guard).
- **when it is born vs demanded** — two deadline *anchors* genuinely in the code:
  `heralded_at` (birth) and `arrival_time` (demand), currently disguised as one clock by a
  single shared duration `deadline_slack_s`.
  - `round.deadline = arrival_time + deadline_slack_s`  (workload/generator.py:42)
  - `lease.freshness_bound_s = deadline_slack_s`, checked as `now - heralded_at <= bound`
    (engine.py:268, lease.py:83)
- **whether its death is observed** — freshness/fidelity observable was keyed to a
  success-only event class (blind on the failure side); fixed today via
  `fidelity_at_outcome` (cause-tagged at every terminal).
- **whether a good delivered after death is still itself** — `completed_late` (619 in the
  probe run) delivers and *consumes* a good past its deadline as a discounted success.

The four survive as **instances** of the one absence; naming the abstraction organizes them,
it does not dissolve them (tested: does-it-organize-or-dissolve — it organizes).

## Register 2 — CORRECTED (a fact the code currently gets wrong; do NOT record the code's version)

The code's deadline **hardnesses are inverted relative to the physics.** An earlier pass
read hardness off the code's *enforcement* and recorded it backwards; that reading is wrong.

- **Coherence death** is physically the **hard cliff** (*ser*): past coherence, the good is
  not a discounted good, it is noise — categorically fatal. The code implements it **soft**
  (fidelity folds into a continuous success probability, `engine.py:610`; never gates).
  This softness is a **bug/omission, not a property** — proven by the fact that the cliff
  *does* exist in the code exactly once, in S1 pregen eligibility (`pregen.py:85`,
  `age_s <= freshness_bound_s`). The codebase knows how to make coherence a cliff and
  declines to on the consumption path.
- **Schedule death** is physically the **survivable slope** (*estar*). The code enforces it
  **hard at admission** ("past deadline at admission time" defer) and **soft at completion**
  (`completed_late` succeeds + consumes). That is not "hard" — it is *inconsistently
  enforced*, and the inconsistency is what produces the immortal past-deadline zombie churn
  (a failed round retries against a frozen schedule-death deadline forever; 192 failed rounds
  → 87,072 deferrals in the probe; `retry_cap` bounds it but masks rather than fixes).
- Corrected-fix shape (do not build yet): coherence's cliff is enforceable **only at
  consumption** (hidden in flight — the herald is a birth certificate, not a heartbeat), so
  the fix is a **fidelity threshold at consumption** — a sub-threshold `completed_late` is a
  **drop** (noise booked as noise), not a discounted success.

## Register 3 — HYPOTHESIZED, pending Simmons, NOT committed

Committing to any of these now would smuggle disputed structure past the toll gate (the same
error as "separate the durations, no semantics committed" — separating one duration into two
*durations* commits to them being commensurable same-kind quantities, which is exactly the
disputed cliff-vs-slope question). So: parked, not built.

- coherence death is a true cliff (*ser*) — probable, unverified.
- schedule death is a latency-tolerant slope (*estar*) — depends on the SHYPS decoder window.
- the two clocks are **coupled, not parallel**: schedule-lateness burns decoder time →
  backlog → the next round holds longer → its coherence cliff arrives sooner. A slope that
  *manufactures cliffs downstream* ("read-wear with a hangover"). A duration-ratio sweep
  between independent clocks is structurally blind to this; representing it needs the backlog
  coupling *in the model* — a further concept the instrument is demanding and no one has named.

---

## The three Simmons questions this thread generated (Register-3 currency)

1. Is **coherence death** a true hard cliff — below some fidelity the pair is worse than
   useless (injects errors past QEC threshold), categorically not "the good"?
2. Does the **SHYPS decoder tolerate schedule-latency**, and how much? (Is schedule death a
   survivable slope with a real window, or a hard real-time cliff?)
3. Does **schedule-lateness feed coherence-death through decoder backlog** — does a late
   syndrome measurably push the next round's coherence deadline closer?

## Explicit next-instance instructions

- **Name the abstraction** (Register 1) — it is ripe, verified, parameter-independent. This
  is plausibly the section the position paper owes. Do it fresh, rested, against this note.
- **Leave the coupling** (Register 3) until the physics comes back. Do not model it yet.
- **Do NOT separate the durations** as an "instrument-neutral" change — it is not neutral.
- **Do NOT rebuild the deadline semantics** until cliff-vs-slope-and-coupling is decided.
- The wander delivered: it found the day's questions and the single abstraction beneath them.
  Stop pulling. Let it rest.
