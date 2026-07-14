# Pre-registration: hedged-placement Stage 1

**Date:** 2026-07-13

**Status:** PRE-REGISTERED -- human-approved 2026-07-14. No model implementation or
deciding run has occurred. This approved revision must be committed and OTS-stamped
before the deciding model is implemented. Build verification may exercise only the
synthetic controls named below.

**Boundary:** governed by the approved hedged-placement conceptual-boundary
contract. This preregistration deliberately instantiates only its minimum deciding
kernel.

## 1. Deciding question

For one fixed request time and a direct three-clone encrypted construction:

1. Where does late site binding capture a recovery opportunity that a prebound
   policy misses?
2. Where does a non-clairvoyant late quality estimate improve recovered quality?
3. Where do key fragility and structural resource cost erase those gains relative
   to a single stored carrier?

The result is an exact region map of an **AUTHORED MODEL**. It is not a hardware
estimate, deployment verdict, or test of exercise timing.

## 2. Instrument choice

The deciding instrument is exact finite enumeration, not Monte Carlo and not the
`qsim` DES. Every binary world is enumerated with its analytic probability, and all
three arms are evaluated on the same world assignment.

Consequences:

- no seed, sampling confidence interval, warm-up, steady-state test, or trajectory
  replication is applicable;
- numerical error is limited to floating-point accumulation and must remain below
  `1e-12` in probability-balance and identity checks;
- all output probabilities and expectations are exact under the declared finite
  model, not estimates of the world;
- any later continuous or Monte Carlo refinement is a new battery.

The implementation should remain readable in one sitting. Generic simulation
infrastructure, persistent ontology, event queues, and the full conceptual-boundary
ledger are not licensed.

## 3. Fixed physical shape

- Direct protocol only.
- Number of encrypted signal carriers: `k = 3`.
- Number of all-required key qubits: `n_key = 3`.
- Canonical site order: `pi = (0, 1, 2)`.
- Permanent decoding relation: intact at every surviving carrier; no separate
  `D_i` failure channel in Stage 1.
- One request, instantaneous selection, one proposed site, authoritative gate
  validation, at most one materialization, no retry or fallback.
- Warrant valid, gate uncontended, no active probe, no crash or torn exercise.
- Successful plural construction is a condition of entry. Construction failure
  and unconditional deployment value remain outside the envelope.

Normalized event indices are `tau0=0`, `tau_c=1`, `tau_o=2`, `tau1=3`, and
`tau_x=4`. They establish ordering only; they are not physical time or a decay-law
claim.

## 4. Primitive world law

For a Bernoulli marginal `p` and common-mode weight `rho`, define:

```text
Mix3(p, rho):
  with probability rho:
    draw B ~ Bernoulli(p); return (B, B, B)
  with probability 1-rho:
    draw B_0, B_1, B_2 iid ~ Bernoulli(p)
```

This preserves each site's marginal while ranging from independent to fully
common-mode behavior.

Each world contains:

- global catastrophe `G ~ Bernoulli(g)`;
- key-qubit survival vector `K_vec ~ Mix3(q_k, rho_k)`;
- carrier survival vector `C ~ Mix3(p_c, rho_c)`;
- transient path launchability vector `L ~ Mix3(p_l, rho_l)`;
- latent high-quality vector `H ~ Mix3(0.5, rho_q)`;
- observed eligibility vector `E_hat`;
- initial quality-forecast vector `Z0`;
- late quality-estimate vector `Z1`.

If `G=1`, all key, carrier, and path bits are set to zero. Otherwise the four
mixtures are conditionally independent. This top-level catastrophe is the explicit
carrier-key-path common shock; no cross-object correlation may arise from draw
order.

Derived physical facts are:

```text
K_complete = all(K_vec)
E_i = C_i and L_i
C_phys_plural = K_complete and any(C)
C_phys_single = C_b
A_star = {i : K_complete and E_i}
```

The policy does not observe `K_complete`, `C`, `L`, `H`, or terminal quality
directly.

