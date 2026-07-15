# Hedged-placement Stage 1: deciding-run note

**Date:** 2026-07-15
**Status:** DECIDING RUN EXECUTED. The c1a393c gate (paper drafting gated on
the validation sprint) is discharged by this run.
**Provenance:** preregistration ca26217 (OTS-stamped, byte-identical at run
time); implementation commit 8549730 (stamped via 5b8a936, which is the
manifest's recorded HEAD); module sha256 0309189e…76ba5e0; artifacts in
`runs/hedged-stage1/` (local, gitignored per repo convention): manifest.json,
controls.json, survival.csv (1,620 rows), quality.csv (540 rows),
summary.json. Enumeration is exact and deterministic; a valid rerun is
byte-identical.

## Battery readings

All eight synthetic controls passed before the grids were evaluated.
Probability balance held within 4.5e-16 everywhere (budget 1e-12). No
NUMERIC_INVALID, no PROBABILITY_IMBALANCE.

- **SITE_CHOICE_DECISION_EARNED.** 1,296 of 1,620 survival cells activated;
  every activated cell labels POSITIVE (Delta_M from +0.0164 to +0.384, all
  at or above epsilon_M = 0.01). The 324 refusals are exactly the
  (rho_c, rho_l) = (1,1) fully-common-mode block, refused
  CHANNEL_SILENCED.CARRIER: when all sites live or die together there is
  nothing to choose between, and the instrument says so rather than reporting
  a null.
- **QUALITY_CHOICE_DECISION_EARNED.** 270 of 540 quality cells activated;
  every activated cell labels QUALITY_POSITIVE (V_Q from +0.0100 to +0.120).
  Refusals: 180 cells at rho_q = 1 (CHANNEL_SILENCED.QUALITY — flat
  within-world quality) and 90 at a_1 = 0.5 (CHANNEL_SILENCED.INFORMATION —
  uninformative late signal). Both boundaries behaved exactly as
  preregistered: neither may support a quality verdict, and neither did.

## Region-map highlights (exact values, authored model)

- Largest site-choice option value Delta_M = +0.384 at p_c = 0.8, p_l = 0.5,
  q_k = 1, a_e = 1, independent hazards — the path-scarce corner. Late
  binding pays most when transient path availability, not carrier survival,
  is the binding constraint.
- Smallest activated Delta_M = +0.0164 at g = 0.10, q_k = 0.9, common-mode
  carriers: catastrophe and key fragility compress the option value by an
  order of magnitude without erasing it anywhere in the activated envelope.
- Largest quality option value V_Q = +0.120 in the balanced-common profile
  (rho_c = rho_l = 1) with perfect late signal and delta_clone = 0.2. The
  complementarity is structural: full common-mode kills the survival channel
  (sites never differ in availability) while producing the cleanest quality
  stratum (all sites jointly alive, so choice is purely about quality).
- Shared-penalty invariance held in the deciding grid as in the control:
  delta_clone moves absolute plural quality, never selection, Delta_M, or
  V_Q.

## The third deciding question: fragility and structural cost (no verdict)

Per the prereg, plural-versus-single receives no binary label; the profile:

- Among the 1,296 activated survival cells, late-bound accepted delivery
  exceeds single in 1,208; single exceeds late in 88; no ties. All 88
  single-wins occur at q_k < 1; with a certain key (q_k = 1, g = 0) single
  never beats late-bound.
- The worst plural deficit is −0.210, at q_k = 0.9 with abundant sites
  (p_c = p_l = 0.95, a_e = 1): the all-required key completes with
  probability 0.729, and when individual sites rarely fail, hedging buys
  little while the key tax is charged in full. The key tax localizes exactly
  where the option is least needed.
- Structural coordinates (counts, not utilities): plural allocates 3
  carriers + 3 key qubits vs 1 + 0, one construction call, 4 decryption
  participants vs 1, residue 5 vs 0 after materialization; expected
  forced-cleanup load on no-materialization worlds ranges up to ~3.5 qubits
  per episode in the tested envelope.

## Allowable inference (§10, restated as read)

In the exact authored three-clone model, late binding has a material positive
accepted-delivery region under the declared site, key, path, and observation
envelope — in this run, the positive region is the entire activated envelope.
The quality selector has value only in the reported survivor and information
regimes; sparse survivors, flat quality, and uninformative estimates were
refused, not counted as nulls. The option region coexists with the
separately reported direct-key fragility (88 cells where the single stored
carrier wins outright) and the structural resource costs above.

Not claimed, per prereg: hardware probabilities or fidelities, deployment
value, exercise timing, retry/probe/concurrency behavior, any scalar net
benefit, or "late binding improves physical recoverability" (the two plural
arms share physical histories; late binding captures recoverability, it does
not create it).

## Process disclosure

The pre-run conformance review (independent fresh-context agent) found no
blocking discrepancies and two minor battery-index findings, fixed test-first
before the implementation commit. The reviewer, not instructed to refrain,
executed the deciding grids during its review and reported summary-level
results before the deciding run. The implementation was frozen before that
preview; the only post-preview changes were the two review-mandated label
fixes, which cannot move any recorded quantity; enumeration is deterministic.
Recorded here so the run record carries the breach. Future review prompts
must explicitly license only the eight synthetic controls.

## What this unlocks

The validation sprint named by the Codex-review disposition (c1a393c) is
executed: the hedged-placement mechanism is DECISION-EARNED in both channels
of its authored model, with its fragility boundary mapped. Paper drafting
against the committed skeleton is no longer gated on this run. Stage 1's
earned-claim scope (review round 2, fbed873) applies to any use of these
results in the draft.
