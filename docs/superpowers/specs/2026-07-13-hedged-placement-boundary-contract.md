# Hedged-placement Stage 1 boundary contract

**Date:** 2026-07-13

**Status:** APPROVED AS CONCEPTUAL BOUNDARY -- human review, 2026-07-13. This is
an inference boundary, not a clause-by-clause implementation specification; no
numerical preregistration or deciding run is authorized by this document.

**Governs:** the finite, exogenous Stage 1 comparison of `single`,
`plural/prebound`, and `plural/late-bound` defined by the hedged-placement
exploration charter.

## 1. Purpose and inference target

Stage 1 asks one narrow question:

> At one fixed exercise-request time, does retaining the choice of
> materialization site change successful capture of an already-existing physical
> recovery opportunity, recovered quality, or typed resource cost?

It does **not** ask whether plural placement makes the physical claim more
recoverable than prebinding. The two plural arms share the same physical
histories through exercise. Late binding can capture recoverability that the
prebound policy misses; it cannot retroactively create that recoverability.

The baseline contract freezes:

- direct encrypted cloning only;
- successful plural construction as a condition of entry into the Stage 1
  comparison, while retaining construction work and duration in the cost ledger;
- one exogenous exercise request at a fixed time;
- one selected site and at most one gate-admitted exercise;
- no waiting, retry, sequential fallback, concurrent request, or policy-chosen
  abandonment;
- shared passive classical telemetry, with no active quantum probing;
- a finite exogenous paired-world model, not a queueing or steady-state DES.

These restrictions isolate **where** to exercise. They leave **when** to exercise,
construction reliability, concurrency, crash recovery, and active sensing
undecided.

## 2. Evidence altitude

- **Paper-demonstrated:** direct encrypted cloning creates individually maximally
  mixed plural carriers; any selected carrier can be decrypted with the complete
  quantum key; the key is single-use; delayed choice is physically possible; and
  circuit depth and idle time affect recovered quality in the reported hardware
  experiments.
- **Systems mapping:** claims, warrants, the exercise gate, paired policy arms,
  event and terminal semantics, selectors, ledgers, controls, and inference
  language.
- **Model assumption:** site and key hazards, permanent decoding-relation loss,
  transient path availability, observation error and staleness, quality potential
  outcomes, resource costs, and joint common-mode shocks.
- **Speculation, excluded from deciding runs:** nondestructive quality probing,
  rollback-safe decryption, torn-exercise physics, deployed failure laws, and a
  universal conservation of fragility.

Every Stage 1 report must carry this altitude split. Mechanical correctness is not
physics validation.

## 3. Physical and observable quantities

Let `I = {1, ..., k}` be canonical site identities and `pi` a canonical ordering
fixed before any world is drawn. For direct encrypted cloning define:

- `K(t)`: the complete direct-protocol quantum key remains sufficient;
- `C_i(t)`: encrypted carrier `i` remains physically present;
- `D_i(t)`: the permanent physical decoding relation for site `i` remains
  possible;
- `L_i(t)`: the current classical/control materialization path to site `i` is
  launchable;
- `Q_i`: latent terminal recovered quality under the standardized Stage 1
  attempt at site `i`, requested at `tau1` with the baseline's fixed gate and
  decryption durations;
- `X_i^0`: pre-construction candidate-site information, including topology,
  planned placement, and calibration forecasts available at `tau0`;
- `X_i(t)`: timestamped information actually observable by a policy about
  carrier status, path status, and quality.

The direct-protocol recovery set for site `i` is:

```text
R_i(t) = K(t) and C_i(t) and D_i(t)
```

Physical claim recoverability and current exercise eligibility are distinct:

```text
C_phys(t) = any_i R_i(t)
A_star(t) = {i : R_i(t) and L_i(t)}
```

`L_i(t) = false` may cause a policy failure or gate refusal while `C_phys(t)`
remains true. Irreversible loss of `K`, or loss of every `C_i and D_i` recovery
path, destroys the direct-protocol claim.

`Q_i` is a potential outcome, not a policy-readable field. An encrypted carrier
does not reveal its eventual recovered quality merely by existing. A policy may
read only declared estimates in `X_i(t)`.