### 4.1 Eligibility observation

For each site independently conditional on true `E_i`:

```text
P(E_hat_i = E_i) = a_e
```

The gate validates the selected site's true `E_i` and, for plural arms,
`K_complete`. A false positive can therefore produce gate refusal; a false negative
can produce no proposal or a missed alternate.

### 4.2 Quality observation and outcome

Conditional on latent class `H_i`, initial and late signals are independent:

```text
P(Z0_i = H_i) = a_0
P(Z1_i = H_i) = a_1
```

Fix `a_0 = 0.60`. `a_1` is swept. Signals are forecasts/estimates, not measurements
of an encrypted carrier. All signal-error bits are independent across sites and
observation times conditional on `H`.

Terminal base quality is `0.80` when `H_i=1` and `0.40` when `H_i=0`. The single arm
receives base quality. Both plural arms receive:

```text
Q_plural_i = max(0, Q_base_i - delta_clone)
```

The accepted-delivery threshold is `q_min = 0.50`. `delta_clone` is an authored
construction-depth penalty, not a fit to IBM hardware.

## 5. Arm rules

All arms read the same realized public signals. Canonical tie-breaking always keeps
the anchor `b` first.

### 5.1 Survival/path pass

- At `tau0`, all arms set `b=0`.
- Single and prebound propose `b` iff `E_hat_b=1`; otherwise no proposal.
- Late-bound scans `[b, pi_without_b]` and proposes the first site with
  `E_hat_i=1`; otherwise no proposal.

### 5.2 Quality pass

- At `tau0`, `b` is the first site under `pi` with maximal `Z0_i`.
- Single and prebound propose `b` iff `E_hat_b=1`; otherwise no proposal.
- Late-bound filters to `E_hat_i=1`, chooses maximal `Z1_i`, and breaks ties under
  `[b, pi_without_b]`; if the filtered set is empty, it makes no proposal.
- A survival-only late selector from Section 5.1 is evaluated on the same quality
  worlds as the quality comparator `J_S`.

### 5.3 Materialization

Single materializes iff it proposes `j` and `E_j=1`. A plural arm materializes iff
it proposes `j`, `E_j=1`, and `K_complete=true`. Materialization consumes the claim
even when terminal quality is below `q_min`.

## 6. Parameter envelopes

No unlisted interpolation contributes to a verdict.

### 6.1 Survival/path envelope: 1,620 cells

Full Cartesian product:

```text
p_c in {0.50, 0.80, 0.95}
p_l in {0.50, 0.80, 0.95}
q_k in {0.90, 0.99, 1.00}
(rho_c, rho_l) in {
  (0.0, 0.0),
  (1.0, 0.0),
  (0.0, 1.0),
  (0.5, 0.5),
  (1.0, 1.0)
}
rho_k in {0.0, 1.0}
g in {0.0, 0.10}
a_e in {0.70, 0.90, 1.00}
```

Quality variables are held flat-high, with `H_i=Z0_i=Z1_i=1` and
`delta_clone=0`, so this pass cannot borrow signal from quality selection.

### 6.2 Quality envelope: 540 cells

Use five named physical profiles:

| Profile | `p_c` | `p_l` | `rho_c` | `rho_l` |
|---|---:|---:|---:|---:|
| carrier-scarce | 0.50 | 0.90 | 0.0 | 0.0 |
| path-scarce | 0.90 | 0.50 | 0.0 | 0.0 |
| balanced-independent | 0.80 | 0.80 | 0.0 | 0.0 |
| balanced-common | 0.80 | 0.80 | 1.0 | 1.0 |
| abundant-independent | 0.95 | 0.95 | 0.0 | 0.0 |

For every profile fix `q_k=0.99`, `rho_k=0`, and `g=0`, then take the Cartesian
product:

```text
a_e in {0.70, 0.90, 1.00}
rho_q in {0.0, 0.5, 1.0}
a_1 in {0.50, 0.70, 0.90, 1.00}
delta_clone in {0.00, 0.10, 0.20}
```

