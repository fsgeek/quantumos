# HotOS Typed Entanglement Contracts Paper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a compact HotOS-shaped paper showing that fidelity is not a sufficient resource type for heterogeneous entanglement and proposing the minimum contract needed to expose non-substitutable offers.

**Architecture:** Open with one request and three non-dominating offers, derive a provisional typed contract from four counterexamples, walk one request through the contract using the exact `hedged-stage1` enumeration, and end with falsifying systems questions. Import the two-dates distinction and physicist-paper evidence by reference; do not reproduce that paper's method, seven questions, or full qsim battery.

**Tech Stack:** Markdown manuscript; exact JSON/CSV enumeration artifacts; local physics and systems references; code-native figure specifications; `scripts/check_number_provenance.py`.

## Global Constraints

- Source skeleton: `docs/drafts/2026-08-18-hotos-typed-contracts-skeleton.md`.
- Destination manuscript: `docs/drafts/2026-08-18-hotos-typed-contracts-draft.md`.
- Working title: `Fidelity Is Not a Type: Resource Contracts for Heterogeneous Quantum Computers`.
- The paper owns typed offers/demands, carrier/claim/warrant/settlement/terminal/custody semantics, the three-offer scenario, single-machine OS boundary, and selective-reclamation consequence.
- It imports expiry versus appointment, the topology failure experiment, and maintenance evidence from the physicist paper without re-deriving them.
- The exact enumeration exercises plural placement and stranded-carrier accounting only; it does not validate the complete runtime.
- A stranded carrier may be locally indistinguishable from useful stock, so selective reclamation is ledger-driven; do not claim all reclamation is otherwise impossible.
- Laser-, LED-, and sunlight-pumped generation are landscape evidence, not costed commercial offers.
- “Six-page shape” is a composition constraint until the 2027 HotOS format is officially announced.
- Preserve ignored-draft policy: do not force-add `docs/drafts/`.

---

### Task 1: Establish the Six-Section Argument and Claim Boundary

**Files:**
- Create: `docs/drafts/2026-08-18-hotos-typed-contracts-draft.md`
- Reference: `docs/drafts/2026-08-18-hotos-typed-contracts-skeleton.md`
- Reference: `docs/drafts/2026-08-10-decision-docket.md`

**Interfaces:**
- Consumes: the ruled split and accepted HotOS ownership map.
- Produces: a complete six-section scaffold with an author-only claim ledger.

- [ ] **Step 1: Create the manuscript scaffold**

Create these headings in order: `Three Offers, No Dominant Choice`; `Why the Familiar Resource Tuple Fails`; `A Provisional Typed Contract`; `Walk the Request`; `Where the OS Goes`; `Questions That Could Kill This Design`. Add `Evidence and Non-Claims` and `Methodology and Artifacts` as compact end matter rather than peer argumentative sections.

- [ ] **Step 2: Add an author-only ownership note**

List claims owned here, claims imported from the physicist paper, and prohibited duplicate arguments. Mark the note for deletion before release.

- [ ] **Step 3: Verify the two front doors differ**

Run:

```bash
rg -n "lettuce|three offers|fidelity is not a type|seven questions" docs/drafts/2026-08-18-hotos-typed-contracts-draft.md
```

Expected: no lettuce tale and no seven-question method; the three-offer opener and provocation are present.

### Task 2: Construct the Counterexample Before the Ontology

**Files:**
- Modify: `docs/drafts/2026-08-18-hotos-typed-contracts-draft.md`
- Reference: `docs/references/2602.10695v1.txt`
- Reference: `docs/references/2026 Generating quantum entanglement from sunlight.txt`

**Interfaces:**
- Consumes: three motivating offer constructions and four non-substitutability dimensions.
- Produces: Sections 1–2, which establish need before naming the proposed kinds.

- [ ] **Step 1: Write one request and three offers**

Give the request an operation, endpoints, fidelity floor, deadline, and risk bound. Present a quickly decaying early offer, a longer-lived offer with a different generation-time distribution, and a plural encrypted claim with late site choice, one-use authorization, and residue. Describe the first two as constructions; do not attach measured prices or claim that they are products.

- [ ] **Step 2: Show why no scalar order is safe**

Use four counterexamples: operation/endpoint incompatibility; decay or generation-time risk; carrier versus redeemable ensemble with at-most-once exercise; terminal and reclamation obligations. State that a scheduler may compute a scalar score after type checking, but may not erase fields required for enforcement or accounting.

