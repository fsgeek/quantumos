import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from qsim.core.rng import Draw, draw_uniform

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_draw_uniform_is_deterministic_for_same_inputs():
    a = draw_uniform(run_seed=42, stream="herald", key=("round-1", "ep-a", "ep-b", 0))
    b = draw_uniform(run_seed=42, stream="herald", key=("round-1", "ep-a", "ep-b", 0))
    assert a == b


def test_draw_uniform_varies_with_key():
    a = draw_uniform(run_seed=42, stream="herald", key=("round-1", 0))
    b = draw_uniform(run_seed=42, stream="herald", key=("round-1", 1))
    assert a != b


def test_draw_uniform_varies_with_stream():
    a = draw_uniform(run_seed=42, stream="herald", key=("round-1", 0))
    b = draw_uniform(run_seed=42, stream="decode", key=("round-1", 0))
    assert a != b


def test_draw_uniform_varies_with_run_seed():
    a = draw_uniform(run_seed=1, stream="herald", key=("round-1", 0))
    b = draw_uniform(run_seed=2, stream="herald", key=("round-1", 0))
    assert a != b


def test_draw_uniform_is_in_unit_interval():
    for i in range(2000):
        u = draw_uniform(run_seed=7, stream="workload", key=("arrival", i))
        assert 0.0 <= u < 1.0


def test_draw_uniform_does_not_depend_on_builtin_hash_seed():
    script = (
        "from qsim.core.rng import draw_uniform; "
        "print(draw_uniform(run_seed=99, stream='herald', key=('round-9', 'a', 'b', 3)))"
    )

    def run_with_hash_seed(seed: str) -> str:
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(REPO_ROOT))
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    assert run_with_hash_seed("0") == run_with_hash_seed("4242")


def test_draw_dataclass_holds_uniform_sample():
    d = Draw(u=0.5)
    assert d.u == 0.5


def test_draw_dataclass_is_frozen():
    d = Draw(u=0.5)
    with pytest.raises(FrozenInstanceError):
        d.u = 0.9
