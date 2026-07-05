"""Run directory writer: header.json + events.jsonl (design spec §12).

FULL-FIDELITY capture is the whole point: the header stamps config, seeds,
and code version; events.jsonl records every published trace event
verbatim. Nothing is silently truncated or aggregated at write time —
metrics are post-hoc computations over this data, never a substitute
source of truth.
"""

from __future__ import annotations

import dataclasses
import json
from enum import Enum
from pathlib import Path

SCHEMA_VERSION = 1


def _key_to_str(key):
    if isinstance(key, str):
        return key
    if isinstance(key, Enum):
        return str(key.value)
    if isinstance(key, (int, float)) and not isinstance(key, bool):
        return str(key)
    return json.dumps(_json_safe(key), sort_keys=True)


def _json_safe(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _json_safe(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {_key_to_str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj


class RunDirWriter:
    def __init__(self, root: Path, run_id: str) -> None:
        self.root = Path(root)
        self.run_id = run_id
        self.run_dir = self.root / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
        self.header_path = self.run_dir / "header.json"
        self.events_path = self.run_dir / "events.jsonl"

    def write_header(self, config, run_seed: int, git_sha: str,
                      filtering_declared: dict | None = None) -> None:
        filtering = filtering_declared if filtering_declared is not None else {"enabled": False}
        header = {
            "run_id": self.run_id,
            "run_seed": run_seed,
            "git_sha": git_sha,
            "schema_version": SCHEMA_VERSION,
            "filtering": filtering,
            "config": _json_safe(config),
        }
        self.header_path.write_text(json.dumps(header, indent=2, sort_keys=True))

    def append_event(self, event) -> None:
        record = {
            "run_id": event.run_id,
            "seq": event.seq,
            "sim_time": event.sim_time,
            "event_type": event.event_type,
            "entity_id": event.entity_id,
            "causal_parent_id": (
                list(event.causal_parent_id) if event.causal_parent_id is not None else None
            ),
            "payload": _json_safe(event.payload),
        }
        with open(self.events_path, "a") as f:
            f.write(json.dumps(record) + "\n")
