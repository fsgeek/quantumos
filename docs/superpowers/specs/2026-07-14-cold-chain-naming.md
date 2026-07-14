# Naming the perishable-good abstraction: the cold chain

**Date:** 2026-07-14
**Status:** NAME ACCEPTED (Tony, in-session veto passed 2026-07-14). This discharges the
naming deferral of `2026-07-05-perishable-good-lifecycle-parked.md`. All other 07-05
next-instance prohibitions remain in force (see §7).
**Inputs:** (1) the parked lifecycle note (2026-07-05) — the four faces and the three
registers; (2) the Chertov naming test (`2026-07-09-chertov-method-transfer.md` §4);
(3) the HSD maintenance-economics note (`2026-07-10-hsd-transfer-note.md`);
(4) `2026-07-13-state-taxonomy-authority-semantics.md` + Yamaguchi et al.,
arXiv 2602.10695 (the mechanism that splits the named object; §5 below).
**Produced by:** a fresh instance, rested reader present, per the 07-05 instruction —
named against the parked note without candidate anchoring (the Chertov note's deferral
was honored; no prior candidates existed).

---

## 1. The name and the claim

**Entanglement is a cold-chain good, and the position paper's object model is missing
the custody record: where the good is, since when, and what it has been exposed to.**

In one sentence: a classical OS manages a **warehouse** — its goods (pages, blocks,
cycles) are dry, ageless, interchangeable, and that is precisely what licenses every
aggregation it performs; a quantum OS manages a **cold chain** — its central good spoils
in place, so location and elapsed custody are not metadata, they are the state.

The name is a pun that happens to be true: the goods are at millikelvin. The quantum OS
runs a cold chain literally — the refrigeration and the computer are the same machine.

## 2. The four faces under the name (organize-or-dissolve test: organizes)

- **where it lives** → the custody map. Cold chains are defined by nodes and legs;
  "which refrigerator, which truck" is first-class. This is the ports/paths/topology
  demand.
- **born vs demanded** → an expiry date and an appointment. Herald is the manufacture
  date; arrival is the appointment in the clinic. Logistics never confuses or adds
  these — they are different-kinded, which preserves the 07-05 prohibition against
  commensurating the two anchors without separating the durations in code.
- **whether its death is observed** → the vial monitor. Cold chains invented
  time-temperature indicators precisely because exposure is invisible in transit (the
  herald is a birth certificate, not a heartbeat). Booking spoilage at every terminal,
  successes and failures alike, is standard cold-chain practice and was the
  `fidelity_at_outcome` fix.
- **whether a post-death good is still itself** → spoilage discipline. A vaccine past
  its exposure budget is not a discounted vaccine; administering it is harm. Sub-threshold
  `completed_late` is a drop, booked as loss. The immortal past-deadline zombie was the
  code administering spoiled doses at a discount.

## 3. The Chertov test (required acceptance criterion — passes)

The test: the name must make obvious why Chertov's aggregate-queue collapse works for
packets and fails for leases; it must carry "what happens to the item while it waits,
and where it waits."

Packets are dry goods — an aggregate queue is legitimate; count them. Leases are
cold-chain goods — pool depth hiding the age mix is malpractice; date them.

> **You can count packets; you have to date doses.**

Under the Yamaguchi split (§5) the test deepens rather than fails: encrypted presences
are individually maximally mixed — individually valueless, valuable only relationally —
so aggregation fails one level deeper still. You can count packets; you must date doses;
and some doses are blank until the key names one.

## 4. Register safety and rejected alternatives

**Register 2/3 safety:** the name does not smuggle the cliff-vs-slope question past the
toll gate. Real cold-chain practice does not claim the underlying chemistry is a cliff —
degradation is continuous; the **decision at consumption** is a threshold (administer or
discard, via the indicator). That is exactly the Register-2 corrected fix shape (fidelity
threshold at consumption) and it survives either Simmons Q1 answer. The backlog coupling
(a delayed leg leaves the next shipment on the dock, accumulating exposure) exists in the
metaphor with room reserved and remains unmodeled, as instructed.

**Rejected (one line each, per the grounding norm):**
- *lease* (already in code) — lapses by contract, does not rot; carries no location.
- *TTL / cache staleness* — staleness is correspondence to a refreshable source of
  truth; entanglement has no source to re-read.
- *wasting asset / option theta* — prices decay continuously; re-imports the
  discounted-success bug Register 2 corrects. (Post-Yamaguchi disposition: the metaphor
  is wrong for the carrier's consumption decision and **correct for the claim's
  exercise-timing decision** — see §5. Each metaphor lands on the decision that reads it.)
- *ember* — carries decay-in-place and categorical death (ash) but no logistics, no
  observability story; a mood, not a model.
- *worldline* — carries where-and-when, but a durable particle has one too; fails the
  Chertov test outright (silent on what happens while it waits).
- *zombie / immortal-past-deadline* — names the pathology, not the object.