`rho_q=1` is the flat-within-world quality boundary. `a_1=0.5` is the
uninformative late-signal boundary. Neither may support a quality-channel verdict.
`delta_clone` is a shared plural-arm penalty: it must move absolute plural quality
and the plural-versus-single profile, but late-minus-prebound `Delta_M` and `V_Q`
should remain invariant. Failure of that invariance is a control failure, not a
finding.

## 7. Recorded outcomes and costs

For every cell and arm record exact probability or expectation of:

- physical claim recoverability before request;
- proposal, gate admission, materialization, and accepted delivery;
- exercise-opportunity miss;
- accepted-delivery miss;
- recovered quality conditional on materialization;
- the paired success cross-table: both, late-only, prebound-only, neither;
- paired quality difference on both-materialize worlds;
- quality-selector minus survival-selector difference by `|A_star|` stratum;
- conditioning-event probability for every conditional statistic.

For either plural arm:

```text
exercise_opportunity_miss =
  not materialized and K_complete and any_i E_i

accepted_delivery_miss =
  not accepted and K_complete
  and any_i (E_i and Q_plural_i >= q_min)
```

Key loss and absence of every launchable site are therefore physical unavailability,
not policy misses. The single arm reports delivery failure but receives no
alternate-site miss label because it owns no alternate carrier.

The primary quality value is:

```text
V_Q = E[Q_plural_(J_Q) - Q_plural_(J_S)
        | K_complete, both selectors materialize, |A_star| >= 2]
```

The same contrast is also reported separately for `|A_star|=2` and
`|A_star|=3`. The probability of each conditioning event is always reported.

Only these structural cost coordinates are instantiated:

```text
allocated_carrier_qubits: single=1, plural=3
allocated_key_qubits: single=0, plural=3
construction_module_calls: single=0, plural=1
selector_site_reads: number of site records inspected
decryption_participants_if_admitted: single=1, plural=4
residue_qubits_after_materialization: single=0, plural=5
forced_cleanup_qubits_after_no_materialization: surviving held resources
```

Report coordinates separately. They are counts, not time, energy, money, or a
scalar utility. No weighted net-benefit statistic is permitted.

## 8. Controls and activation

All controls must pass before the deciding grid is evaluated:

1. **Same-site identity:** force late-bound to the prebound site with selector reads
   excluded; plural outcomes and cost coordinates must match exactly.
2. **Forced rescue:** key intact, anchor unavailable, exactly one alternate truly
   and observably eligible, quality high; prebound misses and late-bound delivers.
3. **Direct-key loss:** all carriers and paths live, key incomplete; both plural
   claims are physically unrecoverable while single can deliver.
4. **Flat quality:** all eligible qualities and signals equal; quality selector
   retains the anchor and has zero quality option value.
5. **Uninformative signal:** `a_1=0.5` is labelled information-silenced regardless
   of decision movement or observed outcome.
6. **Permutation equivariance:** jointly permuting site labels and `pi` preserves
   every aggregate result.
7. **Probability balance:** enumerated world weights sum to one within `1e-12` in
   every cell.
8. **Shared-penalty invariance:** changing `delta_clone` changes absolute plural
   quality but not late-minus-prebound selection, `Delta_M`, or `V_Q`.

Channel activation requires the exact causal chain:

```text
parameter motion -> latent spread -> observable spread
                 -> decision change -> outcome or cost change
```

Survival/path activation additionally requires positive probability of an intact
plural claim with an unavailable anchor and an exercisable alternate. Quality
activation requires positive probability of at least two exercisable sites with
different latent qualities, `a_1>0.5`, a quality-driven decision change, and a
both-materialize comparison stratum.

Failed activation produces a refusal, not a null.

## 9. Cell labels and battery readings

Fix materiality thresholds:

```text
epsilon_M = 0.01  # absolute accepted-delivery probability
epsilon_Q = 0.01  # quality on the [0,1] scale
min_quality_stratum_mass = 0.05
```

