# Physicist Question Interface Paper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a self-contained physicist-facing manuscript that turns modeled quantum-systems uncertainties into seven bounded measurement questions without claiming that the simulator predicts future hardware.

**Architecture:** Build a new manuscript from the accepted physicist-interface skeleton while leaving the combined 2026-08-16 reading copy unchanged as source material. The argument flows from the repaired two-dates invariant, through a decision-to-measurement method and an explicit evidence contract, into four decision surfaces, one bounded model break, and seven questions. Numerical claims remain attached to `docs/number-provenance.json` and their run artifacts.

**Tech Stack:** Markdown manuscript; qsim run artifacts; `scripts/check_number_provenance.py`; local PDF/text references; Markdown tables and code-native figure specifications.

## Global Constraints

- Source skeleton: `docs/drafts/2026-08-18-physicist-interface-paper-skeleton.md`.
- Source manuscript: `docs/drafts/2026-08-16-stage2-reading-copy.md`; do not overwrite it.
- Destination manuscript: `docs/drafts/2026-08-18-physicist-question-interface-draft.md`.
- The paper owns the two-dates test, decision-to-measurement method, qsim evidence and refusals, invariant argument, tale translation, and seven questions.
- The paper does not own the full carrier/claim/warrant/settlement ontology or the claim that fidelity is not a type.
- Say that physics supplies degradation while applications and institutions supply thresholds, appointments, and enforcement; do not say physics alone supplies one complete death.
- Distinguish physical constraints, operational consequences, accounting rules, design hypotheses, instrument findings, and external demonstrations by name.
- Do not infer source price, standing cost, facility-level fidelity, or production economics from the sunlight/LED/laser literature.
- Preserve ignored-draft policy: do not force-add `docs/drafts/`; use the project's existing publication and timestamp workflow when the author selects a release candidate.
- Target 9,000–10,500 prose words before voice calibration.

---

### Task 1: Establish the New Manuscript and Ownership Ledger

**Files:**
- Create: `docs/drafts/2026-08-18-physicist-question-interface-draft.md`
- Modify: `docs/drafts/2026-08-10-decision-docket.md`
- Reference: `docs/drafts/2026-08-18-physicist-interface-paper-skeleton.md`

**Interfaces:**
- Consumes: the accepted section spine and claim-ownership decisions.
- Produces: an empty but complete manuscript skeleton and an updated docket that later tasks can populate without reopening the split.

- [x] **Step 1: Record the split in the docket**

Add a dated entry stating: split ruled 2026-08-18; physicist paper owns the two-dates method, invariant argument, eight-row tale translation with epistemic labels, instrument evidence, and seven questions; HotOS owns typed contracts and the earned closing sentence; the combined-paper title remains unassigned until abstracts can be compared.

- [x] **Step 2: Create the manuscript scaffold**

Create these headings in order: `A Tale of Two Dates`; `How an Unknown Earns Representation`; `The Instrument and Its Evidence Contract`; `Four Decision Surfaces` with four named subsections; `One Model Break, Bounded`; `Earned, Refused, and Owed`; `Related Work and the Negative Envelope`; `Methodology and Provenance`. Copy the skeleton's working claim and explicit non-claims into an author note at the top, marked for deletion before release.

- [x] **Step 3: Verify ownership is explicit**

Run:

```bash
rg -n "two-dates|carrier/claim/warrant/settlement|fidelity is not a type|title remains" docs/drafts/2026-08-18-physicist-question-interface-draft.md docs/drafts/2026-08-10-decision-docket.md
```

Expected: the two-dates ownership and title deferral appear; typed-contract language appears only in the non-ownership note.

- [x] **Step 4: Checkpoint**

Review the scaffold against every heading in the accepted skeleton. Do not force-add the ignored draft or docket.

### Task 2: Write the Tale, Repaired Invariant, and Question-Generation Method

**Files:**
- Modify: `docs/drafts/2026-08-18-physicist-question-interface-draft.md`
- Reference: `docs/drafts/2026-08-16-stage2-reading-copy.md:33`

**Interfaces:**
- Consumes: the mono-costume tale, two-dates distinction, and question-generation rules.
- Produces: Sections 1–2 and the conceptual vocabulary used by every result subsection.

- [x] **Step 1: Draft the shortened lettuce tale**

Retain one costume only. End the tale with the distinction between predicted physical suitability and institutional appointment, plus the pre-generation rule that an unclaimed good has no demand appointment. Remove any sentence implying that either date alone is a complete physical or institutional death.

- [x] **Step 2: Redesign the first half of the eight-row translation**

Seat decay, two dates, harm from reading, and maintenance after the tale. Give each row four columns: tale observation; quantum referent; epistemic status; decision exposed. Use only `physical constraint` or `operational consequence` in this first table segment.

