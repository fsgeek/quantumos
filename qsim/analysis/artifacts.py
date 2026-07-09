"""Write-once gate, provenance, and report writing (design §4.3, §9).

The write-once predicted-lags file is the honesty mechanism: re-running an
analysis can never re-derive predictions after the ACF has been seen;
deleting the file leaves a hole the git/OTS discipline makes visible.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

# The prereg's OTS-stamped commit (docs/superpowers/specs/
# 2026-07-06-field-battery-prereg.md). Every presentable result must come
# from a run whose header git SHA is a descendant of this commit.
STAMPED_COMMIT = "06b0bd4feb0ca97d5b8f0245b8cbdf5bda10721d"


def analysis_dir(run_dir: Path) -> Path:
    d = Path(run_dir) / "analysis"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_once(path: Path, payload: dict) -> tuple[dict, bool]:
    """Write payload as JSON iff `path` does not exist; otherwise return the
    existing content VERBATIM and never rewrite (design §4.3)."""
    path = Path(path)
    if path.exists():
        return json.loads(path.read_text()), True
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return payload, False


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ancestry(run_git_sha: str) -> dict:
    """Best-effort forward-provability check (design §9): is the run's git
    SHA a descendant of the stamped commit? Recorded either way; git being
    unavailable is a note, never a crash."""
    result = {"stamped_commit": STAMPED_COMMIT, "run_git_sha": run_git_sha}
    try:
        proc = subprocess.run(
            ["git", "merge-base", "--is-ancestor", STAMPED_COMMIT, run_git_sha],
            capture_output=True, text=True,
        )
    except OSError as exc:
        result["is_descendant"] = None
        result["note"] = f"git unavailable: {exc}"
        return result
    if proc.returncode == 0:
        result["is_descendant"] = True
        result["note"] = "run sha is a descendant of the stamped commit"
    elif proc.returncode == 1:
        result["is_descendant"] = False
        result["note"] = "run sha is NOT a descendant of the stamped commit"
    else:
        result["is_descendant"] = None
        result["note"] = f"ancestry undecidable: {proc.stderr.strip()}"
    return result


def write_report(run_dir: Path, name: str, payload: dict) -> Path:
    """Write `<run_dir>/analysis/<name>.json` — the JSON artifact is the
    record; stdout summaries are a courtesy (design §9)."""
    path = analysis_dir(run_dir) / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return path
