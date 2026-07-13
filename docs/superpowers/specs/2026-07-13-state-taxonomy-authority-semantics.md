# State taxonomy + authority semantics for the perishable good (working note)

**Date:** 2026-07-13
**Status:** DRAFT for veto. Vocabulary and structure only — nothing here is admitted into
qsim (admission waits on the gate cascade; see "What this note does not do"). Naming is
PROVISIONAL and flagged as the veto item.
**Inputs:** (1) the parked lifecycle note (2026-07-05, Registers 1–3 discipline inherited);
(2) Yamaguchi et al., arXiv 2602.10695 (encrypted cloning demonstrated on IBM Heron R2,
docs/references/); (3) an external multi-scout perspective map (Codex, 2026-07-13, supplied
by Tony).
**Method rule applied throughout:** a represented state must name the decision that reads
it (object-model admission rule). States with no reader are listed as speculation, not
taxonomy.

---

## 1. The invariant

**Plural encrypted presence, single materialization.** (Convergent phrasing from the scout
map; adopted.) Quantum information may be spread to n sites without dilution — the paper
demonstrates this survives hardware noise, with degradation tracking circuit depth and idle
time, not clone count. Exclusivity is not enforced on the data; it is enforced one level up
by a consume-once recovery authority. The scarce, schedulable, protectable object is the
authority, not the state.

## 2. The structural correction: two ontologies, not one taxonomy

A flat state list (live / encrypted potential / spent / lost …) mixes two
**different-kinded** objects and repeats the commensuration error (method lesson,
2026-07-05: a knob that commensurates different-kinded things is premature collapse). The
taxonomy splits:

- **Carrier states** — where and what the physical presence is.
- **Claim states** — the condition of the recovery authority.

In the pre-cloning world (all of qsim today) each good has exactly one carrier and the
claim is implicit in possession of it. **The two objects coincide in the degenerate case —
which is why the 07-05 abstraction was hard to name: it is two objects that look like one
until a mechanism pulls them apart.** Encrypted cloning is that mechanism, now demonstrated
on hardware.

### 2.1 Carrier states (reader decision in bold)

| State | Description | Read by |
|---|---|---|
| latent | heralded, single presence, aging unobserved in flight (birth certificate, not heartbeat) | **admission / retry** (existing qsim semantics) |
| live | materialized, local, consumable | **consumption gate** — fidelity threshold at consumption (Register-2 corrected shape, 07-05; not yet built) |
| encrypted potential | plural presence; each site individually maximally mixed; unreadable, unrouteable as data; **not lost** | **binding** (which site materializes — late binding) and **abandonment** (when to stop paying carry cost) |
| spent residue | the n−1 sites after materialization: provably worthless, still occupying hardware | **reclamation** (garbage collection) |
| dead | terminal, with death-KIND preserved (see 2.3) | **accounting / cause-tagged terminals** (fidelity_at_outcome pattern) |

### 2.2 Claim states

The claim is **relational and physical**, not a classical bearer token (scout-map
correction, adopted): {designated clone + the full n-qubit noise bundle + the decryption
operation + control-path ability to execute it}. Losing any element loses the claim.

| State | Description | Read by |
|---|---|---|
| intact | all key qubits coherent; custody resolved | **exercise authorization** — who may attempt materialization. Physics does NOT provide this: no mutual exclusion, no authentication, no split-brain prevention. Classical control must serialize attempts. |
| decaying | held but aging. The option has a theta, empirically priced: waiting through one extra clone generation before exercising dropped Fe 0.569 → 0.355 (paper Table III, l=2 vs l=2*) | **exercise timing** — hold vs. exercise now |
| consumed | exercised; provides *post-action fencing* (all other presences are dead by physics) | nothing — that is the point; at-most-once is free after the fact |
| torn *(speculation)* | interrupted or partial decryption: neither materialized nor recoverable. Not examined by the paper | **crash consistency / failure handling** — flagged, no reader designed |

Two claim facts with OS weight:

1. **The claim is itself a perishable good.** It decoheres, it cannot be cloned (no-cloning
   applies to the key), and it has location — an all-n-of-n kernel that must survive intact,
   dual to the any-1-of-n redundancy on the carrier side. *Conjecture (flagged, not
   claimed): fragility is conserved — it can be relocated but not eliminated. Iteration
   relocates it at a favorable exchange rate (key grows linearly while clones grow
   exponentially: n(l+1) key qubits for (n+1)^(l+1) clones) but an all-of-n kernel always
   remains somewhere. If true, "where does the fragile kernel live" is a placement decision
   the OS must own.*
2. **The linearization point is classical.** Physically, delayed-choice orderings are
   frame-dependent (paper, Experiment 2 + relativistic discussion); operationally, the OS
   commits at a classical event — the decision-plus-control-pulse that launches decryption.
   The OS serializes a classical event even though the resource is quantum. Recovery-stack
   shape that follows (scout map, adopted): one-shot key-gated quantum checkpoint + a
   classical WAL for measurements, Pauli frames, calibration epochs, and scheduler
   decisions.

### 2.3 Death-kinds propagate (inherited constraint, 07-05)

Coherence death (hard cliff, *ser* — hypothesized, pending Simmons Q1) and schedule death
(survivable slope, *estar*) remain distinct and non-commensurable. New question the split
raises, deliberately left in Register 3: which kind is the death of *encrypted potential*?
Key decoherence degrades recovered fidelity gradually (slope-like) until the noise floor
(cliff-like categorical loss). Do not resolve this by fiat; it is a measurement question.

## 3. The four faces (07-05, Register 1) under the split

The parked note's four faces of the missing abstraction organize cleanly — evidence the
split is the right cut, not a new layer of structure:

- **where it lives** → carrier location, now possibly plural (binding decision).
- **born vs demanded** → claim creation vs claim exercise; the two anchors were always
  claim-side facts disguised as carrier-side clocks.
- **whether its death is observed** → cause-tagged terminals must now tag *which object*
  died (carrier vs claim) as well as which kind.
- **is a good delivered after death still itself** → a claim exercised past a death
  threshold materializes noise, not the good — the fidelity-threshold-at-consumption gate,
  unchanged.

## 4. Provisional naming (THE veto item)

Proposed: **carrier** and **claim**. The perishable good = one claim + one-or-more
carriers; the OS tracks claims, carriers are where claims can be exercised.

Alternatives rejected (one line each, per grounding norm):
- *capability / token* — implies a classical, copyable-or-at-least-durable bearer object;
  the claim is physical, relational, decaying.
- *replica / backup* — implies readable copies; encrypted presences are individually
  maximally mixed and readable by no one.
- *future / promise* (single-assignment handle, forced at most once, site chosen late) —
  attractive as verb-framing ("materialization forces the future") and kept as prose
  imagery, but PL-loaded and silent about decay and plural presence.

## 5. Boundary ledger

| Register | Content |
|---|---|
| Paper-demonstrated | plural encrypted presence survives hardware noise; degradation tracks depth/idle, not clone count; entanglement witness to n=7 direct, 27 iterated; CHSH violation through clone-and-decrypt to n=3; clones individually maximally mixed; idle-cost priced (l=2*) |
| Systems mapping (ours, defensible) | two-ontology taxonomy; claim as consume-once relational authority; classical linearization point; late binding; spent-residue reclamation; theta on held claims |
| Speculation (flagged) | torn materialization; conservation of fragility; option-portfolio placement; death-kind of encrypted potential; any coupling into decoder backlog (Register 3 of 07-05, still parked) |

## 6. What this note does not do

- Does not admit any state into qsim. Admission waits on the hedged-placement mechanism
  naming its decision and passing the gate cascade (DECISION-EARNED → REPRESENTATION-CHEAP
  → FIELD-EARNED).
- Does not touch deadline semantics, duration separation, or the backlog coupling (07-05
  next-instance instructions remain in force).
- Does not finalize names — carrier/claim is standing for veto.
