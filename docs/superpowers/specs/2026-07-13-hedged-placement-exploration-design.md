# Hedged-placement exploration charter

**Date:** 2026-07-13
**Status:** APPROVED FOR READ-ONLY SCOUT PASS. This charter freezes comparison
semantics and allowable inference. It is not a numerical preregistration, does
not admit fields or objects into `qsim`, and licenses no implementation.

**Inputs:**

1. `2026-07-13-state-taxonomy-authority-semantics.md`
2. Yamaguchi et al., arXiv 2602.10695, in `docs/references/`
3. The object-model admission rule in `2026-07-06-field-battery-prereg.md`
4. The flat-result, paired-accounting, and replication lessons in
   `2026-07-10-s1-run-note.md`

## 1. Research question

Does late binding among plural encrypted presences improve recoverability or
recovered quality after accounting for the shared claim's fragility and the
cost of creating, carrying, exercising, and reclaiming the plural structure?

The exploration separates two option-value channels:

- **Survival/path option:** choose at exercise among sites that differ in
  carrier survival or current materialization-path executability.
- **Quality option:** choose at exercise among eligible sites that differ in
  currently recoverable quality.

A binary survival/path model may earn the mechanism but cannot reject it
globally. A mechanism-level negative conclusion requires an activated quality
pass as well.

## 2. Evidence altitude

Every scout statement must be labeled as one of:

- **Paper-demonstrated:** supported directly by Yamaguchi et al.
- **Systems mapping:** a defensible consequence for an OS decision.
- **Model assumption:** introduced to make an analytic envelope possible.
- **Speculation:** a candidate extension or failure mode not established by
  the paper.

The paper does not establish a deployed carrier-loss process, a key-placement
hazard model, a materialization-path contention model, or a universal quality
decay law. Those remain model assumptions even when physically plausible.

## 3. Shared paired world

Each comparison is evaluated in one paired sample world:

- A quantum state becomes available at creation time `t0`.
- Exercise is requested at `t1`, with `t1 >= t0`.
- The world contains `k` candidate sites, their carrier histories, their path
  histories, and, in the quality pass, their quality histories.
- A shared key-bundle history exists for the two plural arms.
- Every arm sees the same exogenous realization. An arm cannot redraw a more
  favorable world.
- Decisions at `t0` may read only information observable at `t0`.
- Decisions at `t1` may read only information observable at `t1`. No arm has
  access to future outcomes.
- Stage 1 treats carrier, key, path, and quality histories as exogenous.
  Policy-induced contention and other endogenous feedback belong to Stage 2.

The first pass is symbolic or uses dimensionless sensitivity parameters. It
does not claim hardware-calibrated prediction.

## 4. Arm contract

### 4.1 Single

- One unencrypted stored presence at a reference site selected at `t0`.
- No encrypted-cloning key bundle and no clone-generation overhead.
- Pays the same passive-storage duration and baseline decay model as the
  plural arms.
- Pays the materialization or consumption-path costs that any arm would pay;
  encryption/decryption-specific costs remain separately visible.

### 4.2 Plural/prebound

- `k` encrypted presences and the complete shared key bundle are created at
  `t0`.
- One site is designated at `t0` using the same `t0` information and selection
  rule used by the single arm.
- The other presences are carried but are unavailable for reselection at
  exercise. This is a deliberate control, not a proposed operating policy.
- Pays the full plural-presence, key, exercise-gate, decryption, and residue
  reclamation costs.

### 4.3 Plural/late-bound

- Has the same `k` encrypted presences, key bundle, and non-selection costs as
  plural/prebound.
- The exercise gate selects one eligible site at `t1` using only the channel
  information observable then.
- The exercise gate serializes against the ensemble-level claim and admits at
  most one exercise in flight.

The two plural arms may differ only in binding time, selection work, and costs
caused directly by that difference. Any other asymmetry is a confound.

## 5. Frozen contrasts

- `plural/prebound - single`: plural-presence overhead and fragile-kernel tax.
- `plural/late-bound - plural/prebound`, survival/path pass: option value from
  carrier survival and path executability.
- `plural/late-bound - plural/prebound`, quality pass: option value from
  recovered-quality spread.
- `plural/late-bound - single`: net deployment comparison within each channel.

The contrasts are reported as vectors. They are not summed into one utility.

## 6. Outcome and cost ledger

Report separately:

- probability of successful materialization;
- conditional recovered quality or fidelity;
- exercise latency and deadline compliance, when a deadline is represented;
- carrier qubit-time;
- key-bundle qubit-time;
- control-path occupancy;
- clone-generation and decryption work;
- spent-residue count and reclamation work;
- gate refusal, claim destruction, and torn-attempt outcomes.

Agents may derive Pareto regions or break-even exchange rates, such as the
minimum value assigned to one additional successful materialization needed to
pay a qubit-time increment. They must not silently assign exchange rates or
collapse different-kinded costs into a scalar.

## 7. Model families to explore

The charter freezes families, not values.

### 7.1 Carrier availability

