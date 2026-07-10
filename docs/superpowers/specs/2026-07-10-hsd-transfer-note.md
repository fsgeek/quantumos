# HSD method transfer — history, maintenance economics, and the Markov-completeness question

**Date:** 2026-07-10
**Source:** Tony's HSD storage work (the weighty-negative-paper precedent:
reads consumed future write capacity; reclamation units exceeded logical
objects; low utilization did not imply low maintenance), surfaced in
conversation with an external reviewer the same day as the S1 mechanism
correction. Routed by point of use, per the Chertov transfer pattern.

## The sharp question this transfers

> Can two machine states that look identical to the present OS object model
> have materially different futures because of operations already performed?

For HSD the answer was yes (reads silently spent future media stability),
which made current-contents + free-space an incomplete state description.
For qsim TODAY the answer is no BY CONSTRUCTION — every cost is immediate,
decay is observable in fidelity, wear is applied where the OS can see it.
That "no" is a property of the model, not of the machine. The mechanisms
that would flip it are exactly the ones parked or blocked: QND read wear
(Q3's ε branch, built and waiting on a scalar), calibration drift (B2,
blocked on Q7/Q8 rulings), and any hardware answer to Q4/Q6 that carries
duty-cycle or fatigue terms.

**Method rule this adds — sweep HISTORY, not just operating points:** when
any history-dependent mechanism lands, the battery gains a new test class:
drive two runs to identical instantaneous observables (load, pool depth,
quality table) via different histories (clean start vs prolonged churn) and
diff their futures. If futures diverge, the scheduler's exposed Markov
state is incomplete, and the missing history term must pass the admission
cascade like any other quantity.

## Instrument-earned TODAY: the maintenance-dominated regime

The HSD low-nonzero-utilization pathology (a little live state keeps the
maintenance machinery running over mostly-dead space) has a measured
analogue already sitting in the committed S1 anchor run (rr, δ=0, calm):

- switch reservations: foreground 145 vs replenish 467 — **76% of all
  fabric actuations are maintenance** (3.22:1);
- pool wastage: 334 deposited, 243 withdrawn, 85 expired — **25.4% of
  manufactured entanglement ages out unconsumed**.

At this operating point, demand is sparse enough that most inventory
perishes, but not sparse enough to quiet the low-water replenishment. This
is the perishable-good economics in its purest visible form — maintenance
work amplified by a small live demand ("quantum garbage collection" is the
reviewer's phrase; adopt with the caveat that nothing here pins domains or
fragments — expiry is purely temporal).

**Candidate excursion (not run, not precommitted):** sweep arrival rate
downward from the calm point and map maintenance-to-useful actuation ratio
and pool wastage vs demand. Expected shape: a hump — the ratio worsens as
demand thins (fixed low-water maintenance amortized over fewer useful
events) until demand is sparse enough that admission/pregen should
arguably turn OFF, which is itself an OS decision (pregen hysteresis) that
currently has no policy. The decision that reads the curve: when should an
OS stop maintaining inventory it will probably never use?

## Candidate questions — parked, NOT added to the committed list

The committed question list is instrument-earned; these three are
analogy-earned (HSD) and stay parked until a run or a hardware answer
forces them:

1. **Latent consumption** — can an operation spend part of a resource's
   future usefulness while the resource still reads as available? (QND ε
   is the live candidate; earns admission when the Q3 branch runs.)
2. **Pinned maintenance domains** — can one live lease/path/calibration
   dependency prevent reclaiming or resetting a larger shared unit? (Kin
   to Q5's compatibility-relation reframe; earns admission if the port
   envelope answer names shared banks/domains.)
3. **Age-dependent maintenance amplification** — does restoring a domain
   cost more with operating history (actuation count, read count,
   fragmentation of live state)? (No current mechanism; earns admission
   only from hardware.)

## Framing language worth keeping (talk §6, position paper)

- The questions discover the **contract boundary**: each physicist answer
  ("not stable," "not observable without disturbance," "the unit is a
  bank, not a port") corrects an abstraction, not a parameter.
- The productive asymmetry: "here is the decision, the quantity it reads,
  the lead time — at what threshold does your hardware invalidate this
  distinction?"
- The v2 success criterion: **version 2 should fail for fewer accidental
  reasons** — by the time it says "impractical," the remaining reasons
  belong to physics or architecture, not simulator ambiguity.
- The legitimate endpoint: a joint-envelope negative result ("no single
  parameter improvement suffices; practical operation requires crossing
  THIS envelope") is a heavier contribution than an optimistic scheduler
  under unrealizable assumptions. HSD is the precedent.
