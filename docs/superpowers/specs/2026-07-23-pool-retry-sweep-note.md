# Pool retain-and-retry sweep: the maintenance share is robust — and conservative

**Date:** 2026-07-23 (evening)
**Discharges:** the pre-§4 drafting gate from the Gemini review disposition (2026-07-16,
recorded in the draft's session notes): "Before §4 drafts: either run the cheap
confirmation sweep on qsim (retain-and-retry replenishment arm at the same operating
point) or bound the claim inline."
**Register:** practice-grade (qsim). Expectation stated in-conversation before results
were read; recorded below including the part that was wrong.
**Artifacts:** runs/sweep-pool-retry/ (manifest.json + per-arm header.json committed;
events.jsonl local-only, regenerable). Script: scripts/pool_retry_sweep.py. Knob:
RunConfig.pool_herald_attempts (new, default 1 = shipped behaviour; engine change in
_on_pool_replenish_active; tests in tests/core/test_engine_pool.py +
tests/experiments/test_config.py; full suite 559 green).

## The question on record

The simulator implements retain-and-retry for rounds but release-and-reacquire for
§8.2 pool replenishment (each generation trigger burns a full switch reservation for
ONE herald attempt). The maintenance-amplification finding — 76% of fabric actuations
are maintenance, 3.22:1 (HSD transfer note, S1 anchor rr/δ=0/calm) — counts replenish
actuations under that choice. Is the figure an artifact of the choice?

## Design

Anchor config = examples/t1-open.toml verbatim (seed 11, four paths at p=0.7,
F=0.95, C=2, L=2, retry_cap 4, 400 s), the committed sweep-s1 δ=0 arm.
pool_herald_attempts ∈ {1, 2, 4, 8}: one replenish reservation hosts up to N bounded
herald attempts (spacing herald_retry_interval_s) before resolving. N=1 is the
regression control.

## Expectation (stated before reading results) — and its fate

Predicted: replenish reservations fall toward ~335–360 (reservations-per-deposit → 1),
maintenance share drops 76% → ~70%, qualitative claim (maintenance-dominated, >2:1)
survives. Falsification criterion: share below ~50% ⇒ the framing is design-induced
and §4 rewrites around the bounded claim.

**The specific prediction was WRONG in both moving parts.** Replenish reservations did
not fall (467 → 473–474, flat); the share ROSE. The error: the prediction modeled
replenish volume as failure-driven when it is demand-driven (the low-water trigger
refires as withdrawals and expiry drain depth), and it ignored that pool hits
substitute for foreground reservations. The falsification criterion was not
approached; the direction of error favors the claim — recorded anyway.

## Results (per arm; deadline compliance bit-identical 0.9948 across all; all CONVERGED)

| N | fg res | replenish res | share | ratio | deposits | withdrawn | expired | herald_failed |
|---|---|---|---|---|---|---|---|---|
| 1 | 145 | 467 | 76.3% | 3.22:1 | 334 | 243 | 85 (25.4%) | 139 |
| 2 | 95 | 473 | 83.3% | 4.98:1 | 435 | 293 | 135 (31.0%) | 44 |
| 4 | 91 | 474 | 83.9% | 5.21:1 | 476 | 297 | 174 (36.6%) | 4 |
| 8 | 83 | 474 | 85.1% | 5.71:1 | 480 | 305 | 170 (35.4%) | 0 |

Regression gate: N=1 reproduces the committed anchor exactly (145/467, 76.3%,
3.22:1, 334/243/85) — same seed, same CRN streams, knob dormant. (Bookkeeping note:
"deposits" counts pool.deposited from BOTH sources — replenish successes and
round-terminal returns — matching the HSD note's accounting.)

## Mechanism (event-legible)

Replenishment work is set by demand (withdrawals + expiry against the low-water mark),
not by its own failure rate. Making each trigger more likely to succeed within its
reservation therefore does not reduce maintenance actuations — it makes them
productive: deposits rise 44%, pool hits rise 26%, and every round served from the
pool skips its foreground fabric reservation entirely (a pool withdrawal holds no
reservation). Foreground actuations fall 145 → 83; the maintenance SHARE rises. The
second effect: the pool now refills faster than demand drains it, so expiry wastage
rises 25.4% → ~35%. The cold-chain sentence: running the compressors more efficiently
does not lower the refrigeration bill's share of the trade — it stocks shelves deeper,
and deeper shelves compost more.

## Dispositions

1. **§4 may draft.** The 76%/3.22:1 figure is robust to the replenishment
   retry-protocol choice at this operating point — and is the CONSERVATIVE end of the
   sweep (retain-and-retry raises it to 83–85%). Print it with both bounds: one
   low-water policy at one operating point (the standing bound), and "robust to the
   Q4 retry-protocol choice; the shipped release-and-reacquire arm is the low end"
   (this sweep).
2. **The wastage figure is MORE protocol-sensitive than the amplification figure.**
   25.4% aging-out (HSD note) becomes 31–37% under retain-and-retry. Anywhere the
   draft prints the wastage number, it carries the protocol-choice bound explicitly.
3. **Q4 sharpens.** The hardware question is not just "which retry protocol" but:
   retry protocol selects the SPLIT of a fixed maintenance budget between failed
   triggers (release-and-reacquire) and expiry wastage (retain-and-retry). Neither
   arm reduces the maintenance share; they trade its composition. Candidate sentence
   for §10's Q4 entry.
4. **Bounds:** one seed, one operating point, same as the original figure. Outcome
   flatness across arms is expected at this calm point (compliance was already
   saturated); no outcome claim is made.