- [x] **Step 3: State the decision-to-measurement chain**

Define the recurring sequence exactly once: physical uncertainty → runtime decision → signal available to the decision → threshold at which the decision changes → probe and cost → freshness bound. Include both rules: every represented quantity names the decision that reads it; every experimental decision declares every signal it reads, including selection rules.

- [x] **Step 4: Seat the seven-question index**

Use columns `Q`, `physicist-facing question`, `decision informed`, and `where earned`. Keep seven questions; Q8 remains outside this paper's instrument-earned set.

- [x] **Step 5: Run the vocabulary gate**

Run:

```bash
rg -n "physics supplies.*death|institution.*death|resource kinds invalidate|universal constant" docs/drafts/2026-08-18-physicist-question-interface-draft.md
```

Expected: no categorical physics-supplies-death sentence and no HotOS resource-kind claim; any `universal constant` occurrence explicitly rejects that interpretation.

### Task 3: Write the Instrument Contract and Four Decision Surfaces

**Files:**
- Modify: `docs/drafts/2026-08-18-physicist-question-interface-draft.md`
- Modify only if required by a new literal: `docs/number-provenance.json`
- Reference: `runs/t1-control/f230668e-3fbd-4016-bd7a-e7bac2e47688/analysis/t1_report.json`
- Reference: `runs/t1-open/94fc5e58-a906-4ecf-af7e-9ac681bfa573/analysis/t1_report.json`
- Reference: `runs/t1-open/94fc5e58-a906-4ecf-af7e-9ac681bfa573/analysis/t3_report.json`
- Reference: `runs/sweep-s1-attempt-price/dose_response.json`
- Reference: `runs/sweep-s2-attempt-price/policy_by_spread_interaction.json`
- Reference: `runs/seed-battery/seed_battery_analysis.json`

**Interfaces:**
- Consumes: the decision-to-measurement chain and existing authored-model artifacts.
- Produces: Sections 3–4, with every number classified and traceable.

- [x] **Step 1: State the evidence hierarchy before results**

Define five classes: authored-model finding; exact enumeration; refusal; physically demonstrated capability; unanswered hardware quantity. State that preregistration and timestamping establish chronology and auditability, not hardware truth.

- [x] **Step 2: Describe only the instrument features needed by the questions**

Cover switched photonic modules, stochastic heralding, perishable inventory, contention, deadlines, decoder service, and typed terminal accounting. Remove construction chronology unless it changes the evidence class.

- [x] **Step 3: Draft the manufacture and maintenance surface**

Organize Q1/Q4/Q6 as uncertainty → decision → result → threshold → measurement. Include maintenance dominance, the retry spiral, and low/high attempt-price regimes. Put each percentage beside its artifact and state `authored-model finding`, not measured hardware property.

- [x] **Step 4: Draft quality, observability, and topology surfaces**

For Q2/Q7, retain the decision-available quality spread and degenerate-dominated refusal. For Q3, separate proxy readability, back-action, and binary versus budgeted wear. For Q5, keep link concurrency, radix, reconfiguration granularity, and the crash/absence/silence signatures; do not argue typed heterogeneous offers here.

- [x] **Step 5: Gate numeric provenance**

Run:

```bash
python scripts/check_number_provenance.py docs/drafts/2026-08-18-physicist-question-interface-draft.md
```

Expected: `0 unregistered numeric claim(s)`. If a new literal is necessary, add an entry with its exact artifact and honest status; otherwise rewrite or delete it.

### Task 4: Bound the Model Break and Account for Debts

**Files:**
- Modify: `docs/drafts/2026-08-18-physicist-question-interface-draft.md`
- Reference: `docs/references/2602.10695v1.txt`
- Reference: `docs/references/2026 Generating quantum entanglement from sunlight.txt`
- Reference: `runs/hedged-stage1/summary.json`

**Interfaces:**
- Consumes: the strict no-copy assumption, encrypted-cloning demonstration, and instrument refusal discipline.
- Produces: Sections 5–6 without importing the HotOS ontology.

- [x] **Step 1: Write encrypted cloning as one bounded model break**

Contrast the original one-carrier assumption with late site choice, one-use authorization, and stranded residue. Introduce only enough vocabulary to state which decisions and measurements become necessary. Refer readers to the separate typed-contract paper for the full structure.

- [x] **Step 2: Seat the four younger translation rows**

Add splitting, waybill, wilting, and clerk. Label each separately as external physical capability, accounting consequence, proposed mechanism, or instrument finding. Do not call all four laws of physics.

- [x] **Step 3: State landscape signals conservatively**