These are effect-size thresholds, not significance tests or hardware tolerances.
The `0.05` stratum rule prevents a large conditional quality contrast on a
negligible part of the authored world mass from earning the mechanism.

For every cell:

```text
Delta_M = P(accepted_late) - P(accepted_prebound)
```

For each activated cell, label late-bound minus prebound accepted delivery:

- `POSITIVE` if `Delta_M >= epsilon_M`;
- `NEGATIVE` if `Delta_M <= -epsilon_M`;
- `NEUTRAL` otherwise.

Label quality option value `V_Q` only when the conditioning stratum has mass at
least `0.05`:

- `QUALITY_POSITIVE` if `V_Q >= epsilon_Q`;
- `QUALITY_NEGATIVE` if `V_Q <= -epsilon_Q`;
- `QUALITY_NEUTRAL` otherwise;
- `QUALITY_UNIDENTIFIED` below the stratum-mass threshold.

Battery-level readings:

- `SITE_CHOICE_DECISION_EARNED`: at least one activated survival/path cell is
  `POSITIVE`.
- `QUALITY_CHOICE_DECISION_EARNED`: at least one activated quality cell is
  `QUALITY_POSITIVE`.
- `REGION_THIN`: the relevant channel has values greater than `1e-12` somewhere but
  no value reaches its materiality threshold.
- `NOT_DECISION_EARNED_IN_TESTED_ENVELOPE`: both channels activate, neither has a
  material positive region, and all controls pass.
- `REFUSED`: any required control, probability balance, or channel-activation check
  fails. Refusal reason is recorded.

The complete refusal vocabulary for this instrument is:

- `CONTROL_FAILED`;
- `PROBABILITY_IMBALANCE`;
- `CHANNEL_SILENCED` with channel name;
- `NUMERIC_INVALID` for NaN, infinity, or tolerance violation.

Positive and negative regions may coexist; the full map is primary and the
battery-level label is only an index into it.

The `plural/prebound - single` contrast receives no binary verdict. It is reported
as the conditional direct-protocol fragility/resource profile against which the
late-bound region is read.

## 10. Allowable inference

Allowed:

> In the exact authored three-clone model, late binding has a material positive
> accepted-delivery region under the declared site, key, path, and observation
> envelope.

> The quality selector has value only in the reported survivor and information
> regimes; sparse survivors, flat quality, and uninformative estimates do not
> adjudicate that channel.

> The option region coexists with the separately reported direct-key fragility and
> structural resource counts.

Not allowed:

- hardware probability, hardware fidelity, or deployment-value claims;
- exercise-timing, retry, active-probe, concurrency, crash, or iterated-construction
  claims;
- a scalar net benefit;
- “late binding improves physical recoverability” relative to prebound;
- “no option exists” from a refused or envelope-bounded null;
- treating `delta_clone` as calibrated from the IBM results.

## 11. Licensed implementation and run discipline

Licensed implementation:

- one standalone exact-enumeration module under `scripts/`;
- focused tests under `tests/experiments/`;
- NumPy for compact enumeration and weighted reductions;
- JSON/CSV artifact writing sufficient for audit.

Not licensed: `qsim` engine integration, CLI integration, generic framework work,
plots required for verdicts, or persistent carrier/claim/warrant/gate classes.

Before any deciding grid run:

1. This preregistration is approved and OTS-stamped.
2. Implementation is reviewed against this document.
3. Only the eight synthetic controls are executed during build verification.
4. The implementation commit is recorded.

The first deciding execution writes one immutable directory containing:

- `manifest.json`: preregistration commit, implementation commit, source hash, and
  exact grids;
- `controls.json`;
- `survival.csv`;
- `quality.csv`;
- `summary.json`: activation, refusal, cell counts, extrema, and battery readings.

Any rerun is labelled replication. Because enumeration is deterministic, a valid
rerun must be byte-identical after excluding only run-directory identity and wall
clock metadata. A changed model or grid requires a new stamped preregistration.
