# Adversarial literature matrix: occupancy of the paper's three core claims

**Date:** 2026-07-23 (evening)
**Discharges:** validation-sprint item (a) of the Codex-review disposition (c1a393c) — the
adversarial differentiation pass — and the draft's own §12 gate ("adversarial literature
matrix REQUIRED before any 'no prior system provides this' claim").
**Method:** twelve independent matrix cells (one reader per system or shelf), each prompted
adversarially — presume our territory occupied, hunt for the closest occupant, resolve
uncertainty toward OCCUPIED/PARTIAL, verdicts admissible only with verbatim quote +
locator. Every cell below rests on a first-hand full-text read EXCEPT REPS (see Bounds).
Three cells were second-round line-level upgrades of sweep-derived candidates, run because
the sweep's own disclosure said its verdicts rested on abstracts; one of those upgrades
caught a wrong author list already in the pipeline (see Corrections).

## The claims as tested

- **C1 (kind-split / presence-vs-recoverability):** the good splits into four kinds —
  carrier (physical stored state), claim (right to materialize exactly one usable good
  from one-or-more redundant carriers via encrypted/hedged cloning), warrant (classical
  key/credential whose own validity decays), exercise gate (classical mediation
  serializing the one-shot exercise) — with plural presence, ensemble-level
  recoverability, and late binding as DISTINCT runtime concerns.
- **C2 (custody record):** a per-good record — where it is, since when, what it has been
  exposed to — read at run time by admission and consumption decisions, with losses
  booked at every terminal under their true cause.
- **C3 (two dates):** the physical decoherence budget and the institutional demand
  deadline kept as different-kinded quantities under separate enforcement, never
  commensurated into one scalar, each loss booked as decohered vs late.

## Verdict table

| System | C1 | C2 | C3 |
|---|---|---|---|
| QNodeOS (Nature 2025) | ABSENT | ABSENT | ABSENT (one date, post-hoc only) |
| QOS (OSDI 2025) | ABSENT | PARTIAL | fails test (single-scalar commensuration) |
| ESDI (arXiv 2303.17540) | ABSENT | ABSENT | ABSENT (deadline only, no physics) |
| Chandra/Dai/Towsley (arXiv 2205.06300) | ABSENT | PARTIAL | ABSENT (physics only, no deadline) |
| Fidelity-Age (arXiv 2602.09562) | PARTIAL | PARTIAL | fails test (fidelity folded into age scalar) |
| REPS (INFOCOM 2021) † | PARTIAL | ABSENT | ABSENT (neither date) |
| Pre-distribution (Ghaderibaneh et al. 2022) | PARTIAL | PARTIAL | ABSENT (no deadline) |
| Repeater cutoffs (Iñesta et al., npj QI 2023) | ABSENT | PARTIAL | ABSENT (second date architecturally precluded) |
| Ent. buffering (Davies et al., Quantum 2024) | PARTIAL | ABSENT | ABSENT (Poisson consumption, no deadline) |
| SeQUeNCe (QST 2021) | ABSENT | PARTIAL | PARTIAL (reservation window, admission-only) |
| QuISP / RuleSet (QCE 2022 / arXiv 1904.08605) | ABSENT | PARTIAL | ABSENT |
| Classical shelves (six, see below) | — | halves exist separately | RTDB temporal validity = ancestor |

† REPS verdicts are secondary-sourced (no arXiv version; IEEE paywalled) from two
consistent full-text sources: ESDI (which positions against it) and the 2024 entanglement-
routing survey (arXiv 2408.01234, mechanism figure). Upgrade path: pull the PDF via
institutional IEEE access.

**Net finding: no single system holds two of the three claims together. The full form —
four-kind split + per-good custody with cause-tagged terminals + two co-enforced dates —
is unoccupied in everything read. Each single element has a named nearest occupant, so
every novelty sentence in §12 must use the fenced forms below.**

## Per-system records

