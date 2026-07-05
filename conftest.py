"""Ensures the repo root is importable so `qsim.core.*` (and sibling qsim
packages developed in parallel) resolve regardless of how pytest is
invoked."""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
