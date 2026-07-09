"""Write-once gate + provenance (design §4.3, §9)."""
import json
import subprocess

from qsim.analysis.artifacts import (
    STAMPED_COMMIT,
    ancestry,
    analysis_dir,
    sha256_of,
    write_once,
    write_report,
)


def test_write_once_first_write_lands(tmp_path):
    path = tmp_path / "predicted_lags_t1.json"
    content, reused = write_once(path, {"a": 1})
    assert content == {"a": 1}
    assert reused is False
    assert json.loads(path.read_text()) == {"a": 1}


def test_write_once_never_rewrites(tmp_path):
    path = tmp_path / "predicted_lags_t1.json"
    write_once(path, {"a": 1})
    content, reused = write_once(path, {"a": 2})
    assert content == {"a": 1}  # original, verbatim
    assert reused is True
    assert json.loads(path.read_text()) == {"a": 1}


def test_sha256_is_stable_over_bytes(tmp_path):
    p = tmp_path / "f.json"
    p.write_text('{"a": 1}')
    assert sha256_of(p) == sha256_of(p)
    q = tmp_path / "g.json"
    q.write_text('{"a": 2}')
    assert sha256_of(p) != sha256_of(q)


def test_ancestry_head_is_descendant_of_stamp():
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()
    result = ancestry(head)
    assert result["stamped_commit"] == STAMPED_COMMIT
    assert result["is_descendant"] is True


def test_ancestry_unknown_sha_is_recorded_not_raised():
    result = ancestry("0" * 40)
    assert result["is_descendant"] in (False, None)
    assert "note" in result


def test_write_report_creates_analysis_dir(tmp_path):
    run_dir = tmp_path / "run1"
    run_dir.mkdir()
    path = write_report(run_dir, "t1_report", {"verdict": "X"})
    assert path == run_dir / "analysis" / "t1_report.json"
    assert json.loads(path.read_text())["verdict"] == "X"
    assert analysis_dir(run_dir).is_dir()
