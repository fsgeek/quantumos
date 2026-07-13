# QuantumOS

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21340726.svg)](https://doi.org/10.5281/zenodo.21340726)

QuantumOS is a Python discrete-event simulator for exploring operating-system
resource management in a Photonic-style, entanglement-first quantum computer.

The simulator is intended as a sensitivity instrument, not a point predictor. It
models how systems-level behavior changes as physics-facing parameters vary:
heralding probability, entanglement freshness, memory access cost, decoder
service time, switch-fabric contention, and deadline slack.

The working hypothesis is that a quantum OS for this architecture must treat
entanglement leases, syndrome rounds, decoder capacity, switch paths, and
calibration epochs as first-class schedulable resources. This repository is the
executable counterpart to that design argument.

The methodological stance is deliberate: this is not a place that accumulates
concepts, but "a place that tests whether concepts deserve to exist" (external
methods review, 2026-07-07). No quantity enters the object model merely for
being physically meaningful — it must name the decision that reads it, the lead
time it is read at, and why it is not derivable from cheaper represented state.
The governing rule and the pre-registered experiments that enforce it live in
`docs/superpowers/specs/2026-07-06-field-battery-prereg.md`.

## Project Status

This is an M0 research simulator. The core package and tests are implemented,
with a small experimental CLI for running checked-in configs and summarizing
run traces.

## What It Simulates

At a high level, one simulated syndrome round flows through:

1. A closed-loop workload generator emits a round request.
2. A scheduler admits, defers, or rejects work.
3. Lease requests reserve switch-fabric paths.
4. Heralding attempts stochastically produce entanglement.
5. Freshness and memory-access models update effective fidelity.
6. A decoder job enters a single-server backlog.
7. Round success is sampled and all state transitions are traced.

The current implementation includes:

- `S0`: baseline scheduler without explicit freshness-aware admission.
- `S1`: scheduler with admission-control and pre-generation hooks.
- Pluggable model surfaces for decay, heralding, memory access, round success,
  and decoder service.
- Keyed random-number draws for deterministic paired-policy comparisons.
- JSONL trace output plus post-hoc observability views.

## Repository Layout

```text
qsim/
  core/          DES engine, event heap, keyed RNG, trace bus, invariants
  entities/      Inert dataclass object model: leases, rounds, modules, qubits
  experiments/   Run configuration and single-run driver
  models/        Physics/model Protocols and analytic M0 implementations
  observe/       Run-directory writer, metric views, work accounting
  policies/      Scheduler protocol and S0/S1 policies
  workload/      Closed-loop synthetic workload generator

docs/
  quantum_os.md                          Constraint-first OS argument
  superpowers/specs/...design.md         Simulator design spec
  references/                            Supporting reference material

examples/                                 CLI-ready experiment configs
tests/                                    Unit and integration tests
timestamps/                              OpenTimestamps artifacts
scripts/                                 Repository helper scripts
```

## Requirements

- Python 3.14 or newer, as declared in `pyproject.toml`
- `uv` for dependency management, or another tool that can install from
  `pyproject.toml`

Runtime dependencies are intentionally small. The only declared dependency is
`opentimestamps-client`, used by repository timestamp tooling rather than the
simulator core.

## Setup

```bash
uv sync
```

If you are not using `uv`, create a Python 3.14 environment and install the
project dependencies from `pyproject.toml`.

## Running Tests

```bash
uv run pytest
```

The test suite covers the object model, model surfaces, scheduler behavior,
engine lifecycle, observability views, workload generation, and deterministic
trace behavior.

## Running a Simulation

The CLI runs TOML or JSON experiment configs:

```bash
uv run quantumos validate-config examples/s0-baseline.toml
uv run quantumos run examples/s0-baseline.toml --out runs --summary
uv run quantumos summarize runs/<run-id>
uv run quantumos compare examples/s0-baseline.toml examples/s1-admission.toml --out runs/compare --seed 42
```

The TOML config format keeps path calibration entries as records:

```toml
run_seed = 42
scheduler = "S0"
arrival_rate_hz = 1.0
leases_per_round = 1
deadline_slack_s = 5.0
switch_capacity_c = 1
reconfig_delay_s = 0.01
max_sim_time_s = 20.0

[epoch]
epoch_id = "example-s0"
memory_access_channel_s = 0.001
memory_access_wear_rate = 0.01
round_success_logistic_midpoint = 0.5
round_success_logistic_slope = 10.0
round_success_slack_penalty_per_s = 1.0
decoder_service_rate = 5.0

[epoch.decay_rate_per_class]
messenger = 0.01
memory = 0.001

[[epoch.paths]]
a = "M0:0"
b = "M1:0"
heralding_p = 0.7
heralded_fidelity = 0.95
```

Experiments can also be launched from Python:

```python
from pathlib import Path

from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.experiments.run import run

a = PortId(module_id="M0", port_index=0)
b = PortId(module_id="M1", port_index=0)
path = make_path_id(a, b)

epoch = CalibrationEpoch(
    epoch_id="example",
    decay_rate_per_class={
        CoherenceClass.MESSENGER: 0.01,
        CoherenceClass.MEMORY: 0.001,
    },
    memory_access_channel_s=0.001,
    memory_access_wear_rate=0.01,
    heralding_p_per_path={path: 0.7},
    heralded_fidelity_per_path={path: 0.95},
    round_success_logistic_midpoint=0.5,
    round_success_logistic_slope=10.0,
    round_success_slack_penalty_per_s=1.0,
    decoder_service_rate=5.0,
)

config = RunConfig(
    run_seed=42,
    scheduler="S0",
    epoch=epoch,
    arrival_rate_hz=1.0,
    leases_per_round=1,
    deadline_slack_s=5.0,
    switch_capacity_c=1,
    reconfig_delay_s=0.01,
    max_sim_time_s=20.0,
)

run_dir = run(config, Path("runs"))
print(run_dir)
```

Each run creates a directory containing:

- `header.json`: configuration, seed, git provenance, filtering declarations,
  and steady-state verdict.
- `events.jsonl`: the full event trace emitted by the simulation.

## Observability Views

Post-hoc metric functions live in `qsim.observe.views` and operate on an
`events.jsonl` path:

- `goodput`
- `freshness_at_consumption`
- `fidelity_at_outcome`
- `decoder_backlog_series`
- `deadline_compliance`
- `resource_utilization`
- `logical_error_proxy`
- `shared_key_fraction`

Example:

```python
from qsim.observe import views

events = run_dir / "events.jsonl"
print(views.goodput(events))
print(views.deadline_compliance(events))
```

## Design References

Start with:

- `docs/quantum_os.md` for the constraint-first quantum OS framing.
- `docs/superpowers/specs/2026-07-04-quantum-os-simulator-design.md` for the
  simulator architecture and M0 design contract.
- `docs/superpowers/specs/2026-07-06-field-battery-prereg.md` for the
  pre-registered field battery and the object-model admission rule.

The simulator intentionally keeps physics details behind Protocol-based model
surfaces so analytic M0 implementations can later be replaced by richer
physicist-supplied or stabilizer-backed models.