### QNodeOS — Delle Donne, Iuliano, van der Vecht et al., Nature 639:321–328 (2025)
All three ABSENT. Coherence shapes scheduling only as static policy (non-preemption
"owing to limited quantum memory lifetimes"; TDMA "centrally optimized to mitigate
present-day memory decoherence") — never as a runtime per-good gate. The 8.95 ms
live-time bound (from measured Tcoh = 13(2) ms) is applied purely in post-processing:
"All measurement results corresponding to circuit executions exceeding 8.95 ms duration
were discarded (146 out of 7,200 data points)." No runtime decision reads qubit age; no
loss is booked by cause. QMMU virtual→physical remapping is address indirection, not
late binding among redundant carriers.
**Draft-claim check (against §2 prose):** (a) short lifetimes as central challenge —
SUPPORTED; (d) post-processing discard — SUPPORTED; (e) no true-cause booking —
SUPPORTED; **(b) "requests entanglement at a minimum fidelity" — CONTRADICTED** (no
fidelity parameter in QNodeOS's sockets; the min-fidelity request belongs to the cited
link layer, Dahlberg et al. SIGCOMM 2019); **(c) "schedules so live qubits do not wait
at ms scales" — CONTRADICTED as phrased** (the live server qubit waits ~4.8 ms and that
wait dominates infidelity; the scheduler stays on the QNPU to avoid ADDING CNPU
round-trips). Both repaired in the draft same day (see Corrections).
**One-liner:** coherence shapes QNodeOS's scheduling policy and its post-hoc data
filter, never a runtime custody record or consumption gate.

### QOS — Giortamis, Romão, Tornow, Bhatotia, OSDI 2025
Perishable resource is device time, not a stored quantum good — so C1's kinds have no
referents (its central move, the Qernel, is explicitly a UNIFYING "common denominator,"
the structural opposite of the kind-split). C2 PARTIAL: the estimator reads per-QPU
calibration data (readout/gate errors, T2) and a decay term ed(t)=1−e^(−t/T2) on
WITHIN-CIRCUIT idle time — per-device and per-calibration-cycle, not per-good custody.
C3: the scheduler's selection formula folds fidelity delta, waiting-time delta, and
utilization into ONE scalar score (c=β=0.5 default) — the canonical, citable
single-scalar commensuration; terminals are bare {done, failed}, uncause-tagged.
**One-liner:** per-device calibration freshness inside one selection scalar — neither
per-good custody nor two dates.

### ESDI — Gu, Yu, Li, Wang, Zhou, arXiv 2303.17540 (2023)
Citation verified (the reviewer's label is the paper's own name). Single ageless
resource kind — "We set fidelity 1 since it is not considered" — under one clock, the
per-commodity demand deadline (EDF/SJF). Aggregate per-node-pair COUNTS, no per-good
state. Clean exemplar of deadline-without-physics. Its three-buffer taxonomy (M/D/R) is
storage-location roles for one kind — do not let it be misread as a kind-split.
**Fence:** deadline-aware scheduling of entanglement requests over buffered memory is
OCCUPIED here; our deadline novelty is the TWO-date structure only.

### Chandra, Dai, Towsley — "Scheduling Quantum Teleportation with Noisy Memories," arXiv 2205.06300 (2022)
Citation verified. Physics-only mirror of ESDI: single clock (storage-time dephasing),
no deadline anywhere (even the future-work timeout is fidelity-derived). C2 PARTIAL:
LIFO-with-pushout reads ordinal queue recency — serve youngest, evict oldest — but no
custody identity, admission use, or cause-tagged loss (only discard cause is buffer
overflow; decoherence is never booked as a loss).
**Fence (hard):** freshness-favoring/youngest-first eviction for perishable quantum
state is PROVABLY OPTIMAL here (their Theorem 1). Never claim the discipline; claim the
object model. Cite this paper for the discipline.

