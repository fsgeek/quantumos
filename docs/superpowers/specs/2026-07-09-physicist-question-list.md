# The physicist questions (instrument-earned, threshold-framed)

*(Retitled 2026-07-10: the spatial battery earned a sixth question and
sharpened Q4. Same day, external adversarial review corrected the
mechanism attribution — Q4 re-sharpened with protocol branches, Q1 scoped,
Q6 narrowed, Q7 added restoring the displaced rank-persistence ask. See
the dated amendments below and the S1 run note's correction section.)*

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

**Scope caveat (added 2026-07-10, external review):** the replenishment
cadence is partly OS-created (low-water policy), not purely physical. What
hardware can supply is the distribution of constituent service times
(actuation, settling, herald attempt, reset, communication). CoV also
cannot distinguish heavy tails from multimodality or state dependence; the
operational form of the ask is a QUANTILE threshold — is the upper-tail
configuration-plus-generation latency small enough that a replenishment
issued at the scheduler's lead time completes before its reserve margin
expires?

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

**Two retries, two thresholds (separated in round 4 — the original text
grounded an in-place-herald question in a round-lineage finding):**

*Round-lineage retry* (a failed ROUND re-enters as a new arrival,
re-choosing paths): threshold is marginal retry occupancy vs remaining
slack and the opportunity cost to waiting work. S0's unbounded-retry
congestion-aging spiral (the first RUN finding) lives at THIS level —
cheap lineage re-injection at high failure rates aged the very leases it
served, so lineage-retry discipline interacts with admission control. The
0.68 s cadence in T1-open's prediction surface is this level's
re-injection delay, not herald recovery.

*In-place herald retry* (a failed ATTEMPT on a still-configured path):
threshold is the failure-to-next-attempt time vs deadline slack — the
spatial battery's regime knob. Bounded by the round deadline in our
model; whether real hardware permits retain-and-retry at all is the
protocol branch below.

**Instrument grounding:** the retry spiral (lineage level, S0) and the
spatial battery's bracketed two-regime result (herald level, 2026-07-10
run note). Both costs are invented in the model and must come from
hardware; they interact but are not the same retry.

**Sharpened by the spatial battery (added 2026-07-10; mechanism corrected
same day, external review — see run-note correction):** the same quantity
carries a second decision. The failed-attempt CYCLE TIME relative to
deadline slack decides whether path quality can matter in OUTCOMES at all.
Two distinct first-order quantities scale with it (review round 2): the
blind-policy heterogeneity penalty (E[1/p] − 1/p̄) × T_attempt, and the
larger quality-awareness payoff (E[1/p] − 1/p_max) × T_attempt — both
microseconds in our model against seconds of slack. The
minimum-sufficient asks are therefore protocol-branched:
- After a heralding failure, can another attempt run ON the already
  configured path, reservation retained — or must some/all of the optical
  path be released, reset, or reconfigured?
- What is the complete failure-to-next-attempt cycle time
  (emission + propagation + detection window + herald return + reset)?
- Do the answers differ between on-demand generation and speculative
  replenishment? (Our simulator currently implements retain-and-retry for
  rounds but release-and-reacquire for replenishment — a design choice,
  not a physics-earned asymmetry; the hardware answer decides which is
  real.)

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

**Threshold that flips a decision (rewritten round 4 — the original
paragraph restated the pre-correction mechanism; its narrowing note below
is retained as history):** the sustainable actuation rate (or
per-actuation cost of any constrained resource) vs the actuation-rate
difference between quality-blind and quality-aware routing. In the
low-attempt-price regime the spatial battery tested (failure-to-next-
attempt spacing of 100 µs against second-scale slacks, retain-and-retry
protocol), quality-aware routing showed no detectable outcome advantage
and its measured payoff was churn: −39% switch reservations and −96% pool
wastage at the widest feasible quality spread. In that regime the churn
currency is the only currency, and whether it has value is this question.
(At binding attempt prices the payoff moves into outcomes — Q4's regime
question — and this question then prices the SECONDARY savings.)

**Instrument grounding:** S1+S2 (2026-07-10, runs committed bd4615c /
1baa246, S2 prediction committed pre-run). Rigged-result caveat carried:
one frozen epoch — this licenses comparative reading at fixed quality
only, not prediction over time (that half stays with B2/T4 and the Q7/Q8
rulings in the battery prereg).

**Narrowed (2026-07-10, external review):** "actuations free implies the
saving is worthless" is too strong — even unbudgeted actuations can cost
fabric occupancy, controller traffic, thermal transients, cross-path
contention, calibration disturbance, and tail latency; all absent or
negligible at this experiment's ~0.4% utilization. The defensible
inference: at THIS operating point the simulator gives saved reservations
no currency except counted churn. The ask stands, broadened one notch:
does an actuation/reservation consume ANY constrained resource at the
relevant rate?

## Q7 — Path-rank persistence at scheduling lead time (added 2026-07-10)

**Ask:** how long does "the best path" remain best? The autocorrelation
time (or rank-inversion rate) of comparative path quality, measured at the
lead times an OS would act on — after measurement, publication, queueing,
and actuation delays.

**Threshold that flips a decision:** rank persistence vs decision lead
time. If the best path stays best for many lead times, a comparative read
of the calibration table is durable state worth publishing; if ranks
reshuffle faster than the OS can act, quality-aware routing is chasing a
ghost and the comparative representation fails admission even when the
churn currency (Q6) has value.

**Instrument grounding:** the battery prereg's original spatial question
(its Q6, the "QOS-shaped" ask) — displaced when this list's Q6 slot took
the actuation-budget question, restored here after external review flagged
the gap. S2's rigged-result warning is exactly this question's shadow:
one frozen epoch makes rank persistence infinite by construction, which is
why S2 licenses comparative reading only. Q7 is what B2's epoch sequences
would probe in-model; the hardware answer supersedes anything the
simulator can author.

---

**Meta-finding, recorded:** the discipline pipeline (pre-registered
prediction surfaces, write-once-then-look, control-calibrate-then-open,
calibration bridge across instrument changes) ran end-to-end on 2026-07-09
and held. When real hardware data arrives, the honesty machinery is
already built and battle-tested; the second simulator inherits it whole.
