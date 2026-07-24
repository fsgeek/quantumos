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
For qsim, distinguish two claims (sharpened by review round 2, which
caught the first version conflating them):
- The FULL simulator microstate is Markov by construction — every cost is
  immediate, no hidden substrate accumulates. That part is true today.
- The state exposed to each OS DECISION is already an open question NOW,
  no latent physics required: `decide_admission` sees decoder backlog
  COUNT but not residual service time (`_decoder_free_at` is
  engine-private, verified 2026-07-10), and pool DEPTH hides the age
  distribution of its residents — equal depths with different age mixes
  have different futures.

**Two separable items this yields:**
1. **Present-tense audit (actionable now):** for each decision interface,
   enumerate represented-but-unexposed state (lease ages, residual decoder
   service, deadline headroom, in-flight events) and ask which omissions
   the decision can feel. This is an admission-interface audit, not a
   history experiment.
2. **Method rule for later — sweep HISTORY, not just operating points:**
   when a history-dependent mechanism lands (QND read wear = Q3's ε
   branch; calibration drift = B2, blocked on Q7/Q8; any Q4/Q6 answer with
   fatigue terms), the test class is: (i) fix the decision interface under
   test, (ii) match ALL state currently exposed to it, (iii) couple future
   stochastic draws, (iv) diff conditional futures across histories.
   Skipping (ii) rediscovers item 1's omissions and calls them latent
   damage.

## Instrument-earned TODAY: the maintenance-dominated regime

The HSD low-nonzero-utilization pathology (a little live state keeps the
maintenance machinery running over mostly-dead space) has a measured
analogue already sitting in the committed S1 anchor run (rr, δ=0, calm):

- switch reservations: foreground 145 vs replenish 467 — **76% of all
  fabric actuations are maintenance** (3.22:1);
- pool wastage: 334 deposited, 243 withdrawn, 85 expired — **25.4% of
  manufactured entanglement ages out unconsumed**.

The precise finding (wording corrected after review round 2): most
inventory does NOT perish — 73% of deposits are withdrawn — yet
maintenance still dominates fabric activity 3:1. That is **maintenance
amplification, not wholesale inventory loss**: a modest wastage rate
sustained by low-water triggering keeps the fabric mostly busy on upkeep.
This is the perishable-good economics in its purest visible form
("quantum garbage collection" is the reviewer's phrase; adopt with the
caveat that nothing here pins domains or fragments — expiry is purely
temporal).

**Candidate excursion (not run, not precommitted):** sweep arrival rate
downward from the calm point and map maintenance-to-useful actuation ratio
and pool wastage vs demand. Expected shape: a hump — the ratio worsens as
demand thins (fixed low-water maintenance amortized over fewer useful
events) until demand is sparse enough that admission/pregen should
arguably turn OFF — an OS decision that currently has no policy. Name the
DECISION, not the mechanism (review round 2, and the premature-collapse
lesson): the missing policy is **pregen gating / adaptive inventory
control** — whether and how much inventory to maintain; hysteresis is one
candidate mechanism, not the earned name. The decision that reads the
curve: when should an OS stop maintaining inventory it will probably
never use?

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

## Addendum 2026-07-24 — primary source verified first-hand

The paper is now in-repo (docs/references/2025-Holographic-Storage-for-the-
Cloud.{pdf,txt}, committed 57e060c) and was read in full on 2026-07-24.
Citation for the pass: Cheriere et al., "Holographic Storage for the Cloud:
Advances and Challenges," ACM Trans. Storage 21(1), Article 3 (Jan 2025),
DOI 10.1145/3708993, open access (CC BY-NC-ND).

**Verification of this note's claims against the primary:**

- Latent consumption CONFIRMED as *read erasure* (§3.1 of the paper): reads
  use the same 532 nm light as writes at lower power and cumulatively erase
  ALL superposed holograms in the zone, including the one being read;
  periodic read refresh (copy live data to a fresh zone) is mandatory. One
  precision correction to this note's own header line: "reads consumed
  future write capacity" mis-compresses the mechanism — reads consume the
  zone's future READABILITY (its read budget); refresh, a write operation,
  restores what reading spent. The body's phrasing ("reads silently spent
  future media stability") was already accurate. Correction carried here
  rather than silently rewritten, per the compression-carries-correction
  rule.
- Reclamation-units-exceed-logical-objects CONFIRMED: UV erasure is
  zone-granular; pages are append-only within a zone; GC must relocate
  every live page before the zone can be reset. (The pinned-maintenance-
  domains parked question's precedent, exactly as parked.)
- Low-utilization-does-not-imply-low-maintenance: the paper's published
  support is HTL-overhead dominance (refresh + GC amortization dominate
  end-to-end energy) plus the stranded-capacity discussion (§2.1, for
  HDDs). The strongest quotable form is the accounting finding below.

**New first-hand hooks (beyond what this note carried):**

1. **The read-budget invariant** — "the read budget of a zone always
   exceeds the number of live pages in it; i.e., each live page can be
   read at least once more," with refresh decisions reading the budget.
   A wear budget as a first-class, decision-named quantity: classical
   precedent for Q3's wear-budgeted lease and §8's calibration-as-
   budgeted-service. ROUTED: one sentence added to §8 (draft, 2026-07-24).
2. **Variable read profile** — energy per read rises with accumulated
   erasure until refresh; prior work assumed constant. Maintenance cost is
   history-dependent; kin to Q3's caveat against a state-independent
   scalar ε.
3. **The accounting-boundary finding** — with HTL overhead excluded from
   the ledger, jointly-optimized and end-to-end-optimized configurations
   perform near-identically; with it included, end-to-end wins (14× at 50%
   reads, and the optimum MOVES: raw pages per zone 400 → 1,018). Where
   the books stop determines which design wins: a measured classical
   precedent for §4's thesis that the accounting is the contribution.
   ROUTED: §9/§13 framing; cite at the citation pass.
4. **Write erasure** — manufacturing new stock degrades existing stock in
   the same zone (cross-good damage at manufacture). PARKED per this
   note's own discipline: no qsim mechanism; kin to Q6's
   calibration-disturbance candidate list; earns admission only from
   hardware.
5. **The quantified negative envelope** — "at least another 13×
   improvement in end-to-end energy efficiency" needed under explicitly
   optimistic assumptions, closable only by fundamental media advances:
   the joint-envelope negative-result precedent §13 needs, now first-hand
   with its number.