### Fidelity-Age — Ercetin & Gedik, arXiv 2602.09562 (Feb 2026)
Citation verified; the most dangerous cell, and it took territory: the SDN controller
"observes ... the fidelity–age states of all stored pairs," keeps redundant stored
pairs, late-binds among them at slot time, enforces use-at-most-once. C1/C2 PARTIAL
accordingly. What it lacks: any second date (no demand deadline exists; FA is AoI-style
freshness), any cause taxonomy ("when the fidelity constraint makes a link unreliable,
its age term grows" — decohered and late made indistinguishable BY DESIGN), and any
kind beyond the physical pair. Layer note for §12: FA is network-layer scheduling
(entanglement distribution), not node-OS resource management.
**Fences (hard):** "first to read stored-pair age at decision time" and "first to
late-bind among redundant carriers" are UNSAFE — both occupied here.

### REPS — Zhao & Qiao, INFOCOM 2021 (secondary-sourced, see †)
C1 PARTIAL: genuine use-time selection — PFT/EPS provision redundant link-level
entanglements at planning time; ELS selects among the ones that SUCCEEDED, at
forwarding time. But redundancy is topological (aggregate throughput over flows), with
no one-good/N-carrier object, no custody state (selection reads counts and success
probabilities), no fidelity, no deadline (both added only by later work: fidelity by
Zhao/Zhao/Qiao's follow-up, deadlines by ESDI).
**Fence:** "late selection over redundant entanglement candidates" is conceded prior
art.

### Pre-distribution — Ghaderibaneh, Gupta, Ramakrishnan, Luo (Stony Brook, 2022)
Closest occupant of the outer provision-ahead shell: EPs stocked over pre-chosen
"super-link" node pairs ahead of demand, consumed by later requests. But binding is
PRECOMPUTED OFFLINE ("we already know the SL that we will use"), inventory is aggregate
spares against swap failure (1/p² stock), per-EP generation time is read only as a
binary usability cutoff, and no deadline exists. **Footnote 10 is the citable gift:**
they explicitly name runtime age-based selection as unexplored future work. Frame our
late-binding language against fn 10 directly — the claim is the kind-split semantics on
top of that named-open direction, not the direction itself.

### Repeater cutoffs — Iñesta, Vardoyan, Scavuzzo, Wehner, npj QI 2023 (arXiv 2207.06533)
C2 PARTIAL, three conjuncts short: state is ONE scalar per link (age, or −1; "we put
fidelity aside... via a constraint on the cutoff time" — fidelity compiled into a
pre-run constant, "not needed after that"); its only reader is the swap decision
(generation unconditional, discard automatic — no admission or consumption gate);
discards are silent resets, no loss ledger. Second date architecturally precluded (the
application enters only as a static Fmin folded into t_cut). **Citable gift:** they
name and DECLINE the richer custody model ("re-compute the age based on the post-swap
fidelity... would lead to a more complicated formulation") — the road we take is the
road they declined for MDP tractability.

### Entanglement buffering — Davies, Iñesta, Wehner, Quantum 8:1458 (2024; arXiv 2311.10052v3)
C1 PARTIAL but narrower than it looks: the split is presence-vs-QUALITY of a SINGLE
stored link (Availability A := 1−π∅; Average Consumed Fidelity F, both steady-state
t→∞ limits over the CTMC — population metrics no decision reads). No ensemble, no
selection at consumption ("if there is a stored link in memory G, it is immediately
used"), purify-vs-consume are independent stochastic streams (fixed probability q at
generation, Poisson consumption). The 2025 "multiple memories" follow-up (arXiv
2502.20240) is a FALSE FRIEND: multiplicity is generation-side feeding one store —
preempt with a footnote. **Quotable anti-pattern for C2:** their terminal transition
collapses consumption + purification-failure into ONE rate (µ + λq(1−p)).
**Warning:** their "availability" is defined almost in our vocabulary ("the probability
that a consumption request may be served at any given time") — §12 must draw the
presence-vs-recoverability line against this paper BY NAME.

### SeQUeNCe — Wu, Kolar, Chung et al., QST 6 (2021) 045027 (arXiv 2009.12000)
C2 PARTIAL: Memory Manager traces {raw/entangled/occupied, partner identity, fidelity,
coherence lifetime}; rule conditions read the state enum and counts, not fidelity/age
thresholds; expiry is a scheduled hard event whose handling just frees resources — no
cause-tagged ledger. **C3 PARTIAL — the strongest single prior-art point in the
matrix:** reservations carry an application start/end window, read at ADMISSION ("checks
whether sufficient local memory is available from the start time to the end time") — a
genuine second, non-physical date. It is enforced once at admission, never re-read at
consumption, and never reconciled against the coherence clock as a different KIND over
one good. Phrase C3 to survive this: co-enforcement at consumption + cause-tagged
losses, not "no second date exists anywhere." **Citable gift:** authentication atop the
reservation protocol is named as future work.

### QuISP / RuleSet — Satoh et al., IEEE QCE 2022 (arXiv 2112.07093); Matsuo, Durand, Van Meter, arXiv 1904.08605
One lineage with SeQUeNCe (its Resource Manager is explicitly "similar to the design of
QuISP") — count as one neighbor, not two. Per-qubit state is a time-evolved
per-error-channel probability vector π(t)=π(0)Q^t (richer exposure physics than a
fidelity scalar — but sampled lazily before operations, never read as a custody
timestamp by a rule). Rule clauses are counters and availability booleans
(Enough-Resource; "oldest available resource" FIFO is the strongest age signal); the
only clock is a 2-minute connection-level RuleSet timeout. Losses surface as aggregate
statistics. No institutional date. **Citation note: for per-pair rule state cite
Matsuo 1904.08605, not the QuISP paper.**

### Classical shelves (six) — credit list with canonical citations verified at first hand
Full form unoccupied classically; the halves exist separately:
- **AoI** (Kaul/Yates/Gruteser INFOCOM 2012; survey Yates et al. JSAC 2021): freshness
  as a single monitor-side scalar. ABSENT.
- **TTL caching** (Gwertzman & Seltzer ATC 1996; Cao & Liu IEEE TC 1998): per-entry age
  bound; no provenance at admission, no cause-tagged misses. ABSENT.
- **Perishable inventory / blood banks** (Nahmias OR 1982; Prastacos MS 1984): PARTIAL —
  owns the ACCOUNTING half: losses booked under two causes, outdating vs shortage, as
  aggregate policy. The classical ancestor of cause-tagged terminals.
- **Cold chain / pedigree** (Taoukis & Labuza 1989; WHO GDP TRS 957 2010; DSCSA 2013):
  PARTIAL — owns the CUSTODY half: the record travels with the good, inspected at
  handoffs; compliance regime, not a running scheduler.
- **Postponement** (Alderson 1950; Feitzinger & Lee HBR 1997): late binding's
  supply-chain form; design principle, no runtime record. ABSENT.
- **Real-time systems / RTDB temporal validity** (Buttazzo; Hamdaoui & Ramanathan 1995;
  Liu et al. 1991; **Ramamritham, Distributed and Parallel Databases 1993**): PARTIAL —
  owns the TWO-CLOCKS half: a data object's absolute validity interval is per-object
  and different-kinded from any transaction deadline. Differentiators: single avi
  scalar (no custody trail); objects REFRESHED IN PLACE by update transactions (our
  goods are non-refreshable; loss is terminal); staleness never booked as a cause.
  §12 sentence shape: we inherit RTDB's refusal to fold physical expiry into a job
  deadline and carry it where refresh is physically forbidden.
Citation cautions: Feitzinger & Lee page range varies by index (confirm from HBR);
Alderson 1950 is a trade publication (cite via Bucklin 1965 / Zinn & Bowersox 1988 if a
peer-reviewed venue is wanted).

## The two-dates test across the board (a §12 organizing device)

Seven distinct ways of not holding two dates, one per system — the separation is not
the field default from ANY direction:
1. ESDI: deadline only; physics vacated (fidelity := 1).
2. Chandra et al.: physics only; no deadline exists.
3. QOS: both present, commensurated into one scheduler scalar.
4. QNodeOS: physics only, and only as a post-hoc dataset filter.
5. Fidelity-Age: physical quality folded into a freshness scalar; no deadline.
6. Deadline-aware DQC (arXiv 2512.06157, sweep foil): both present; physical budget
   collapsed to a static depth limit.
7. SeQUeNCe: both present, different kinds — but the institutional window is
   admission-only, never co-enforced at consumption, losses untagged.

## The unoccupied core (what §12 may claim, in fenced form)

1. **The four-kind ontology.** The warrant — a classical credential whose own validity
   decays — is unoccupied in EVERY cell; nothing in this literature has a
   security/credential dimension on the managed good at all. The claim (right to
   materialize one good from N carriers) exists nowhere as a represented object.
   Encrypted-cloning primitives are an active 2026 physics literature (2604.10155,
   2606.06552, 2604.04888, 2605.26866) with NO OS semantics on top — claim the OS
   framing as open, citing them as the raw material. One-shot tokens/quantum money are
   the crypto rhyme of claim+gate, never an OS resource kind.
2. **Custody with cause-tagged terminals.** Age-reading is occupied (cutoffs, FA,
   LIFO-pushout); exposure-HISTORY beyond scalar age, admission+consumption as the
   readers, and losses booked by true cause are unoccupied — and two neighbors are the
   explicit opposite (FA folds fidelity failure into age; buffering collapses two loss
   causes into one rate).
3. **Two dates co-enforced.** Fenced against SeQUeNCe's admission-only window and
   RTDB's refreshable temporal validity, per above.

## Unsafe-phrasings register (each occupied; never print as ours)

- "freshness-favoring / youngest-first eviction improves outcomes" → Chandra Thm 1.
- "reads stored-pair age at decision time" → Fidelity-Age; cutoffs.
- "late binding / selection among redundant candidates" → FA; REPS ELS.
- "provision ahead of demand, bind to requests later" → Ghaderibaneh (and fn 10 names
  runtime age-selection as the next step).
- "presence tracked separately from quality" → Davies availability vs consumed fidelity.
- "a second, institutional date in a quantum system" → SeQUeNCe reservation window.
- "coherence-aware scheduling" → QNodeOS (policy-level); "models time-decay" → QOS ed(t).
- "deadline-aware scheduling of entanglement" → ESDI.
- perishability premise as such → occupied everywhere; it is the field's shared premise.

## Corrections applied same-day

- Draft §2 QNodeOS sentence repaired: min-fidelity request re-attributed to the link
  layer (Dahlberg et al., SIGCOMM 2019); "so that live qubits do not wait" replaced
  with the verified mechanism (QNPU-local scheduling avoids ADDING classical
  round-trips; the live qubit still waits ~4.8 ms and that wait dominates infidelity —
  which STRENGTHENS the paragraph's point).
- Author list corrected before first print: repeater-cutoffs paper is Iñesta,
  Vardoyan, Scavuzzo, Wehner (the sweep's "Iñesta & Elkouss" was wrong; caught by the
  line-level upgrade).
- REPS first author is Yangming Zhao (not Yiming).

## Bounds of this matrix

- REPS: secondary-sourced (see †). Upgrade via institutional IEEE access when convenient.
- Neighbors sweep bounds, disclosed by its reader: patents triaged but not assessed;
  non-English/non-US venues not covered; purification-scheduling decision literature
  triaged only; fidelity-guarantee routing papers (2111.07764, 2605.00246, 2407.09171)
  judged not-close from abstracts.
- Watch-list (not cells; nothing we print rests on them): Chakraborty/Rozpedek/
  Dahlberg/Wehner 2019 virtual-link routing (touches only already-conceded territory);
  RTDB update-transaction scheduling successors (Xiong/Ramamritham line) — the one
  place a reviewer might hunt for a classical full-form occupant; QuISP RuleSet
  implementation internals beyond the two papers read.
- Sociological note for the ask channel: three of the closest neighbors (QNodeOS,
  buffering, cutoffs) are Wehner-group work — the people most likely to review this
  paper already own the nearest territory; §12's precision about their work is not
  optional politeness, it is survival.

## Gate disposition

Sprint item (a) of c1a393c is DISCHARGED. The perishability premise is confirmed
occupied territory (as the disposition presumed); the presence-vs-recoverability split,
the custody-with-cause-tagged-terminals record, and the two-date co-enforcement are
unoccupied in everything read, with per-system fences recorded above. §12 drafting may
proceed against this matrix; every "no prior system" sentence must use the fenced forms
and check the unsafe-phrasings register. Remaining print gate: the CITATION PASS on the
matrix's own bibliographic details marked above (REPS full text; Feitzinger & Lee pages).
