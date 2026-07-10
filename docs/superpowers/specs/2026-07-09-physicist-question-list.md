# The physicist questions (instrument-earned, threshold-framed)

*(Retitled 2026-07-10: the spatial battery earned a sixth question and
sharpened Q4 — see the dated amendments below and the S1 run note.)*

**Date:** 2026-07-09
**Status:** Drafted after the first open-regime battery results (T1
FIELD-EARNED 11b5de8, T2 STRUCTURE-ATTRIBUTED / T3 NON-FIELD 6dd1260).
Externally sanity-checked same day (Perplexity survey): all five are open —
none has a published, OS-usable answer for Photonic-style silicon
spin–photon architectures. Citations from that survey are NOT yet
verified; verify before any appears in print.

**Framing rule (decided 2026-07-09):** each request is phrased as a
THRESHOLD, not a constant and not an open-ended distribution. Every
represented quantity must name the decision that reads it (the admission
rule); the threshold is the value at which that decision flips, so the
experimentalist knows exactly when their answer is good enough to stop
measuring. Constants would calibrate us to one vendor's current device;
open-ended distributions invite characterization work nobody will
prioritize. Thresholds are the minimum-sufficient ask.

---

## Q1 — Switch reconfiguration cadence: spectral line or heavy tail?

**Ask:** the reconfiguration/replenishment cadence of the photonic switch
fabric, and whether its variance is small relative to the cadence itself.

**Threshold that flips a decision:** coefficient of variation of the
reconfig interval. Narrow (quasi-deterministic) → the OS sees a spectral
line it can schedule around, and the field is representable as a period.
Heavy-tailed → the field must carry a distribution, and phase-locked
scheduling strategies are off the table.

**Instrument grounding:** T1 control AND de-rigged open both show the
replenishment cycle imprinting on pool dynamics at exactly its own
timescale (lag-1 ACF, 5–9× the null band, attributed, surrogate-surviving).
The coupling mechanism survives de-rigging; it is not an artifact of model
wiring. This is the highest-priority measurement.

## Q2 — Instantaneous fidelity spread across coexisting pairs

**Ask:** the distribution of pair fidelities across simultaneously
available paths AT ONE INSTANT (not averaged over time), and the dominant
source of the spread (path asymmetry, calibration drift, heralding
statistics).

**Threshold that flips a decision:** is the instantaneous spread larger
than the scheduler's decision resolution? If not, fidelity-ranked
scheduling is machinery without a purpose and the OS should not carry it
(admission rule: the quantity's reading decision would read nothing).
If yes, the spread's SOURCE becomes an OS-visible field.

**Instrument grounding:** T3 NON-FIELD-AT-OPERATING-POINT — 86% of 382
rank decision points degenerate at our modeled decay rates and
concurrency. The instrument cannot see the ranking mechanism at operating
points where spreads are tight; hardware data decides whether such
operating points are the norm or the exception.

## Q3 — Memory read-out wear: rate or cliff, and ε per QND readout

**Ask:** whether repeated (QND) readout degrades the stored state
gradually or fails discretely, and the approximate per-readout fidelity
cost ε.

**Threshold that flips a decision:** N_reads = (fidelity headroom)/ε vs
the number of reads a lease lifecycle actually performs. Destructive read
(or N_reads ≈ 1) → lease accounting is binary. ε small enough for many
reads → leases carry a wear budget, a qualitatively different object
model.

**Instrument grounding:** the QND reframe (2nd instrument-forced finding):
the wear knob is a rate, not a cliff, IF the physics cooperates — the
model branch is built and waiting on one scalar.

## Q4 — Cost of a failed heralding attempt

**Ask:** after a heralding failure, is the slot/port blocked, for how
long, and is any resource destroyed? How fast can a retry be issued?

**Threshold that flips a decision:** retry cost relative to the aging
rate of everything waiting behind it. Cheap-and-fast retries at high
failure rates → the OS MUST ration retries (S0's unbounded-retry
congestion-aging spiral is self-defeating: retries age the very leases
they are trying to serve). Expensive/blocking retries → admission control
dominates and retry discipline is secondary.

**Instrument grounding:** the first RUN finding (retry spiral) plus the
retry cadence (0.68 s) entering T1-open's prediction surface as a named
cycle. Retry discipline is a load-bearing de-rigging knob; its real cost
is invented in the model and must come from hardware.

**Sharpened by the spatial battery (added 2026-07-10):** the same quantity
carries a second decision. The attempt price relative to deadline slack
decides whether path-quality awareness can matter in OUTCOMES at all:
under retry-with-reassignment, per-path heterogeneity averages out of the
outcome column at first order, and only an attempt price comparable to
slack lets a poor path cost anything a deadline can see (S1: outcome-flat
across three orders of magnitude of operating point; mechanism
code-confirmed; run note 2026-07-10).

## Q5 — Port-level topology envelope

**Ask:** simultaneous entangling links per memory module, switch radix,
and the granularity of reconfiguration (per-port? per-bank? global?).

**Threshold that flips a decision:** links-per-module = 1 vs > 1 changes
whether replenishment and consumption can overlap at all; reconfig
granularity determines whether one reconfiguration stalls one path or the
fabric. These bound the entire resource model.

**Instrument grounding:** demanded three independent ways before the
battery ever ran (S1 crash, inert pregen, uncalibrated-path guard) — the
instrument could not be built coherently without inventing answers to
this question. It is the position paper's next section.

## Q6 — Is a switch reconfiguration a budgeted operation? (added 2026-07-10)

**Ask:** does an actuation of the photonic switch fabric carry a cost the
OS must ration — power/thermal budget, duty-cycle limit, component wear —
or are actuations free at OS-relevant rates?

**Threshold that flips a decision:** the sustainable actuation rate (or
per-actuation wear) vs the actuation-rate difference between quality-blind
and quality-aware routing. The spatial battery found that when
reconfiguration is fast relative to deadlines, path-quality-aware routing
is outcome-equivalent to blind rotation and its ENTIRE payoff is churn:
−39% switch reservations and −96% pool wastage at the widest feasible
quality spread. If actuations are free, that saving is worthless and the
OS should not represent per-path quality for routing in this regime; if
the fabric has an actuation budget, the churn currency is real and the
representation earns admission (the admission rule reads through: the
quantity's reading decision is "route by quality or don't").

**Instrument grounding:** S1+S2 (2026-07-10, runs committed bd4615c /
1baa246, S2 prediction committed pre-run). Rigged-result caveat carried:
one frozen epoch — this licenses comparative reading at fixed quality
only, not prediction over time (that half stays with B2/T4 and the Q7/Q8
rulings in the battery prereg).

---

**Meta-finding, recorded:** the discipline pipeline (pre-registered
prediction surfaces, write-once-then-look, control-calibrate-then-open,
calibration bridge across instrument changes) ran end-to-end on 2026-07-09
and held. When real hardware data arrives, the honesty machinery is
already built and battle-tested; the second simulator inherits it whole.
