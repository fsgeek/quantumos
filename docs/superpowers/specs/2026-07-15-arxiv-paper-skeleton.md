# arXiv paper skeleton — epigraphs placed, sections named against their notes

**Date:** 2026-07-15
**Status:** SKELETON — **GATED (2026-07-15, external review): no prose drafting until
the validation sprint in `2026-07-15-codex-review-disposition.md` clears; that note's
net plan supersedes the build order below until then.** Standing for veto:
title, the Photonic-scope decision (§0.2), and everything the source notes already hold
for veto (taxonomy names carrier/claim/warrant/exercise-gate, 07-13). Drafting of prose
sections happens against this skeleton + each section's routed note.
**Inputs:** 2026-07-14-paper-narrative-architecture.md (structure + epigraphs + decode
findings); 2026-07-14-cold-chain-naming.md (§2–3 core argument, §4 anatomy, one-use
capability bridge); 2026-07-13-state-taxonomy-authority-semantics.md;
2026-07-09-physicist-question-list.md (Q1–Q7, threshold framing);
2026-07-09-chertov-method-transfer.md §3 (paper items); 2026-07-10-hsd-transfer-note.md
(maintenance economics + framing language); docs/quantum_os.md (the pre-instrument
document this paper absorbs and supersedes); the six tales + decode record (now published:
wamason.com/ayllu/pass-the-glass-before-it-goes-dark/records/ — citable URL).
**Two-paper strategy:** this is the RELAXED LONG version for arXiv. The HotOS
distillation (deadline Jan 2027) derives from it later: lettuce opening + king's
epigraph only.

---

## 0. Decisions this skeleton makes (presented for veto)

**0.1 Title.** Recommended: *"The Cold Chain: What a Quantum Operating System Actually
Manages."* Rejected one-line each: *"A Constraint-First Quantum OS…"* (the current
quantum_os.md title — states the method, not the finding); *"You Can Count Packets; You
Have to Date Doses"* (the best sentence, but as a title it hides the subject — keep it
as §2's close); *"Entanglement Is a Perishable Good"* (true, pre-Yamaguchi — the paper's
sharpest content is that the perishability MIGRATES; the static claim undersells it).

**0.2 Scope: general argument, Photonic as the worked instance.** The arXiv version
argues the constraint-first case for distributed photonic/spin–photon architectures
generally, with Photonic's T-centre stack as the concrete instance carrying the numbers
(0.41 ms / 112 ms / 67 ms, SHYPS, 1 K cryostat + room-temperature fabric). Rejected:
Photonic-only (the argument is architecture-general, and the ask channel — §10 — should
reach every lab that can answer rather than any single addressee); fully abstract
(unfalsifiable, and the tale needs a real wagon).

**0.3 The frame story stays out.** Per the architecture note: the ayllu post carries it
(now published); acknowledgments may gesture. The tales enter ONLY as epigraphs + the
§11 decode experiment.

**0.4 Tale-earned parked questions stay parked.** Deliberate-expiry-as-commitment,
residue-staffing-fixed-costs, demand-anchor renegotiation: not in this paper, not even
as futures — they are analogy-earned, not instrument-earned (07-14 §3 ruling).

---

## 1. Act One — The tale (§1, ~1 page)