**Prior-art shelf (credit first, then scope novelty — rotation-finding lesson; shelf
pointers UNVERIFIED until citation pass):** perishable-inventory theory (blood-bank
inventory; Nahmias's survey is the canonical entry), cold-chain logistics and pharma
pedigree / chain-of-custody practice, and **postponement / delayed differentiation**
(Alderson; the HP printer-localization case) for late binding. Scoped novelty: those
systems track custody *around* their machines; a quantum OS is the first system whose
**scheduler must be the cold-chain operator**, because the refrigeration and the computer
are the same machine.

## 5. The Yamaguchi wrinkle: the perishability migrates to the paperwork

Encrypted cloning (arXiv 2602.10695, demonstrated on Heron R2) is the mechanism that
pulls the named object apart into the 07-13 kind-split (carrier / claim / warrant /
exercise gate). The cold-chain reading of the split:

- **Encrypted cloning lets the OS ship the goods like dry goods** — plural presence at
  n sites, no dilution penalty — **by concentrating all of the perishability into the
  shipping documents.** The claim is itself a perishable good: it decoheres, no-cloning
  applies to it, and it has location. **The waybill becomes the cargo.** The cold chain
  does not close down; it stops carrying doses and starts carrying title.
- The conservation-of-fragility conjecture (07-13, flagged) is the cold-chain statement:
  the fragile kernel can be relocated (at a favorable exchange rate) but not eliminated;
  an all-n-of-n document always exists somewhere, and "which vault holds it" is an OS
  placement decision.
- **Encrypted potential is postponement at the physical limit:** goods individually
  indistinguishable from noise until the key names one; commit at the last minute.
- **Spent residue** (n−1 provably worthless sites still occupying hardware) is the
  expired stock awaiting disposal — the reviewer's "quantum garbage collection," now with
  a precise referent.
- The claim's decay is correctly priced continuously for the **exercise-timing** decision
  ("the option has a theta," Fe 0.569 → 0.355 for one extra held generation — paper
  Table III), while the carrier's death at **consumption** remains a threshold. The
  kind-split sorts the metaphors along with the objects.

**Composition:** "the cold chain" names the section; carrier / claim / warrant / exercise
gate (07-13, still standing for veto) is its object-model anatomy. The composite
perishable good = one claim + one-or-more carriers; the custody record must now say
**which object** died (carrier vs claim) as well as which kind (coherence vs schedule) —
consistent with 07-13 §3.

The HSD maintenance economics rides along unchanged: 76% of fabric actuations being
maintenance is the refrigeration bill — a cold chain runs its compressors whether or not
the shelf is full.

## 6. Addendum (same day): the one-use capability — interface name, not object name

Tony's framing, in-session 2026-07-14: what Yamaguchi found is beautifully expressed by
the 1970s systems term **capability** — specifically a **one-use capability**.

**Reconciliation with the 07-13 rejection (which stands):** the taxonomy note rejected
*capability/token* as a name for the **claim**, because the claim is physical, relational,
and decaying, while OS capabilities are classical and copyable. Both are right at their
own level. The term attaches to the **interface**: the composite {valid warrant + intact
claim + gate admission} presents exactly one-use-capability semantics to everything above
it. The claim is the *backing store* of that capability, not the capability itself — the
same relation as file descriptor to inode, or as a classical capability to the kernel
c-list that implements it. Nobody calls the kernel table a capability; nobody should call
the key bundle one. The name lives at the interface; the anatomy (carrier / claim /
warrant / exercise gate, 07-13, still standing for veto) lives underneath.

**Why the term is load-bearing rather than decorative:**

1. **It reframes no-cloning from a storage constraint to an authorization primitive.**
   Yamaguchi shows quantum data is copyable after all (encrypted, at will, no dilution);
   what physics irreducibly provides is not uncopyable *data* but the universe's only
   **native linear capability** — use-exactly-once, enforced by dynamics rather than by
   a reference monitor.
2. **Classical linearity is always mediated linearity.** Bits copy freely, so every
   classical single-use object (single-use tokens, exclusive transfer in ocap systems,
   money — the double-spending problem) requires a trusted mediator to police
   non-duplication. Physics provides the at-most-once half natively — but only
   **after** exercise (post-action fencing; taxonomy 2.2). Attempt serialization
   remains classical: the exercise gate. The split is complementary — classical
   mediation before the linearization point, physics after it.
3. **The 1970s produced both halves** *(shelf pointers, unverified until citation
   pass)*: capabilities (Dennis & Van Horn 1966; Hydra; Lampson's protection matrix)
   and Wiesner's conjugate coding / quantum money (manuscript circa 1970, published
   1983) — a physics-enforced unforgeable token. The two threads meet here: quantum
   money was the first proposed use of quantum information, and it was a capability.
4. **Cold-chain convergence — the bill of lading.** Logistics has run one-use
   capabilities for centuries: a negotiable bill of lading is a document of title,
   surrendered against delivery — one use, then spent — policed by law because paper
   copies. §5's "the waybill becomes the cargo" sharpens: **the waybill was always a
   one-use capability made of paper; the claim is one made of physics, and it polices
   half of itself.**

**Rhetorical consequence for the paper:** this is the bridge for the classical-OS
reader. "You already know this object — it is a capability; your kernels have been
faking its linearity with mediation for fifty years, and physics finally implements it
natively (half of it)."

## 7. What this note does not do

- Does not separate the durations, does not model the backlog coupling, does not rebuild
  deadline semantics (07-05 instructions remain in force; Simmons Q1–Q3 still pending).
- Does not admit any state into qsim (07-13 gate cascade governs admission).
- Does not finalize the taxonomy names (carrier / claim / warrant / exercise gate remain
  the 07-13 veto item).
- Does not write the paper section; it names it. The section drafts against this note,
  the parked note, and the 07-13 taxonomy together.