For a preregistered acceptance threshold `q_min`:

```text
C_good(tau1) = any_i [R_i(tau1) and L_i(tau1) and Q_i >= q_min]
```

`C_good` is an analyst-side potential-outcome quantity. It is not selector input.

### 3.1 Direct versus iterated construction

The direct protocol has one literal all-required key dependency. Iterated cloning
has path-specific ancestry and key dependencies; losing one lower-level key can
prune a branch without destroying every recovery path. Stage 1 therefore excludes
iteration rather than representing it as one larger all-required bundle.

Any later iterated pass must enumerate a recovery-set graph `K_i` for each leaf and
recompute recoverability after component loss. The defensible open conjecture is a
**protocol-scoped common-quantum-cut-set hypothesis**, not a universal conservation
law inferred from no-cloning.

## 4. Clocks and event order

The clocks are:

- `tau0`: source input is available and the common initial site rule runs;
- `tau_c`: plural construction has completed successfully;
- `tau_o`: cutoff of the freshest decision-admissible observation;
- `tau1`: exogenous exercise request;
- `tau_g`: gate admission and site binding, if admitted;
- `tau_m`: materialization attempt terminal;
- `tau_x`: fixed end-of-episode cleanup.

When the corresponding events occur, the required ordering is:

```text
tau0 <= tau_c <= tau_o <= tau1 <= tau_g <= tau_m <= tau_x
```

Equality is allowed. `tau_c` is never reused as an observation timestamp.
This three-clock form supersedes the exploration charter's shorthand in which
plural construction occurred at `t0`.

The event grammar is:

```text
input.available @ tau0
  -> common initial observation
  -> {single.select b | prebound.designate b | latebound.anchor b}
  -> plural.construct.begin
  -> paired primitive shocks and passive evolution*
  -> plural.construct.complete @ tau_c
  -> paired primitive shocks and passive evolution*
  -> observation.cutoff @ tau_o
  -> paired primitive shocks through tau1-
  -> exercise.request @ tau1
  -> {
       policy.no_proposal -> NOT_ADMITTED
     | policy.propose one site
         -> gate validates claim, warrant, selected site, and path
         -> {
              gate.refuse -> NOT_ADMITTED
            | atomic(reserve claim, reserve path, bind site, admit) @ tau_g
                -> materialization.launch
                -> {materialized.accepted | materialized.subthreshold} @ tau_m
            }
     }
  -> classify request, claim, schedule, relation, and cleanup axes
  -> fixed end-of-episode cleanup @ tau_x
```

The single arm has no plural-construction events; it stores its one carrier while
the paired plural arms construct. `tau_c` remains a common comparison checkpoint.
Policy selection is instantaneous in the baseline, and every admitted arm uses the
same fixed gate and decryption durations. Selection latency and its physical
consequences require a separately named extension.

At equal timestamps, a preregistered sequence order applies. Primitive shocks
intended to affect a decision occur before the associated observation. Deadline
compliance is inclusive at the deadline; physical materialization and deadline
status remain separate facts.

All arms experience the same elapsed baseline from `tau0` to `tau1`. Plural
construction adds its actual circuit work, depth, occupancy, key/carrier
qubit-time, and construction-specific quality penalty, but elapsed time is not
charged twice. Stage 1 claims are conditional on construction completing by
`tau_c`; construction failure belongs to a later unconditional deployment pass.

## 5. Arm contract

| Arm | Decision at `tau0` | Decision at `tau1` | Physical resources |
|---|---|---|---|
| `single` | Select reference site `b` with the common initial rule. | May propose only `b`. | One unencrypted carrier; no plural key. |
| `plural/prebound` | Use the exact same rule and designate `b`. | May propose only `b`; no reselection or fallback. | Same plural construction, carriers, key, and histories as late-bound. |
| `plural/late-bound` | Compute `b` as an identity anchor but do not bind. | Select zero or one site from admissible observations. | Identical to prebound through `tau1`. |

The single and prebound initial site and tie-break must match. The two plural arms
must have identical construction, primitive shocks, carrier/key histories, passive
exposure, and non-selection accounting.

