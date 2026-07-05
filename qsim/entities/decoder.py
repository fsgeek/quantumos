"""DecoderJob entity: service demand, priority, and enqueue/dequeue/
completion timestamps (design spec §5). Adds a task-local `cancelled_at`
timestamp (not in the frozen interface contract's field list for
DecoderJob) to represent the §5 failure-cleanup cascade's decoder-job
cancellation disposition."""

from dataclasses import dataclass


@dataclass
class DecoderJob:
    job_id: str
    round_id: str
    priority: int
    enqueue_time: float
    dequeue_time: float | None = None
    completion_time: float | None = None
    cancelled_at: float | None = None  # task-local addition; see module docstring

    def dequeue(self, at: float) -> None:
        """Record dequeue time. Illegal if already dequeued, completed, or
        cancelled."""
        if self.dequeue_time is not None:
            raise ValueError(f"job {self.job_id} already dequeued at {self.dequeue_time}")
        if self.completion_time is not None:
            raise ValueError(f"job {self.job_id} already completed")
        if self.cancelled_at is not None:
            raise ValueError(f"job {self.job_id} already cancelled")
        self.dequeue_time = at

    def complete(self, at: float) -> None:
        """Record completion time. Illegal unless dequeued first, and
        illegal if already completed or cancelled (rejects double
        completion)."""
        if self.dequeue_time is None:
            raise ValueError(f"job {self.job_id} cannot complete before being dequeued")
        if self.completion_time is not None:
            raise ValueError(f"job {self.job_id} already completed at {self.completion_time}")
        if self.cancelled_at is not None:
            raise ValueError(f"job {self.job_id} already cancelled")
        self.completion_time = at

    def cancel(self, at: float) -> None:
        """Round-cleanup-cascade disposition (design spec §5): cancel this
        job on round failure/cancellation, whether or not it has already
        been dequeued. Illegal if already completed or already cancelled."""
        if self.completion_time is not None:
            raise ValueError(f"job {self.job_id} already completed, cannot cancel")
        if self.cancelled_at is not None:
            raise ValueError(f"job {self.job_id} already cancelled at {self.cancelled_at}")
        self.cancelled_at = at