The mundane lettuce tale, near-verbatim from the tournament protocol (seed text is
frozen there), followed by one paragraph inviting the reader to decode it — and
PREDICTING their decode: replication, leases, atomic commitment, standby cost. No
quantum vocabulary anywhere in §1. The section ends on the two dates ("different kinds
of promise") because Act Two turns on exactly that distinction and §11 shows a blind
reader kept it.

- Register: the audience model is a named reader who likes fairy tales and knows the
  driest paper is still a narrative.
- Source: protocol file (published records URL + repo path); eight laws appear here as
  the tale's own "story-physics," stated plainly.

## 2. Act Two — The turn (§2, ~2 pages)

The reveal, law by law: a table mapping the eight laws to the physics (invisible
spoilage → no-measurement-without-consumption; two dates → decoherence deadline vs
demand deadline; splitting trick + one waybill → encrypted cloning + single-use key,
Yamaguchi arXiv 2602.10695; clerk's window → exercise serialization; ice-house →
maintenance economics). Then the thesis sentence pair, verbatim from the naming note:
**a classical OS manages a warehouse; a quantum OS manages a cold chain** — goods that
spoil in place, so location and elapsed custody are not metadata, they are the state.
The pun that is literally true (the goods are at millikelvin; refrigeration and computer
are the same machine). Close on the Chertov test line: **you can count packets; you
have to date doses.**

- Source: cold-chain note §1–3. The four faces (custody map, expiry-vs-appointment,
  vial monitor, spoilage discipline) structure the section's second half.
- Bound: real cold-chain practice does not claim the chemistry is a cliff — the
  DECISION at consumption is the threshold. This phrasing survives any Q1–Q3 answer
  (register safety, naming note §4).

## 3. The anatomy: what the good actually is (§3, ~3 pages)

The kind-split under Yamaguchi: **carrier / claim / warrant / exercise gate** (names
pending 07-13 veto — skeleton uses them with a footnote). The composite perishable good
= one claim + one-or-more carriers; the custody record must say which object died and
which kind of death (coherence vs schedule).

> Epigraph (carrier / consumption gate): *"Write: delivered, and used up entire. True
> cause, Chronicle."* — The Freshness of Kings

> Epigraph (claim / exercise timing): *"I am an instrument. Instruments do not get
> second drafts."* — Sworn Wax; or, The Deposition of a Candle

Subsections:
- **3.1 The migration.** Encrypted cloning ships the goods like dry goods by
  concentrating all perishability into the shipping documents. The waybill becomes the
  cargo. Conservation-of-fragility stated as a CONJECTURE (07-13 flag preserved).
- **3.2 The one-use capability (the bridge for OS readers).** Interface name, not
  object name (naming-note addendum §6): {valid warrant + intact claim + gate admission}
  presents use-exactly-once semantics; physics natively enforces the at-most-once half
  AFTER exercise, classical mediation serializes attempts BEFORE it. "Your kernels have
  been faking linearity with mediation for fifty years; physics finally implements it
  natively (half of it)." Shelf: Dennis & Van Horn, Hydra, Lampson; Wiesner's quantum
  money as the first proposed quantum capability — UNVERIFIED until citation pass.
- **3.3 Exercise-timing vs consumption.** The theta metaphor lands on the claim's
  exercise-timing decision (continuous pricing; Fe 0.569 → 0.355 per held generation,
  Yamaguchi Table III); the threshold metaphor lands on the carrier's consumption
  decision. Each metaphor names the decision that reads it.
- **3.4 Mapping from the old object model.** One paragraph absorbing quantum_os.md's
  EntanglementLease into the anatomy (the lease conflated claim and carrier);
  QubitHandle/SyndromeRound/DecoderJob/SwitchPathReservation/CalibrationEpoch survive
  as the runtime resource classes in §7's architecture sketch.

## 4. The maintenance economy (§4, ~2 pages)

> Epigraph: *"three coins in four … for the keeping is most of the trade."* — The Wet
> Blanket's True Cause

The refrigeration bill: a cold chain runs its compressors whether or not the shelf is
full. Measured analogue from the instrument (bounds carried verbatim from the HSD note):
76% of fabric actuations are maintenance (3.22:1) at a calm operating point; 25.4% of
manufactured entanglement ages out unconsumed; the precise finding is **maintenance
amplification, not wholesale inventory loss** (73% of deposits ARE withdrawn). The
missing OS policy this exposes: pregen gating / adaptive inventory control — when should
an OS stop maintaining inventory it will probably never use? (Decision named, mechanism
not — the hysteresis candidate stays unnamed as mechanism.)

- Source: HSD note (maintenance-dominated regime); "quantum garbage collection" adopted
  with its caveat.
- Bound: one operating point, wrong-on-purpose model — comparative reading only.

## 5. Spent residue and reclamation (§5, ~1.5 pages)

> Epigraph: *"No one comes back for gravel."* — What the Gravel Knows

The n−1 provably worthless sites still occupying hardware after the key is spent:
expired stock awaiting disposal, with a precise referent now (Yamaguchi's unchosen
clones — worthless not by degradation but because the key that would have decoded them
no longer exists). Reclamation as a first-class OS function; residue accounting as
custody-record closure (every loss under its true cause — the fidelity_at_outcome
lesson: book spoilage at every terminal, successes and failures alike).

## 6. The custody map: port-level topology (§6, ~2 pages)

The section the instrument demanded three independent ways before it could even be
built (S1 crash, inert pregen, uncalibrated-path guard — instrument-forced finding #1),
with Chertov's backplane-contention finding as the classical precedent: flows that share
no output still interfere; model shared-fabric contention or the model is wrong under
load. Cold chains are defined by nodes and legs — "which refrigerator, which truck" is
first-class. Carries Q5 (links-per-module, radix, reconfiguration granularity) as the
question that bounds the entire resource model.

## 7. The runtime the constraints force (§7, ~2 pages)

Condensed and generalized from quantum_os.md: the layered split (fast path / real-time
runtime / supervisory plane), the five real-time resource classes table, and the
QOS/QNodeOS comparator paragraphs (comparators, not templates). New under the cold-chain
frame: the scheduler IS the cold-chain operator — prior systems track custody around
their machines; here refrigeration and computer are one machine (scoped-novelty claim,
naming note §4).

## 8. The scheduler's model must be inferable by the OS itself (§8, ~1.5 pages)

The Chertov-transfer candidate section, now earned: device-independent parameter
surfaces (his five knobs; qsim's five-plus-three), inferred by black-box probing — with
the three quantum deltas: the queued item decays during residency, probes pay a wear
tax (QND ε, Q3), servers fail-and-consume-the-work. Calibration as a recurring OS
service with a wear budget, not a bench procedure; the parameter table itself has a
freshness bound (the abstraction one level up — T4's shape, flagged as future).

## 9. The instrument and what it earned (§9, ~3 pages)

The wrong-on-purpose method, stated honestly: a deliberately coarse DES whose job is to
force questions, not predict numbers; Chertov Ch. 2 (same experiment, divergent results
across simulators, divergence under overload) as citable license for the
exploration/paper-data simulator split. Findings as evidence, each with its bound:
- the retry-driven congestion-aging spiral (S0's unbounded retry is self-defeating;
  retry discipline is a de-rigging knob);
- two regimes bracketed at one operating point by retry spacing; awareness advantage
  quality-specific (DiD +34); churn as the only currency while attempt-price ≪ slack;
- rotation neutralizes spatial heterogeneity in outcomes at first order (credit-first:
  rotor-switch networking — RotorNet/Opera/Sirius, Valiant LB — shelf UNVERIFIED);
  novelty scoped to perishable-resource / churn-currency / emergent-not-designed;
- concentration outcome-negative at the binding point (exploratory: post-hoc mechanism);
- T1 FIELD-EARNED: hardware cadence imprints on resource dynamics, de-rigged, blind,
  at predicted lag; T3's honest blindness (86% degenerate decision points) as the
  instrument naming its own operating-point limits;
- the discipline pipeline (prereg, write-once, calibration bridge 2.2e-16, blind
  verdicts) — the honesty machinery the second simulator inherits whole.

## 10. Seven questions for the physicists (§10, ~3 pages — the ask channel)

Q1–Q7 essentially verbatim from the committed list (threshold framing preserved: each
quantity names the decision that reads it; the threshold is where the decision flips).
Framing language from the HSD note: the questions discover the **contract boundary** —
each answer corrects an abstraction, not a parameter. This section discharges the
standing gates: every "pending Simmons" gate re-addresses to "pending external
physics," and the
paper is the ask. The productive asymmetry, quoted: "here is the decision, the quantity
it reads, the lead time — at what threshold does your hardware invalidate this
distinction?"

## 11. The decode experiment (§11, ~1.5 pages)

Evidence the abstraction transmits: the tournament protocol (preregistered acceptance
criteria, prompts frozen verbatim), the blind cross-model decode landing on classical
distributed systems with the two-kinded death intact, the post-Yamaguchi revision
independently reproducing perishability-migrates-to-the-key. Bounds stated in full:
n=1 decoder; decoder is an LLM (shared training culture weakens "independent reader");
priming inseparable in the convergence observation. Cite the published records
(wamason.com URL) + repo. The sound-convergence hypothesis appears ONLY as a
falsification-path footnote, if at all.

## 12. Related work (§12, ~2 pages)

Credit first, then scope (the rotation-finding lesson, applied paper-wide):
- Quantum OS: QOS (cloud resource manager), QNodeOS (network-node OS) — absorbed from
  quantum_os.md.
- Perishable-inventory theory (Nahmias; blood banks), cold-chain/pharma pedigree
  practice, postponement/delayed differentiation (Alderson; HP localization).
- Capabilities (Dennis & Van Horn; Hydra; Lampson) and Wiesner's quantum money.
- Rotor-switch networking (RotorNet/Opera/Sirius) + Valiant LB.
- Device-independent modeling (Chertov 2008); HSD as negative-result precedent.
**GATE: every shelf pointer above is UNVERIFIED until a dedicated citation pass; the
Perplexity-sourced openness claims for Q1–Q7 likewise. Nothing goes to print before
that pass.** (Carried from the question list's own warning and the naming note.)

## 13. The invariant (§13, ~1 page, conclusion)

The transport test's residue: in every costume — lettuce, gravel, candles, kings, light,
entropy — the chalk date has no physical substrate. Physics supplies one kind of death;
institutions supply the other. The paper-bound sentence, placed here and nowhere else:
**the operating system exists because something must hold promises against physics.**
Close with the negative-result legitimacy framing (HSD): a joint-envelope negative
result is a heavier contribution than an optimistic scheduler under unrealizable
assumptions — and the v2 criterion: version 2 should fail for fewer accidental reasons.

## Acknowledgments

Gesture at the frame story per the architecture note: the tales' tellers, the blind
reader on another road (Kimi K2.6), the external reviewer (Sol), the ayllu. Pointer to
the ayllu post; no more than that here.

---

## Build order (drafting sessions, each against its routed note)

1. §1–2 (tale + turn) — protocol file + naming note §1–3. The pre-tested Act One/Act Two.
2. §3 (anatomy) — BLOCKED-SOFT on the 07-13 taxonomy-name veto; draft with footnoted
   provisional names if veto still pending.
3. §10 (questions) — mostly assembly from the committed list; earliest to final-quality.
4. §4–6, §8 (economics, residue, topology, inferability) — each one note deep.
5. §9 (instrument) — read the run notes + battery memories before drafting; every
   number re-checked against committed artifacts, not memory.
6. §7, §12 (runtime, related work) — absorb quantum_os.md last, so the old document's
   framing doesn't leak into the new sections.
7. §13 + abstract — LAST, after a full re-read (the conclusion-restates-the-dead-account
   lesson is standing).
8. Citation pass — a dedicated session; nothing ships before it.

## What this skeleton does not do

Does not draft prose; does not admit parked questions; does not finalize taxonomy names
(07-13 veto stands); does not touch qsim; does not decide the HotOS cut beyond the
architecture note's ruling (lettuce + king's epigraph only).