At `tau1` each arm gets one proposal opportunity. A gate refusal does not open a
fallback loop. Any wait, retry, or second proposal would reintroduce exercise
timing and is an arm-contract violation.

## 6. Information and selector contract

All arms receive the same public passive telemetry stream. Each observation records
source, timestamp, acquisition protocol, and any declared error model. Alternate-
site telemetry may be known to prebound even though prebound cannot act on it; the
contrast is option value, not unequal information acquisition.

The baseline permits no active probe of an encrypted carrier or key. A future
`late-binding-plus-sensing` variant must be separately named and charge work,
latency, control occupancy, estimate age, and carrier/key backaction. Perfect
observation may appear only as an explicitly labelled analytic upper bound, never
as the deciding baseline.

A selected site `J_a(tau1)` must be measurable from that arm's declared information
at `tau1`. Replaying the selector from recorded observations must reproduce every
choice. Reading latent `R_i`, `Q_i`, future survival, or an unreturned reservation
result is oracle leakage.

### 6.1 Common initial selector

The preregistration will freeze one initial selector per pass. It is applied
identically by single and prebound and produces late-bound's anchor `b`.
Because plural carriers do not yet exist at `tau0`, this selector reads only
`X_i^0`. Initial quality information is a forecast of the standardized terminal
recovery outcome, not telemetry from a constructed carrier.

- Survival/path pass: first pre-construction admissible candidate under `pi`.
- Quality pass: largest pre-construction quality forecast among admissible
  candidates, ties by `pi`.

### 6.2 Late-bound survival/path selector

At `tau1`, choose the first site under ordering `[b, pi]` that is observed eligible.
If no site is observed eligible, produce no proposal. The gate validates the one
selected site against current authoritative state.

Carrier rescue and transient-path rescue are tagged separately. A stale observation
that fails gate validation is a refusal, not permission to try another site.

### 6.3 Late-bound quality selector

At `tau1`, filter to observed-eligible sites, choose the largest timestamped quality
estimate available by `tau_o`, and break ties under `[b, pi]`. Consequently, tied or
unchanged worlds retain `b`.

The preregistration must specify the relation:

```text
law(Q_i | quality_estimate_i(tau_o), tau1 - observation_time_i)
```

An expired estimate follows a preregistered canonical default ordering; it does not
silently become current truth.

Selectors never combine materialization probability, quality, latency, qubit-time,
or work into a hidden weighted score. Costs remain outputs.

## 7. Gate and exercise semantics

For the deciding Stage 1 baseline:

- one warrant is valid in every world;
- there is no competing request;
- selection is instantaneous and does not change launch time or physical outcome;
- the gate still validates physical claim status and the selected path so request,
  policy, and physical failures remain distinguishable;
- atomic gate admission reserves the claim and path, binds one site, and is the
  classical linearization point at which exercise begins;
- at most one exercise is admitted;
- direct-protocol decryption is modeled atomically after admission, producing one
  realized quality for the selected site.

The valid warrant, attached relation, and uncontended reservation are constant
analytic labels in this baseline. They do not field-earn persistent warrant,
relation, or serialization state; those objects require later authorization or
concurrency decisions.

Crash, interruption, nondestructive decryption failure, and torn exercise are not
in the deciding model because the paper does not establish their transition law.
Synthetic classification controls may inject them, but they cannot contribute to a
Stage 1 region result. A later crash pass must define a destructive frontier; absent
that evidence, an interrupted claim is `indeterminate` and quarantined, never
retried.

## 8. Outcome contract

A flat terminal enum is prohibited. Each episode records separate axes:

| Axis | Baseline values | Meaning |
|---|---|---|
| `request_disposition` | `NO_PROPOSAL`, `GATE_REFUSED`, `MATERIALIZED` | What happened to this request. |
| `attempt_disposition` | `NOT_ADMITTED`, `ACCEPTED`, `SUBTHRESHOLD` | What happened after gate admission. |
| `claim_state_at_request_terminal` | `INTACT`, `DESTROYED`, `CONSUMED` | Physical recoverability after the request and before cleanup. |
| `schedule_status` | `IN_DEADLINE`, `LATE`, `NO_DELIVERY` | Deadline result, independent of physical state. |
| `relation_status` | `ATTACHED`, `ORPHANED` | Classical warrant/gate relation. Baseline remains attached. |
| `cleanup_action` | `RELEASE_ONLY`, `RECLAIM_RESIDUE`, `FORCED_TEARDOWN_AND_RECLAIM` | Physical cleanup performed at the fixed horizon. |
| `cleanup_status` | `PENDING`, `COMPLETE`, `LEAKED` | Whether the cleanup action balanced. |
| `claim_state_after_cleanup` | `CONSUMED`, `DESTROYED` | Physical state after the fixed cleanup action. |

Extensions may add `FAILED_NONDESTRUCTIVE`, `TORN`, and `INDETERMINATE`, but only
with an explicit physical failure model.

Classification rules:

1. Materialization with `Q_j >= q_min` records `MATERIALIZED`, `ACCEPTED`, and
   `CONSUMED`, even if late.
2. Materialization below threshold records `MATERIALIZED`, `SUBTHRESHOLD`, and
   `CONSUMED`; delivery failed, but the key was still used.
3. Physical irrecoverability before admission records `DESTROYED`; any later
   request refusal is derivative.
4. `NO_PROPOSAL` and `GATE_REFUSED` do not themselves alter claim state.
5. Warrant loss or gate unreachability can orphan an intact claim; orphanhood is
   relational, not a claim state.
6. An **exercise-opportunity miss** is an analyst-side diagnostic: the arm did not
   materialize while another site belonged to `A_star` in the same paired world.
7. An **accepted-delivery miss** is stricter: the arm did not deliver an accepted
   result while some alternate `i` satisfied `R_i(tau1) and L_i(tau1) and
   Q_i >= q_min`. Neither diagnostic is a physical terminal.

At fixed `tau_x`, every episode performs the same non-decision cleanup rule.
Successful plural materialization creates `spent_after_success` residues. Physical
claim loss creates `dead_after_claim_loss` residues. Both are physically reclaimed
and charged. An intact no-launch claim is recorded intact at request terminal and
only then undergoes charged `FORCED_TEARDOWN_AND_RECLAIM`, which destroys the claim
and releases its carriers and key. The ledger preserves both claim-state snapshots;
cleanup cannot rewrite the request-terminal postcondition or end qubit-time without
a physical teardown/reclamation event.

## 9. Paired-world contract

One independent world contains immutable potential histories for every candidate
site and key component. Primitive shocks are generated before arm execution and
jointly derive carrier, key, permanent decoding relation, transient path, observable
signal, and latent quality consequences. Sampling separate marginals that erase
carrier-key-path common mode is prohibited.

Every stochastic draw has a canonical semantic key such as:

```text
(contract_version, world_id, process, site_id, component_id, event_ordinal)
```

The key must not contain arm, policy, draw order, selected site, or event-heap
position. A stable hash over canonical serialization of `(world_seed, stream, key)`
implements the repository's existing key-addressed randomness contract. Potential
exercise outcomes exist for unselected sites but remain hidden from policies.

Each world records generator version, schema version, information-set definition,
primitive-shock inventory, semantic-key inventory, and a world checksum. Every arm
ledger references that checksum.

The independent world is the Stage 1 inference unit. Arms and sites within a world
are paired observations, not replicates. A later repeated-arrival DES uses the
independent seed/trajectory as its inference unit and additionally requires steady-
state, censoring, offered-work, and time-resolved pairing-coverage checks.

## 10. Typed accounting ledger

Each arm/world records:

- identity: world, arm, claim, carrier, site, key, and contract version;
- construction: mode, start/end, duration, circuit depth, gate/work counts,
  occupancy, and completion condition;
- storage: carrier and key qubit-time by site/component, elapsed exposure, and
  construction-specific penalties;
- observation: source, timestamp, error draw, work, latency, and perturbation flag;
- selection/gate: anchor, selected site, information-set hash, validation result,
  refusal reason, and reservation interval;
- exercise: launch/end, site, decryption work/depth, realized quality, and
  acceptance result;
- residue/cleanup: kind, count, location, residence time, work, released capacity,
  forced-teardown work, and leaks;
