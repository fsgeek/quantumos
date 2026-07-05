from pathlib import Path

from qsim.cli import load_config, main, summarize_events
from qsim.entities import CoherenceClass


def _config_text(scheduler: str = "S0") -> str:
    extra = ""
    if scheduler == "S1":
        extra = """
admission_theta = 0.1
pregen_low_water_mark = 1
"""
    return f"""
run_seed = 11
scheduler = "{scheduler}"
arrival_rate_hz = 1.0
leases_per_round = 1
deadline_slack_s = 20.0
switch_capacity_c = 1
reconfig_delay_s = 0.0
max_sim_time_s = 5.0
{extra}

[epoch]
epoch_id = "cli-test"
memory_access_channel_s = 0.0
memory_access_wear_rate = 0.0
round_success_logistic_midpoint = -10.0
round_success_logistic_slope = 10.0
round_success_slack_penalty_per_s = 0.0
decoder_service_rate = 1000.0

[epoch.decay_rate_per_class]
messenger = 0.0
memory = 0.0

[[epoch.paths]]
a = "M0:0"
b = "M1:0"
heralding_p = 1.0
heralded_fidelity = 0.9
"""


def _write_config(tmp_path: Path, name: str = "config.toml", scheduler: str = "S0") -> Path:
    path = tmp_path / name
    path.write_text(_config_text(scheduler))
    return path


def test_load_config_builds_run_config_from_toml(tmp_path):
    config = load_config(_write_config(tmp_path))

    assert config.run_seed == 11
    assert config.scheduler == "S0"
    assert config.epoch.epoch_id == "cli-test"
    assert config.epoch.decay_rate_per_class[CoherenceClass.MESSENGER] == 0.0
    assert len(config.epoch.heralding_p_per_path) == 1


def test_cli_validate_config_prints_valid_config(tmp_path, capsys):
    config_path = _write_config(tmp_path)

    exit_code = main(["validate-config", str(config_path)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "valid:" in out
    assert "scheduler: S0" in out


def test_cli_run_writes_run_directory_and_summary(tmp_path, capsys):
    config_path = _write_config(tmp_path)
    out_root = tmp_path / "runs"

    exit_code = main(["run", str(config_path), "--out", str(out_root), "--summary"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "goodput:" in out
    run_dirs = [path for path in out_root.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "header.json").exists()
    assert (run_dirs[0] / "events.jsonl").exists()


def test_cli_summarize_accepts_run_directory(tmp_path, capsys):
    config_path = _write_config(tmp_path)
    out_root = tmp_path / "runs"
    assert main(["run", str(config_path), "--out", str(out_root)]) == 0
    run_dir = next(path for path in out_root.iterdir() if path.is_dir())

    exit_code = main(["summarize", str(run_dir)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert str(run_dir / "events.jsonl") in out
    assert "logical_error_proxy:" in out


def test_cli_compare_runs_both_configs(tmp_path, capsys):
    left = _write_config(tmp_path, "s0.toml", "S0")
    right = _write_config(tmp_path, "s1.toml", "S1")

    exit_code = main(["compare", str(left), str(right), "--out", str(tmp_path / "cmp")])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "left_run_dir:" in out
    assert "right_run_dir:" in out
    assert "delta:" in out
    assert len(list((tmp_path / "cmp" / "left").iterdir())) == 1
    assert len(list((tmp_path / "cmp" / "right").iterdir())) == 1


def test_summarize_events_exposes_core_metrics(tmp_path):
    config_path = _write_config(tmp_path)
    out_root = tmp_path / "runs"
    assert main(["run", str(config_path), "--out", str(out_root)]) == 0
    run_dir = next(path for path in out_root.iterdir() if path.is_dir())

    summary = summarize_events(run_dir / "events.jsonl")

    assert summary["offered"] > 0
    assert "goodput" in summary
    assert "max_decoder_backlog" in summary