Use a model capable of separating common-mode loss from site-specific loss.
The independent-site limit and the fully correlated limit are both required
boundary cases.

### 7.2 Key-bundle survival and placement

Compare at least:

- a co-located or common-mode bundle whose qubits tend to live or die together;
- a distributed bundle with site-specific hazards and an all-required survival
  condition.

Do not assume `q^n` is the only key-survival law. Bundle size, direct versus
iterated construction, and correlated noise are explicit sensitivity or
boundary questions.

### 7.3 Materialization-path executability

Path executability is per-site and may change between `t0` and `t1`. It must
create cross-site spread in some tested regime. Stage 1 models it exogenously;
contention caused by the arms themselves is deferred.

### 7.4 Recovered-quality spread

The cheapest admissible model is a two-class or scalar per-site quality at
`t1`, conditional on carrier and key survival. Its relation to information
available at `t0` must be explicit: fixed and known, revealed later, or evolving
with a stated temporal correlation. An independent redraw at `t1` is an upper
option-value boundary, not a neutral default.

If quality or path state requires measurement, calibration, or probing, its
observability must be justified or charged. The late-bound arm receives no
free oracle.

### 7.5 Passive decay

All arms experience the same baseline passive-storage duration. Additional
encrypted-cloning circuit-depth, key, or decryption penalties are represented
separately so cloning is not charged for aging that the single arm also pays.

## 8. Activation and refusal rules

No flat result is interpretable until the relevant chain is demonstrated:

1. **Carrier activation:** some worlds contain partial, not merely all-or-none,
   carrier survival.
2. **Path activation:** path executability differs across sites at `t1` in some
   tested regime.
3. **Quality activation:** surviving eligible sites differ in quality at `t1`
   in some tested regime.
4. **Decision activation:** late binding sometimes selects a different site
   than prebinding.
5. **Kernel activation:** changing key placement or correlation changes claim
   survival somewhere in the envelope.
6. **Accounting activation:** plural arms visibly pay the costs the charter
   assigns to them.

If an activation check fails, the result is **REFUSED: CHANNEL SILENCED**, not
a null effect.

## 9. Allowable inference

- Survival/path positive: late binding is decision-earned in that channel for
  the identified region.
- Survival/path null after activation: no demonstrated value in that channel
  and envelope; quality remains undecided.
- Quality positive: late binding is decision-earned in that channel for the
  identified region.
- Quality null after activation: no demonstrated value in that quality model
  and envelope; it is not a hardware-universal negative.
- Both channels null after activation: the mechanism is not decision-earned in
  the tested Stage 1 envelope.
- A changed decision supported entirely by cheaper existing state is
  **REPRESENTATION-CHEAP**; it does not earn new ontology.
- New persistent state is **FIELD-EARNED** only when a decision requires it and
  the required fact is not derivable from cheaper represented state.

A positive Stage 1 result licenses a minimal mechanism preregistration, not a
full `qsim` integration. A negative result may preserve the vocabulary while
rejecting the modeled mechanism at that regime.

## 10. Parallel scout assignments

All scouts are read-only. They do not edit files, implement code, or select
final numerical ranges.

### Scout A: fragility tax

Analyze `plural/prebound - single`, including passive-decay symmetry,
clone/key overhead, key-placement correlation, and the conservation-of-
fragility conjecture.

### Scout B: survival/path option

Analyze `plural/late-bound - plural/prebound` under carrier survival and
time-varying path executability. Separate carrier survival from path survival.

### Scout C: quality option

Analyze `plural/late-bound - plural/prebound` under the minimal quality-spread
model. Make temporal correlation, observability, and information timing
explicit.

### Scout D: boundary and preregistration skeptic

Audit all shared assumptions, activation checks, claim bounds, cost symmetry,
paired-world semantics, steady-state needs for a later DES, and replication
requirements. Search specifically for knob-silencing and commensuration.

## 11. Common scout output schema

Each scout returns:

1. Its exact estimand and event sequence.
2. Symbolic equations, bounds, or counterexamples.
3. The decision and information read at each decision time.
4. The strongest favorable and unfavorable regimes.
5. Channel-activation checks.
6. Separate outcome and cost effects.
7. The strongest falsifier.
8. Minimum represented state and whether it appears representation-cheap.
9. Assumption and evidence-altitude ledger.
10. Allowable claim language and prohibited overclaim.
11. Questions that require physics or hardware evidence.

## 12. Synthesis and stopping rule

The coordinating agent synthesizes by tracing assumptions and equations, not
by majority vote. It must preserve disagreements that arise from genuinely
different model families.

The scout pass is converged when:

- the arms and contrasts have unambiguous operational definitions;
- each channel has a demonstrated activation path;
- remaining disagreements concern parameter values or hardware facts rather
  than the identity of the decision or represented object; and
- a minimal preregistration can state both earning and refusal outcomes without
  importing the full proposed ontology.

If those conditions fail, the next step is another boundary clarification, not
implementation. If they pass, the next artifact is a stamped Stage 1
preregistration followed by a minimal analytic or event-driven mechanism
probe.