- outcome axes from Section 8, including claim state before the request, at request
  terminal, and after cleanup.

Costs remain a typed vector:

```text
kappa = (
  carrier_qubit_time,
  key_qubit_time_by_placement,
  construction_work_by_kind,
  construction_duration,
  observation_work,
  selection_work,
  gate_work,
  control_path_time,
  decryption_work,
  exercise_latency,
  residue_count,
  residue_qubit_time,
  reclamation_work,
  reclamation_duration
)
```

Report coordinate-wise paired deltas, Pareto relations, and symbolic break-even
surfaces. A weighted sum is permitted only with explicit, dimensioned, externally
supplied exchange rates and sensitivity analysis. Reduced work caused by more
refusals is never reported without the associated lost materializations.

## 11. Estimands and channel decomposition

The primary contrasts remain:

- `plural/prebound - single`: direct-protocol fragility and plural-presence tax;
- `plural/late-bound - plural/prebound`: site-choice option value;
- `plural/late-bound - single`: conditional post-construction outcome/cost profile
  inside the tested envelope.

None is an unconditional deployment comparison because Stage 1 conditions on
successful plural construction. Deployment inference requires construction-failure
probability, failed-construction cost, and the unconditional offered population.

For paired accepted-materialization indicators `M_L` and `M_B`:

```text
Delta_M = E[M_L - M_B]
        = P(M_L=1, M_B=0) - P(M_L=0, M_B=1)
```

Report the full paired cross-table: both succeed, late only, prebound only, neither.
Tag discordant worlds as carrier rescue, path rescue, selector harm, stale-signal
harm, gate-refusal difference, or deadline harm.

Quality is never set to zero on failure. Report:

- each arm's materialization and accepted-delivery probability;
- paired quality difference on both-materialize worlds;
- quality distributions for late-only and prebound-only deliveries;
- all conditional denominators.

For the quality selector `J_Q` and survival/path selector `J_S`:

```text
V_Q(n) = E[Q_(J_Q) - Q_(J_S)
           | C_phys=true, |A_star|=n, both materialize]
```

The conditioning-event probability is reported separately. Interpretation by
survivor regime is fixed:

- no exercisable sites: no site-choice value;
- one survivor equal to `b`: neither channel has option value;
- one alternate survivor: survival/path rescue only;
- at least two survivors including `b`: clean quality-option stratum;
- at least two alternate survivors excluding `b`: survival enabled capture;
  quality comparison among rescued alternatives is not quality improvement over
  prebound;
- flat eligible qualities: no physical quality spread;
- spread qualities with uninformative estimates: observation channel silenced;
- spread estimates with flat true qualities: decision movement without quality
  value.

## 12. Invariants, controls, and activation

Required invariants:

- **Plural identity:** both plural arms share construction and physical histories.
- **Same-site identity:** when late-bound selects `b`, outcomes and non-selection
  ledgers match prebound; selection is instantaneous, and with incremental
  selection work zero the full ledgers match.
- **Single/prebound anchor identity:** both select the same `b` at `tau0`.
- **Consume once:** at most one exercise is admitted per claim.
- **Balance:** every acquired resource is released, physically reclaimed after a
  declared teardown, or reported leaked; residues never disappear silently.
- **Filtration:** every selector choice replays from declared observations.

Required synthetic and metamorphic controls:

- identity world: force late-bound to `b`; plural arms must match;
- forced rescue: `b` unavailable, exactly one alternate exercisable, key intact;
  prebound misses while late-bound materializes without any change in `C_phys`;
- direct-key loss: carriers survive but `K=false`; both plural claims are destroyed;
- intact-but-refused: claim recoverable but selected path unavailable; claim remains
  intact;
- `k=1`: late-bound and prebound are identical;
- fully common-mode or all-site-identical histories: no survival option value;
- flat quality: no quality option value and tie retains `b`;
- uninformative signal: physical quality spread does not license a quality verdict;
- site-label permutation: results are equivariant under relabeling plus `pi`;
- oracle trap: future reversal must not alter the choice without a timely admissible
  signal;
- monotone threshold coupling for probability sweeps with fixed policy.