Use laser-, LED-, and sunlight-pumped entanglement only as evidence that source properties may vary. State explicitly that the cited work does not license integrated price, standing-cost, or facility-level substitutability claims.

- [x] **Step 4: Build the evidence/debt table**

Use columns `finding or question`, `evidence class`, `decision affected`, `artifact or reference`, and `claim not licensed`. Divide debts into unanswered physics, instrument limitations, and unadmitted conjectures. State prominently that qsim does not exercise warrants or settlement under contention.

- [x] **Step 5: Verify ontology depth**

Run:

```bash
rg -n "carrier|claim|warrant|settlement|typed offer|typed demand" docs/drafts/2026-08-18-physicist-question-interface-draft.md
```

Expected: carrier/claim/warrant/settlement appear only in the bounded model-break explanation, debt statement, or cross-paper pointer; no typed offer/demand design is developed.

### Task 5: Close the Argument and Preserve Methodological Candor

**Files:**
- Modify: `docs/drafts/2026-08-18-physicist-question-interface-draft.md`
- Reference: `docs/drafts/2026-08-16-stage2-reading-copy.md:1141`
- Reference: `docs/drafts/2026-08-16-stage2-reading-copy.md:1294`

**Interfaces:**
- Consumes: the repaired invariant, related-work classifications, and docket #12.
- Produces: Sections 7–8 and the paper's closing sentence.

- [x] **Step 1: Classify related systems without retroactive obligations**

Apply the two-dates test as a classification. Distinguish systems outside the paper's scope from systems that represent only one constraint; do not call either category a failure unless it claims the omitted obligation.

- [x] **Step 2: State the repaired invariant**

Argue that physics supplies degradation while applications and institutions supply thresholds, appointments, and enforcement. Retain “a ledger physics cannot see” as the compact expression of why a resource model cannot be derived from physics alone.

- [x] **Step 3: Preserve the verified part of docket #12**

Keep the Kimi K2.6 cross-vendor transport-test fact at the resolution the records support: six generated tales were decoded blind by Kimi K2.6 (Moonshot AI), a different vendor and training lineage, given no laws, protocol, or repository. State that the tale inputs and protocol are public verbatim, the decode is a labeled condensation of a fuller session record, and the failed replication is documented in the repository. Do not call the lettuce seed one of six generated costumes or claim that the complete records and failed replication are published verbatim at the public URL. Move extended workflow narration to the linked record.

- [x] **Step 4: Land the closing claim**

Make the final substantive sentence: `The product is falsifiable questions for the owners of hardware numbers.` No later paragraph may reopen the ontology or add a stronger hardware claim.

### Task 6: Build Figures and Run the Manuscript Gates

**Files:**
- Create: `docs/drafts/2026-08-18-physicist-figure-specs.md`
- Modify: `docs/drafts/2026-08-18-physicist-question-interface-draft.md`
- Compare: `docs/drafts/2026-08-18-hotos-typed-contracts-draft.md` if present

**Interfaces:**
- Consumes: the completed argument and artifact map.
- Produces: four unambiguous figure specifications and a reviewable physicist-paper draft.

- [x] **Step 1: Specify four figures**

Write exact labels, nodes, axes, data sources, captions, and prohibited inferences for: one-good lifecycle with physical and institutional tracks; question-generation chain; Q1/Q4/Q6 economy charts; Q5 custody/topology map with crash/absence/silence signatures.

- [x] **Step 2: Check structural budget**

Run:

```bash
wc -w docs/drafts/2026-08-18-physicist-question-interface-draft.md
rg -n '^## |^### ' docs/drafts/2026-08-18-physicist-question-interface-draft.md
```

Expected: 9,000–10,500 words and the accepted section order.

- [x] **Step 3: Repeat the provenance gate**

Run:

```bash
python scripts/check_number_provenance.py docs/drafts/2026-08-18-physicist-question-interface-draft.md
```

Expected: `0 unregistered numeric claim(s)`.

- [x] **Step 4: Run the cross-paper ownership gate**

If the HotOS draft exists, compare abstracts, opening scenarios, full section headings, and closing sentences. Expected: lettuce appears only here; full typed-contract definitions appear only in HotOS; the two-dates argument is derived only here; each paper has a different final substantive sentence.

- [x] **Step 5: Audition titles only after the abstract exists**

Compare the current combined-paper title against at least one title naming questions, measurements, or model breakage. Keep “The Cold Chain: What a Quantum Operating System Actually Manages” unassigned unless the physicist abstract—not the tale alone—earns it.

- [x] **Step 6: Stop at the structural review gate**

Deliver the draft, figure specifications, word count, provenance output, and overlap audit for author reaction. Do not begin the final voice pass until this structure is accepted.
