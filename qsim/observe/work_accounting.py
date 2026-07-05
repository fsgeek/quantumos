"""Work accounting: offered-work-normalized aggregation over a run's trace
(design spec §11). Primary metrics (goodput, logical-error proxy) divide by
*offered* rounds, never by admitted or attempted, so an admission controller
cannot trivially improve them by rejecting work.

`pool_returned` (pregen return path, §5) is accounted separately and never
folded into "consumed"/"completed" counts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class WorkAccounting:
    offered: int = 0
    retries: int = 0
    admitted: int = 0
    deferred: int = 0
    dropped: int = 0
    completed_in_deadline: int = 0
    completed_late: int = 0
    failed: int = 0
    pool_returned: int = 0  # accounted separately per §5, never folded into "consumed"

    def attempts(self) -> int:
        return self.offered + self.retries

    def goodput(self) -> float:
        if self.offered == 0:
            return 0.0
        return self.completed_in_deadline / self.offered


def iter_events(events_path: Path) -> Iterator[dict]:
    """Yield one parsed JSON dict per line of events.jsonl, in file order.

    A trace with zero published events never has its events.jsonl created
    by RunDirWriter.append_event (it is only opened on first append), so a
    missing file is treated as an empty trace rather than an error.
    """
    events_path = Path(events_path)
    if not events_path.exists():
        return
    with open(events_path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


# Local trace convention (payload shapes are not frozen by the interface
# contract): each of these event types increments the identically-named
# WorkAccounting field once per occurrence. `round.arrived` is handled
# separately below since it splits into `offered` vs `retries` based on
# payload["retry_ordinal"].
_TERMINAL_ROUND_FIELD = {
    "round.admitted": "admitted",
    "round.deferred": "deferred",
    "round.dropped": "dropped",
    "round.completed_in_deadline": "completed_in_deadline",
    "round.completed_late": "completed_late",
    "round.failed": "failed",
    "lease.pool_returned": "pool_returned",
}


def compute_work_accounting(events_path: Path) -> WorkAccounting:
    """Scan a trace and return a populated WorkAccounting (design spec §11)."""
    wa = WorkAccounting()
    for record in iter_events(events_path):
        event_type = record["event_type"]
        if event_type == "round.arrived":
            if record["payload"].get("retry_ordinal", 0) == 0:
                wa.offered += 1
            else:
                wa.retries += 1
            continue
        field = _TERMINAL_ROUND_FIELD.get(event_type)
        if field is not None:
            setattr(wa, field, getattr(wa, field) + 1)
    return wa
