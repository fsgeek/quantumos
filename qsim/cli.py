"""Small experiment CLI for running and summarizing QuantumOS simulations."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from dataclasses import replace
from pathlib import Path
from typing import Any, Sequence

from qsim.analysis.t1 import analyze_t1
from qsim.analysis.t2 import analyze_t2
from qsim.analysis.t3 import analyze_t3
from qsim.entities import CalibrationEpoch, CoherenceClass, PortId, make_path_id
from qsim.experiments.config import RunConfig
from qsim.experiments.run import run
from qsim.observe import views
from qsim.observe.work_accounting import compute_work_accounting


def load_config(path: Path) -> RunConfig:
    """Load a RunConfig from a JSON or TOML experiment file."""
    path = Path(path)
    raw = path.read_bytes()
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
    elif path.suffix.lower() == ".toml":
        data = tomllib.loads(raw.decode())
    else:
        raise ValueError(f"unsupported config extension {path.suffix!r}; use .toml or .json")
    if not isinstance(data, dict):
        raise ValueError("config root must be an object")
    return config_from_mapping(data)


def config_from_mapping(data: dict[str, Any]) -> RunConfig:
    """Build a RunConfig from a plain mapping.

    The config file keeps path-keyed calibration maps human-editable by using
    `epoch.paths` records:

        [[epoch.paths]]
        a = "M0:0"
        b = "M1:0"
        heralding_p = 0.7
        heralded_fidelity = 0.95
    """
    fields = dict(data)
    try:
        epoch_data = fields.pop("epoch")
    except KeyError as exc:
        raise ValueError("config requires an [epoch] section") from exc
    if not isinstance(epoch_data, dict):
        raise ValueError("epoch must be an object")
    fields["epoch"] = _epoch_from_mapping(epoch_data)
    return RunConfig(**fields)


def _epoch_from_mapping(data: dict[str, Any]) -> CalibrationEpoch:
    fields = dict(data)
    paths = fields.pop("paths", [])
    if not isinstance(paths, list):
        raise ValueError("epoch.paths must be a list")

    fields["decay_rate_per_class"] = _coherence_map(
        fields.get("decay_rate_per_class", {})
    )
    heralding_p_per_path = {}
    heralded_fidelity_per_path = {}
    for index, item in enumerate(paths):
        if not isinstance(item, dict):
            raise ValueError(f"epoch.paths[{index}] must be an object")
        path_id = make_path_id(_parse_port(item["a"]), _parse_port(item["b"]))
        heralding_p_per_path[path_id] = float(item["heralding_p"])
        heralded_fidelity_per_path[path_id] = float(item["heralded_fidelity"])

    fields["heralding_p_per_path"] = heralding_p_per_path
    fields["heralded_fidelity_per_path"] = heralded_fidelity_per_path
    return CalibrationEpoch(**fields)


def _coherence_map(data: dict[str, Any]) -> dict[CoherenceClass, float]:
    if not isinstance(data, dict):
        raise ValueError("epoch.decay_rate_per_class must be an object")
    result = {}
    for key, value in data.items():
        try:
            coherence = CoherenceClass(key)
        except ValueError:
            try:
                coherence = CoherenceClass[key.upper()]
            except KeyError as exc:
                raise ValueError(f"unknown coherence class {key!r}") from exc
        result[coherence] = float(value)
    return result


def _parse_port(value: str) -> PortId:
    if not isinstance(value, str) or ":" not in value:
        raise ValueError(f"port must use MODULE:INDEX syntax, got {value!r}")
    module_id, raw_index = value.rsplit(":", 1)
    if not module_id:
        raise ValueError(f"port module id cannot be empty: {value!r}")
    return PortId(module_id=module_id, port_index=int(raw_index))


def summarize_events(events_path: Path) -> dict[str, Any]:
    events_path = Path(events_path)
    wa = compute_work_accounting(events_path)
    deadline = views.deadline_compliance(events_path)
    backlog = views.decoder_backlog_series(events_path)
    freshness = views.freshness_at_consumption(events_path)
    return {
        "offered": wa.offered,
        "retries": wa.retries,
        "attempts": wa.attempts(),
        "admitted": wa.admitted,
        "deferred": wa.deferred,
        "dropped": wa.dropped,
        "completed_in_deadline": wa.completed_in_deadline,
        "completed_late": wa.completed_late,
        "failed": wa.failed,
        "goodput": views.goodput(events_path),
        "logical_error_proxy": views.logical_error_proxy(events_path),
        "deadline_completed_in_deadline": deadline["completed_in_deadline"],
        "deadline_completed_late": deadline["completed_late"],
        "deadline_failed": deadline["failed"],
        "deadline_dropped": deadline["dropped"],
        "max_decoder_backlog": max((value for _, value in backlog), default=0),
        "mean_freshness_at_consumption": _mean(freshness),
    }


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def format_summary(summary: dict[str, Any], label: str | None = None) -> str:
    lines = []
    if label is not None:
        lines.append(f"{label}:")
    for key in (
        "offered",
        "retries",
        "attempts",
        "admitted",
        "deferred",
        "dropped",
        "completed_in_deadline",
        "completed_late",
        "failed",
        "goodput",
        "logical_error_proxy",
        "max_decoder_backlog",
        "mean_freshness_at_consumption",
    ):
        lines.append(f"{key}: {_format_value(summary[key])}")
    return "\n".join(lines)


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if value is None:
        return "n/a"
    return str(value)


def _events_path(path: Path) -> Path:
    path = Path(path)
    if path.name == "events.jsonl":
        return path
    return path / "events.jsonl"


def _run_command(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    run_dir = run(config, args.out)
    print(run_dir)
    if args.summary:
        print()
        print(format_summary(summarize_events(run_dir / "events.jsonl")))
    return 0


def _summarize_command(args: argparse.Namespace) -> int:
    events_path = _events_path(args.path)
    print(format_summary(summarize_events(events_path), label=str(events_path)))
    return 0


def _compare_command(args: argparse.Namespace) -> int:
    left_config = load_config(args.left_config)
    right_config = load_config(args.right_config)
    if args.seed is not None:
        left_config = replace(left_config, run_seed=args.seed)
        right_config = replace(right_config, run_seed=args.seed)

    left_dir = run(left_config, args.out / "left")
    right_dir = run(right_config, args.out / "right")
    left_summary = summarize_events(left_dir / "events.jsonl")
    right_summary = summarize_events(right_dir / "events.jsonl")

    print(f"left_run_dir: {left_dir}")
    print(f"right_run_dir: {right_dir}")
    print()
    print(format_summary(left_summary, label="left"))
    print()
    print(format_summary(right_summary, label="right"))
    print()
    print("delta:")
    for key in ("goodput", "logical_error_proxy", "max_decoder_backlog"):
        print(f"{key}: {_format_value(right_summary[key] - left_summary[key])}")
    return 0


def _validate_config_command(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    print(f"valid: {args.config}")
    print(f"scheduler: {config.scheduler}")
    print(f"run_seed: {config.run_seed}")
    return 0


def _print_analysis(report: dict) -> None:
    print(f"test: {report['test']}")
    print(f"verdict: {report['verdict']}")
    if report.get("directive"):
        print(f"DIRECTIVE: **{report['directive']}**")
    if report.get("caveat"):
        print(f"caveat: {report['caveat']}")
    for refusal in report.get("refusals", []):
        print(f"refusal: {refusal}")


def _analyze_command(args: argparse.Namespace) -> int:
    if args.test == "t1":
        report = analyze_t1(args.run_dir, mode=args.mode,
                            companion_dir=args.companion,
                            bin_s_override=args.bin_s,
                            surrogate_seed=args.seed)
    elif args.test == "t2":
        report = analyze_t2(args.run_dir, bin_s_override=args.bin_s,
                            surrogate_seed=args.seed)
    else:
        report = analyze_t3(args.run_dir)
    _print_analysis(report)
    print(f"report: {Path(args.run_dir) / 'analysis'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quantumos",
        description="Run and summarize QuantumOS simulator experiments.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run one experiment config")
    run_parser.add_argument("config", type=Path, help="TOML or JSON config file")
    run_parser.add_argument("--out", type=Path, default=Path("runs"), help="run output root")
    run_parser.add_argument(
        "--summary", action="store_true", help="print a metric summary after the run"
    )
    run_parser.set_defaults(func=_run_command)

    summarize_parser = subparsers.add_parser(
        "summarize", help="summarize a run directory or events.jsonl file"
    )
    summarize_parser.add_argument("path", type=Path, help="run directory or events.jsonl")
    summarize_parser.set_defaults(func=_summarize_command)

    compare_parser = subparsers.add_parser(
        "compare", help="run two configs and print side-by-side summaries"
    )
    compare_parser.add_argument("left_config", type=Path, help="left TOML or JSON config")
    compare_parser.add_argument("right_config", type=Path, help="right TOML or JSON config")
    compare_parser.add_argument("--out", type=Path, default=Path("runs/compare"), help="output root")
    compare_parser.add_argument("--seed", type=int, help="override both configs' run_seed")
    compare_parser.set_defaults(func=_compare_command)

    validate_parser = subparsers.add_parser("validate-config", help="validate a config file")
    validate_parser.add_argument("config", type=Path, help="TOML or JSON config file")
    validate_parser.set_defaults(func=_validate_config_command)

    analyze_parser = subparsers.add_parser(
        "analyze", help="run a field-battery analysis over a run directory"
    )
    analyze_sub = analyze_parser.add_subparsers(dest="test", required=True)
    t1_parser = analyze_sub.add_parser("t1", help="pool-flux ACF (prereg T1)")
    t1_parser.add_argument("run_dir", type=Path)
    t1_parser.add_argument("--mode", choices=("control", "open"), required=True)
    t1_parser.add_argument("--companion", type=Path, default=None,
                           help="knob-motion companion run dir (open mode)")
    t1_parser.add_argument("--bin-s", dest="bin_s", type=float, default=None)
    t1_parser.add_argument("--seed", type=int, default=0,
                           help="surrogate shuffle seed (recorded in report)")
    t1_parser.set_defaults(func=_analyze_command)
    t2_parser = analyze_sub.add_parser("t2", help="backlog-slope ACF (prereg T2)")
    t2_parser.add_argument("run_dir", type=Path)
    t2_parser.add_argument("--bin-s", dest="bin_s", type=float, default=None)
    t2_parser.add_argument("--seed", type=int, default=0)
    t2_parser.set_defaults(func=_analyze_command)
    t3_parser = analyze_sub.add_parser("t3", help="rank inversions (prereg T3)")
    t3_parser.add_argument("run_dir", type=Path)
    t3_parser.set_defaults(func=_analyze_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
