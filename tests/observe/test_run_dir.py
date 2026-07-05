import json
from dataclasses import dataclass
from enum import Enum

from qsim.observe.run_dir import RunDirWriter, SCHEMA_VERSION


class _FakeCoherenceClass(Enum):
    MESSENGER = "messenger"
    MEMORY = "memory"


@dataclass(frozen=True)
class _FakePortId:
    module_id: str
    port_index: int


@dataclass(frozen=True)
class _FakeEpoch:
    epoch_id: str
    decay_rate_per_class: dict
    heralding_p_per_path: dict


@dataclass(frozen=True)
class _FakeRunConfig:
    run_seed: int
    scheduler: str
    epoch: _FakeEpoch


def _plain_config():
    return _FakeRunConfig(
        run_seed=42, scheduler="S0",
        epoch=_FakeEpoch(epoch_id="e0", decay_rate_per_class={}, heralding_p_per_path={}),
    )


def test_write_header_declares_no_filtering_by_default(tmp_path):
    writer = RunDirWriter(root=tmp_path, run_id="run-1")

    writer.write_header(config=_plain_config(), run_seed=42, git_sha="abc123")

    header = json.loads((tmp_path / "run-1" / "header.json").read_text())
    assert "filtering" in header
    assert header["filtering"] == {"enabled": False}


def test_write_header_records_declared_filtering_verbatim(tmp_path):
    writer = RunDirWriter(root=tmp_path, run_id="run-2")
    filtering = {"enabled": True, "reason": "capped at 1000 events", "cap": 1000}

    writer.write_header(config=_plain_config(), run_seed=1, git_sha="def456",
                         filtering_declared=filtering)

    header = json.loads((tmp_path / "run-2" / "header.json").read_text())
    assert header["filtering"] == filtering


def test_write_header_includes_identity_and_schema_version(tmp_path):
    writer = RunDirWriter(root=tmp_path, run_id="run-3")

    writer.write_header(config=_plain_config(), run_seed=9, git_sha="jkl012")

    header = json.loads((tmp_path / "run-3" / "header.json").read_text())
    assert header["run_id"] == "run-3"
    assert header["run_seed"] == 9
    assert header["git_sha"] == "jkl012"
    assert header["schema_version"] == SCHEMA_VERSION


def test_write_header_serializes_enum_and_tuple_dataclass_keys(tmp_path):
    writer = RunDirWriter(root=tmp_path, run_id="run-4")
    port_a = _FakePortId(module_id="modA", port_index=0)
    port_b = _FakePortId(module_id="modB", port_index=1)
    epoch = _FakeEpoch(
        epoch_id="e0",
        decay_rate_per_class={_FakeCoherenceClass.MEMORY: 0.01},
        heralding_p_per_path={(port_a, port_b): 0.5},
    )
    config = _FakeRunConfig(run_seed=7, scheduler="S0", epoch=epoch)

    writer.write_header(config=config, run_seed=7, git_sha="ghi789")

    raw = (tmp_path / "run-4" / "header.json").read_text()
    header = json.loads(raw)  # must not raise: proves valid JSON was written
    epoch_out = header["config"]["epoch"]
    assert epoch_out["decay_rate_per_class"] == {"memory": 0.01}
    (path_key,) = epoch_out["heralding_p_per_path"].keys()
    assert epoch_out["heralding_p_per_path"][path_key] == 0.5


def test_init_creates_run_directory_with_checkpoints_subdir(tmp_path):
    RunDirWriter(root=tmp_path, run_id="run-5")

    assert (tmp_path / "run-5").is_dir()
    assert (tmp_path / "run-5" / "checkpoints").is_dir()
