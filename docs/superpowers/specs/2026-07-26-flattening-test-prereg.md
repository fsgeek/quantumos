# Flattening-test preregistration: does a correctly-sited layer flatten the residual structure beneath it?

**Date:** 2026-07-26
**Status:** PREREGISTERED, not yet computed. Registered before any outcome
value in the data was read (exposure disclosed below).
**Register:** practice-grade per the standing qsim discipline — this is an
exploratory instrument, not the second simulator. The prereg exists because
the bet is directional and the data already exists, which is exactly the
condition under which post-hoc reading is cheapest to disguise.

## Provenance of the question

Tony's storage intuition, recorded in the 2026-07-25 handoff ("What the Fence
Was For"): *a correctly-sited layer flattens the residual structure beneath
it.* The handoff named this the most fun thing on the board and left it
undone. Tony, on 2026-07-26, endorsed running it and stated he expects a
surprise to be waiting for the analyst — that expectation is itself recorded
here as his stake in the outcome, prior to computation.

The analyst's rival lean, formed from the run-note summary before this
prereg: the layer **redistributes** structure rather than absorbing it. The
evidence for the lean is the key-tax localization (all 88 single-wins at
q_k < 1; worst plural deficit −0.210 exactly where sites are abundant),
which reads like structure being *moved onto the key axis*, not removed.

## Data (already existing, immutable)

`runs/hedged-stage1/survival.csv` — 1,620 cells; manifest ancestry:
implementation commit 5b8a936, prereg ca26217, source sha256 0309189e…76ba5e0.
Deterministic exact enumeration; no sampling error, so all statements are
about the authored model over the declared grid, and no p-values apply.
The quality channel (quality.csv) is OUT OF SCOPE for this test.

Three arms per cell, all on identical worlds:
- `late.p_accepted` — plural sites, binding at exercise time (the
  correctly-sited layer, per the Stage-1 result).
- `prebound.p_accepted` — same plural apparatus, binding at manufacture
  (the mis-sited layer).
- `single.p_accepted` — one stored carrier, no layer.

Grid axes (survival): p_c, p_l, q_k, g, a_e, rho_k, and the paired
categorical rho_c_rho_l.

## Definitions (frozen)

- **Residual structure** of an arm = the dependence of its delivered outcome
  (`p_accepted`) on the environment axes, measured two ways:
  1. **Total:** population variance of p_accepted across cells.
  2. **Per-axis:** main-effect range = max − min of the marginal mean of
     p_accepted across the levels of that axis.
- **Cell sets:** primary = all 1,620 cells; sensitivity = the 1,296
  activated cells (the 324 refused cells are (rho_c, rho_l) = (1,1) and the
  refusal is about *choice labeling*, not about outcome existence).
- **Margin:** ε = 0.01 in p_accepted units, matching the run's epsilon_m
  convention. Differences within ε are ties.

## Predictions (frozen, mutually exclusive on the primary contrast)

**Primary contrast: late vs prebound** (same apparatus, siting isolated).

- **H-FLATTEN (Tony's intuition):** Var(late) < Var(prebound) − ε², AND
  late's main-effect range ≤ prebound's + ε on **every** axis. The
  correctly-sited layer uniformly absorbs environmental structure.
- **H-REDISTRIBUTE (analyst's lean):** on at least one axis, late's
  main-effect range exceeds prebound's + ε, regardless of the total-variance
  verdict. The layer trades structure between axes rather than absorbing it.
  Named candidate axis, stated now: **g** (decay/hazard during the wait) or
  **q_k** if the prebound arm's key exposure differs from late's; the lean
  is that *waiting* is what late binding buys, and waiting has its own
  landlord.
- **NEITHER:** anything else (e.g., prebound flatter than late).

**Secondary contrast: late vs single** (layer vs no layer; resource
confound present, reported descriptively). Note recorded in advance: single
allocates 0 key qubits, so if single shows ~zero q_k-range while late shows
a material one, that is the *trivial* form of redistribution and will be
reported as such, not claimed as a win for the lean. The non-trivial claim
lives in the primary contrast.

**Falsifier for the lean:** if late's ranges are within ε of or below
prebound's on every axis AND total variance drops, the redistribution lean
is wrong and H-FLATTEN stands confirmed in this model.

## Exposure disclosure

The analyst has read, before this prereg: the Stage-1 run note (extrema of
Delta_M and V_Q with their grid locations; the 88/1,208 win split; worst
deficit −0.210 and its coordinates; key completion 0.729 at q_k = 0.9;
refusal structure; shared-penalty invariance) and summary.json's top-level
key names only. The analyst has NOT read: any p_accepted value, any variance
or marginal mean, any per-axis aggregate, or any row of either CSV. The
extrema exposure informs the lean; it does not contain the statistics
defined above, which have never been computed by anyone.

## Procedure

1. Commit this document (post-commit hook stamps it).
2. Implement `scripts/flattening_test.py` computing exactly the statistics
   above, nothing else, and emitting a JSON result.
3. Run once. Record the verdict in a results note. No statistic may be
   added after looking; anything further is a NEW preregistration.