- [ ] **Step 3: Import rather than re-derive adjacent evidence**

Cite expiry versus appointment as one contract dimension. Cite the physicist paper's crash/absence/silence result as evidence that topology decisions need a map; argue here only that endpoints and topology belong in the contract.

- [ ] **Step 4: Run the speculation gate**

Run:

```bash
rg -n "cheap|costly|standing cost|commercial|facility-level|LED|sunlight|laser" docs/drafts/2026-08-18-hotos-typed-contracts-draft.md
```

Expected: `cheap` and `costly`, if retained, are declared scenario assumptions; source modalities carry no inferred facility economics.

### Task 3: Define the Minimum Typed Contract

**Files:**
- Modify: `docs/drafts/2026-08-18-hotos-typed-contracts-draft.md`
- Create: `docs/drafts/2026-08-18-hotos-figure-specs.md`

**Interfaces:**
- Consumes: the counterexamples from Task 2.
- Produces: the exact kind definitions, offer/demand fields, and lifecycle figure used in Tasks 4–6.

- [ ] **Step 1: Define six kinds without claiming finality**

Define carrier, claim, warrant, settlement, terminal, and custody record. Make terminal a cause-tagged event/state transition. State which identities and state each kind must preserve, and identify which separations remain conjectural.

- [ ] **Step 2: Define offer and demand fields**

Offer fields: resource kind; compatible operations; endpoints/topology; generation-time distribution; quality estimate and uncertainty; decay model; exercise cardinality; maintenance obligations; terminal/reclamation semantics. Demand fields: operation; acceptable kinds; endpoints/topology; quality floor; deadline; risk bound.

- [ ] **Step 3: Ground maintenance conditionally**

If publication order and anonymity permit, cite the physicist paper's maintenance-dominance result. Otherwise cite the shared qsim artifact as motivation without restating the percentage and without making maintenance evidence a HotOS result.

- [ ] **Step 4: Specify the load-bearing lifecycle figure**

In `docs/drafts/2026-08-18-hotos-figure-specs.md`, specify producer offers → broker/admission → custody → warrant validation and control-path reservation → settlement/consumption → cause-tagged terminal → reclamation. Label the state read and state written at each transition.

- [ ] **Step 5: Check vocabulary consistency**

Run:

```bash
rg -n "carrier|claim|warrant|settlement|terminal|custody record|offer|demand" docs/drafts/2026-08-18-hotos-typed-contracts-draft.md
```

Expected: every kind is defined before the request walk; `terminal` is a transition, not merely a custody-record field.

### Task 4: Walk the Request and Exercise One Distinction

**Files:**
- Modify: `docs/drafts/2026-08-18-hotos-typed-contracts-draft.md`
- Reference: `runs/hedged-stage1/summary.json`
- Reference: `runs/hedged-stage1/controls.json`
- Reference: `runs/hedged-stage1/manifest.json`
- Reference: `runs/hedged-stage1/survival.csv`
- Reference: `runs/hedged-stage1/quality.csv`
- Reference: `docs/superpowers/specs/2026-07-15-hedged-stage1-run-note.md`

**Interfaces:**
- Consumes: the contract definitions and exact enumeration artifacts.
- Produces: one end-to-end request walk and the paper's only original numerical evidence.

- [ ] **Step 1: Walk the request through each transition**

At offer publication, admission, custody, settlement, consumption, terminal recording, and reclamation, state the decision, fields read, possible refusal, and ledger update. Show one point where fidelity-only admission chooses an incompatible offer or must reconstruct erased information.

- [ ] **Step 2: Interpret the exact enumeration narrowly**

Use `hedged-stage1` only to establish that late binding among plural carriers has option value on declared cells and that exercise leaves a key/residue tax elsewhere. Name the modeled assumptions and do not extrapolate to a production scheduler.

- [ ] **Step 3: State the selective-reclamation consequence**

Explain that a stranded carrier may be locally physically indistinguishable from useful stock. Therefore the custody ledger is required for safe selective reclamation. Explicitly concede that indiscriminate reset remains possible.

- [ ] **Step 4: Keep three evidence classes visible**

Mark plural-placement enumeration as exercised; encrypted cloning and source heterogeneity as external demonstrations or landscape signals; coexistence under one runtime as architectural conjecture.

- [ ] **Step 5: Gate numerical provenance**

Run:

```bash
python scripts/check_number_provenance.py docs/drafts/2026-08-18-hotos-typed-contracts-draft.md
```

Expected: `0 unregistered numeric claim(s)`.

### Task 5: Establish the OS Boundary and Falsification Surface

**Files:**
- Modify: `docs/drafts/2026-08-18-hotos-typed-contracts-draft.md`
- Reference: `docs/references/2021-the-last-cpu.txt`
- Reference: `docs/references/QOS-OSDI-2025.txt`
- Reference: `docs/references/Qibolab_an open-source hybrid quantum operating system.txt`

**Interfaces:**
- Consumes: the typed request walk and relevant systems architectures.
- Produces: Sections 5–6 and the final provocation.

- [ ] **Step 1: Draw the runtime boundary**

Describe self-managing quantum subsystems publishing offers and local constraints, a real-time broker admitting and binding work, a fast control path, and a supervisory model/policy plane. Argue that the OS contract coordinates these layers; do not imply one central executable owns all mechanisms.

- [ ] **Step 2: State why adjacent layers are insufficient**

Link layers manufacture resources, controllers expose telemetry, and compilers request capabilities. The coordinating runtime is the locus that jointly sees operation, deadline, topology, competing offers, custody, and terminal accounting. Compare this division directly with the architectural lesson of *The Last CPU*.

- [ ] **Step 3: Write five kill questions**

Ask whether existing interfaces already capture operation and topology; claim/carrier can always remain fused; a warrant is only an ACL; a scalar can preserve every enforcement and attribution obligation; and heterogeneous offers coexist long enough for runtime choice. Phrase each so a negative answer can remove a proposed kind or collapse the design.

- [ ] **Step 4: Keep federation hostile and brief**

Use one paragraph only: if the contract is needed inside one trusted machine, administrative boundaries make omitted fields contested. Do not introduce markets, pricing protocols, trust mechanisms, or a federation architecture.

- [ ] **Step 5: Land the closing sentence**

Make the final substantive sentence: `The operating system exists because something must hold promises against physics.`

### Task 6: Fit, Overlap, and Review Gates

**Files:**
- Modify: `docs/drafts/2026-08-18-hotos-typed-contracts-draft.md`
- Modify: `docs/drafts/2026-08-18-hotos-figure-specs.md`
- Compare: `docs/drafts/2026-08-18-physicist-question-interface-draft.md` if present

**Interfaces:**
- Consumes: the complete HotOS-shaped draft.
- Produces: a structurally reviewable paper that neither overstates its evidence nor duplicates the physicist paper.

- [ ] **Step 1: Specify the second figure**

Define a three-offer plot with axes for operation compatibility, endpoint/topology compatibility, availability-time risk, decay, exercise cardinality, and reclamation obligation. Do not use a single aggregate utility axis and do not attach empirical prices to the motivating constructions.

- [ ] **Step 2: Run the composition-budget gate**

Run:

```bash
wc -w docs/drafts/2026-08-18-hotos-typed-contracts-draft.md
rg -n '^## |^### ' docs/drafts/2026-08-18-hotos-typed-contracts-draft.md
```

Expected: approximately 3,500–4,500 prose words, six argumentative sections, and compact end matter. Treat this as a six-page composition test, not an announced HotOS limit.

- [ ] **Step 3: Run the overclaim gate**

Run:

```bash
rg -n "ledger-driven or impossible|proves|production scheduler|measured economics|federated market|future machine" docs/drafts/2026-08-18-hotos-typed-contracts-draft.md
```

Expected: no absolute reclamation claim, no production validation claim, and federation confined to the hostile closing paragraph.

- [ ] **Step 4: Run the overlap audit**

If the physicist draft exists, compare both abstracts, openings, headings, evidence tables, and conclusions. Expected: no shared tale; the two-dates method is cited rather than taught here; the qsim battery remains in the physicist paper; typed contracts are defined only here; `hedged-stage1` is interpreted fully only here.

- [ ] **Step 5: Repeat the provenance gate**

Run:

```bash
python scripts/check_number_provenance.py docs/drafts/2026-08-18-hotos-typed-contracts-draft.md
```

Expected: `0 unregistered numeric claim(s)`.

- [ ] **Step 6: Stop at the structural review gate**

Deliver the draft, two figure specifications, word count, provenance output, and overlap audit. Do not perform a voice pass or format for a venue until the argument survives this review and the official 2027 HotOS call is available.