The causal activation chain is:

```text
knob motion
  -> latent physical spread
  -> admissible observable spread
  -> decision change
  -> terminal and/or typed-cost change
```

Every relevant link must move before a positive or null channel verdict is read.

## 13. Refusals are data

Analysis refusal codes are distinct from observed gate outcomes:

- `REFUSED.BROKEN_PAIRING`
- `REFUSED.ARM_CONTRACT_VIOLATION`
- `REFUSED.ORACLE_LEAKAGE`
- `REFUSED.OBSERVABILITY_UNSPECIFIED`
- `REFUSED.ACCOUNTING_INACTIVE`
- `REFUSED.TERMINAL_SEMANTICS_COLLAPSED`
- `REFUSED.CONTROL_FAILED`
- `REFUSED.CHANNEL_SILENCED.CARRIER`
- `REFUSED.CHANNEL_SILENCED.PATH`
- `REFUSED.CHANNEL_SILENCED.QUALITY`
- `REFUSED.CHANNEL_SILENCED.INFORMATION`
- `REFUSED.CHANNEL_SILENCED.DECISION`
- `REFUSED.CHANNEL_SILENCED.KERNEL`
- `REFUSED.INSUFFICIENT_REPLICATION`
- `REFUSED.CONDITIONAL_QUALITY_UNIDENTIFIED`

`REFUSED.TRANSIENT_OR_CENSORED` applies only to a later DES, not finite exogenous
Stage 1.

Observed outcomes use the Section 8 axes and detailed reasons such as
`selected_site_unavailable`, `selected_path_unavailable`, or
`claim_physically_destroyed`.
An observed gate refusal is not an analysis refusal.

A region map is interpretable only after checksums and shared draws match; arm
invariants and controls pass; the causal channel activates; accounting balances;
each cell has preregistered independent-world support and uncertainty; and terminal
causes and evidence altitude are reported.

## 14. Allowable and prohibited inference

Allowable:

> Within authored world family `M`, information contract `I`, fixed request time
> `tau1`, and the declared direct-protocol model, late binding changed exercise-
> opportunity misses, accepted-delivery misses, and accepted-materialization
> probability by the reported paired contrasts in region `R`; physical claim
> histories were paired and costs are reported as vector `Delta_kappa`.

> Conditional on an intact claim, at least two exercisable sites, and concordant
> materialization, the non-clairvoyant quality selector changed recovered quality
> relative to the survival-only selector.

> No site-choice value was demonstrated in this activated policy-information-regime.

> The designated-site request failed while physical recovery through another site
> remained possible.

Prohibited:

- late binding improved pre-exercise physical recoverability relative to prebound;
- a gate refusal, policy miss, warrant loss, or deadline failure destroyed a claim;
- the selector chose the highest-quality carrier when it saw only an estimate;
- a failed or interrupted decryption can safely retry another carrier;
- Stage 1 supports holding, early exercise, retry, abandonment, crash recovery, or
  exercise timing;
- a conditional post-construction result establishes deployment value or
  deployment preference;
- encrypted cloning is net-beneficial or cost-effective without explicit exchange
  rates or component-wise Pareto dominance;
- fragility is universally conserved, any key loss destroys an iterated claim, or
  the direct-protocol cut set is universal;
- an authored model result is hardware-validated or hardware-universal;
- a null after failed activation means no option value exists.

## 15. Handoff to preregistration

This contract resolves the conceptual boundary. The numerical Stage 1
preregistration must still freeze:

- site count and direct key width;
- primitive-shock families and their independent, common-mode, and correlated
  boundaries;
- clock values and passive/construction quality laws;
- observation source, error, staleness, and authoritative gate checks;
- acceptance threshold and quality model;
- selector parameters, although not selector semantics;
- cost-vector coordinates actually instantiated by the Stage 1 mechanism;
- parameter grid, precision or power rule, independent-world count, and uncertainty
  method;
- exact positive, null, interaction, and refusal readings.

The preregistration may simplify this contract but may not silently broaden it. Any
addition of iteration, active probing, fallback, timing choice, concurrency,
construction failure, or torn exercise is a separately named battery.
